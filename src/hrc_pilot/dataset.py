"""HRC-Continuous 数据集生成、加载和模型批量评测。

数据集以 episode 目录为唯一边界。目录名和 ``scenario.json`` 决定实例身份；
不使用 manifest 保存模型、伙伴或反事实的配对关系。模型评测会重新运行同一
场景契约，因此输入模型看见的仍然是公开 Observation，评测器保留私有目标。
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from dataclasses import replace
from typing import Any, Iterable

from .continuous import (
    ContinuousScenario,
    ContinuousWorld,
    generate_benchmark_suite,
    generate_scenarios,
    load_continuous_policy,
    make_partner,
    run_continuous_episode,
    load_scenario_catalog,
    scenario_from_dict,
)


DATASET_VERSION = "hrc-continuous-1"


def _episode_files(root: Path) -> Iterable[Path]:
    """递归找到 episode 的 scenario.json，不把聚合输出当成 episode。"""
    for path in sorted(root.rglob("scenario.json")):
        if path.parent.name.startswith("_"):
            continue
        yield path


def iter_dataset(root: str | Path, *, split: str | None = None) -> list[tuple[Path, ContinuousScenario]]:
    """按稳定路径读取数据集 episode，可按结构 split 筛选。"""
    root = Path(root)
    episodes: list[tuple[Path, ContinuousScenario]] = []
    for scenario_path in _episode_files(root):
        scenario = scenario_from_dict(json.loads(scenario_path.read_text(encoding="utf-8")))
        if split is None or scenario.structure.split == split:
            episodes.append((scenario_path.parent, scenario))
    return episodes


def _safe_name(spec: str) -> str:
    return spec.replace(":", "_").replace("/", "_").replace("\\", "_")


def _ensure_empty_or_missing(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise ValueError(f"输出目录已有内容，请使用新的目录：{path}")


def generate_dataset(*, output: str | Path, count: int = 0, seed: int = 0,
                     suite: bool = True, count_per_condition: int = 2,
                     repeats: int = 1, partner_mode: str = "adaptive",
                     policy_spec: str = "greedy_public",
                     scenario_dir: str | Path | None = None,
                     backend_factory=ContinuousWorld) -> dict[str, Any]:
    """生成结构化 benchmark 数据集，并写入每个 episode 的完整审计产物。

    ``suite=True`` 生成 train/dev/test 结构条件；``count`` 用于只生成随机
    场景；``scenario_dir`` 直接加载用户定义的 JSON 场景目录。重复实验
    通过 episode 名和 seed 区分，仍然不需要关系清单。
    """
    output = Path(output)
    _ensure_empty_or_missing(output)
    if repeats < 1:
        raise ValueError("repeats 必须为正整数")
    if partner_mode not in {"fixed_replay", "reactive", "adaptive"}:
        raise ValueError(f"未知伙伴模式: {partner_mode}")
    if scenario_dir is not None and count:
        raise ValueError("scenario_dir 不能和 count 同时使用")
    if scenario_dir is None and suite and count:
        raise ValueError("suite 和 count 只能选择一个")
    if scenario_dir is not None:
        base = load_scenario_catalog(scenario_dir)
    else:
        base = (generate_benchmark_suite(count_per_condition=count_per_condition,
                                         seed=seed, include_reference=False)
                if suite else generate_scenarios(count, seed=seed))
    if not base:
        raise ValueError("没有可生成的场景")
    names = [scenario.name for scenario in base]
    if len(names) != len(set(names)):
        raise ValueError("场景目录中的 name 必须唯一，才能稳定生成 episode 路径")
    policy = load_continuous_policy(policy_spec)
    results: list[dict[str, Any]] = []
    for repeat in range(repeats):
        for scenario in base:
            episode_seed = seed + repeat
            episode_name = f"{scenario.structure.split}/{scenario.name}_r{repeat:03d}"
            episode_scenario = replace(scenario, name=f"{scenario.name}_r{repeat:03d}")
            episode_output = output / episode_name
            result = run_continuous_episode(
                episode_scenario, policy, make_partner(episode_scenario, partner_mode),
                seed=episode_seed, output=episode_output, partner_mode=partner_mode,
                backend_factory=backend_factory,
            )
            result["dataset_version"] = DATASET_VERSION
            result["episode_id"] = episode_name
            (episode_output / "metrics.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            results.append(result)
    output.mkdir(parents=True, exist_ok=True)
    summary = aggregate_results(results)
    metadata = {
        "dataset_version": DATASET_VERSION,
        "generator": "hrc_pilot.dataset.generate_dataset",
        "policy_spec": policy_spec,
        "partner_mode": partner_mode,
        "seed": seed,
        "repeats": repeats,
        "scenario_source": (str(scenario_dir) if scenario_dir is not None
                             else ("generated_suite" if suite else "generated_random")),
        "episode_count": len(results),
        "backends": sorted({result["backend"] for result in results}),
        "splits": sorted({result["structure_split"] for result in results}),
        "aggregate": summary,
    }
    (output / "dataset.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "summary.json").write_text(json.dumps({"episodes": results, **summary},
                                                     ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """计算可跨策略比较的总体和分组指标。"""
    numeric_keys = (
        "task_success", "activity_success", "robot_success", "human_success",
        "robot_role_success", "human_role_success", "completion_time_s",
        "coordination_cost", "conflict_rate", "human_reassignments",
        "public_replans", "recovery_time_steps", "human_trust_delta",
        "human_reliability_delta", "human_workload_delta", "human_dependency_delta",
    )

    def mean(rows: list[dict[str, Any]], key: str) -> float | None:
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        return sum(values) / len(values) if values else None

    def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {key: mean(rows, key) for key in numeric_keys} | {"episodes": len(rows)}

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        for key in ("structure_split", "condition", "structure_family", "partner_mode", "policy_name"):
            if key in result:
                grouped[f"{key}={result[key]}"].append(result)
    return {
        "overall": summarize(results),
        "groups": {key: summarize(rows) for key, rows in sorted(grouped.items())},
    }


def evaluate_dataset(*, dataset: str | Path, output: str | Path,
                     policy_spec: str, partner_mode: str = "adaptive",
                     seed_offset: int = 0, split: str | None = None,
                     backend_factory=ContinuousWorld) -> dict[str, Any]:
    """用一个模型策略重新评测已有场景，保持场景和分割不变。"""
    dataset = Path(dataset)
    output = Path(output)
    _ensure_empty_or_missing(output)
    episodes = iter_dataset(dataset, split=split)
    if not episodes:
        raise ValueError(f"数据集中没有匹配的 episode：{dataset}")
    policy_name = _safe_name(policy_spec)
    policy = load_continuous_policy(policy_spec)
    results: list[dict[str, Any]] = []
    for episode_dir, scenario in episodes:
        source_metrics = episode_dir / "metrics.json"
        source = json.loads(source_metrics.read_text(encoding="utf-8")) if source_metrics.exists() else {}
        run_seed = int(source.get("seed", 0)) + seed_offset
        target = output / policy_name / scenario.structure.split / episode_dir.name
        result = run_continuous_episode(
            scenario, policy, make_partner(scenario, partner_mode), seed=run_seed,
            output=target, partner_mode=partner_mode,
            backend_factory=backend_factory,
        )
        result.update({
            "dataset_version": DATASET_VERSION,
            "episode_id": f"{scenario.structure.split}/{episode_dir.name}",
            "source_episode": str(episode_dir),
            "policy_spec": policy_spec,
            "policy_name": policy_name,
        })
        (target / "metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append(result)
    output.mkdir(parents=True, exist_ok=True)
    summary = aggregate_results(results)
    payload = {
        "dataset_version": DATASET_VERSION,
        "dataset": str(dataset),
        "policy_spec": policy_spec,
        "partner_mode": partner_mode,
        "split": split,
        "episode_count": len(results),
        "backends": sorted({result["backend"] for result in results}),
        "episodes": results,
        **summary,
    }
    (output / f"{policy_name}.summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
