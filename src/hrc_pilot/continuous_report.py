"""从保存的实验产物生成离线动画与研究复盘报告。"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any

from .continuous import ContinuousScenario


ARTIFACT_NAMES = (
    "metrics.json", "scenario.json", "trace.jsonl", "events.jsonl",
    "public_observations.jsonl", "policy_io.jsonl", "public_scenario.json",
    "demo.mp4", "preview.png", "trajectory.npz", "video_timeline.json", "history_probe.json", "partner_inputs.jsonl",
)


def _json_lines(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row.get("scenario"), row.get("seed"), row.get("partner_mode"),
            row.get("policy_name"), row.get("history_condition"))


def build_replay_payload(output: Path, results: list[dict[str, Any]]) -> dict[str, Any]:
    output = Path(output)
    candidates: dict[tuple[Any, ...], list[Path]] = defaultdict(list)
    for metrics_path in sorted(output.rglob("metrics.json")):
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        candidates[_identity(metrics)].append(metrics_path.parent)
    provenance_path = output / "provenance.json"
    provenance = (json.loads(provenance_path.read_text(encoding="utf-8"))
                  if provenance_path.exists() else {})
    episodes = []
    source_hashes = {}
    for result in results:
        matches = candidates.get(_identity(result), [])
        if len(matches) != 1:
            raise ValueError(f"无法唯一匹配 episode 产物：{_identity(result)}")
        directory = matches[0]
        scenario_path = directory / "scenario.json"
        scenario = (json.loads(scenario_path.read_text(encoding="utf-8"))
                    if scenario_path.exists() else {})
        trace = _json_lines(directory / "trace.jsonl")
        if not trace:
            raise ValueError(f"episode 缺少可回放轨迹：{directory}")
        for previous, current in zip(trace, trace[1:]):
            if current["time_s"] <= previous["time_s"]:
                raise ValueError(f"轨迹时间必须严格递增：{directory}")
        observations = _json_lines(directory / "public_observations.jsonl")
        events = _json_lines(directory / "events.jsonl")
        source = directory.relative_to(output).as_posix()
        artifacts = [name for name in ARTIFACT_NAMES if (directory / name).exists()]
        for name in artifacts:
            path = directory / name
            source_hashes[f"{source}/{name}"] = sha256(path.read_bytes()).hexdigest()
        episodes.append({
            "id": source, "metrics": result, "scenario": scenario,
            "trace": trace, "observations": observations, "events": events,
            "artifacts": artifacts,
            "video_timeline": (json.loads((directory / "video_timeline.json").read_text(encoding="utf-8"))
                               if (directory / "video_timeline.json").exists() else None),
            "history_probe": (json.loads((directory / "history_probe.json").read_text(encoding="utf-8"))
                              if (directory / "history_probe.json").exists() else None),
        })
    run_artifacts = [name for name in (
        "summary.json", "paired_summary.json", "provenance.json", "matched_history_verification.json",
        "model_execution_verification.json", "video_verification.json", "report_browser_verification.json",
    ) if (output / name).exists()]
    for name in run_artifacts:
        path = output / name
        # 浏览器核查产生于页面生成后，不把下游验收日志当作页面的来源。
        if path.exists() and name != "report_browser_verification.json":
            source_hashes[name] = sha256(path.read_bytes()).hexdigest()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for episode in episodes:
        grouped[episode["metrics"]["scenario"]].append(episode)
    comparisons = []
    for name, group in grouped.items():
        modes = {episode["metrics"].get("partner_mode") for episode in group}
        if len(group) > 1 and len(modes) == len(group):
            keys = ("time_s", "objects", "human_position", "robot_position",
                    "active_robot_action", "human_action")
            traces = [[{key: frame.get(key) for key in keys} for frame in episode["trace"]]
                      for episode in group]
            comparisons.append({
                "scenario": name,
                "trajectory_equal": all(trace == traces[0] for trace in traces[1:]),
                "steps": [len(episode["trace"]) for episode in group],
                "modes": [episode["metrics"].get("partner_mode") for episode in group],
            })
    return {
        "report_version": "continuous-replay-1", "run_name": output.name,
        "provenance": provenance, "episodes": episodes, "comparisons": comparisons,
        "source_hashes": source_hashes,
        "run_artifacts": run_artifacts,
        "matched_history_verification": (json.loads((output / "matched_history_verification.json").read_text(encoding="utf-8"))
                                         if (output / "matched_history_verification.json").exists() else None),
    }


def write_continuous_report(output: Path, results: list[dict[str, Any]],
                            scenarios: list[ContinuousScenario] | None = None) -> Path:
    output = Path(output)
    payload = build_replay_payload(output, results)
    path = output / "index.html"
    backup = output / "index.before-replay.html"
    payload["has_original_report"] = path.exists() or backup.exists()
    assets = Path(__file__).parent / "report_assets"
    document = (assets / "continuous_replay.html").read_text(encoding="utf-8")
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    document = document.replace("__REPORT_CSS__", (assets / "continuous_replay.css").read_text(encoding="utf-8"))
    document = document.replace("__REPORT_JS__", (assets / "continuous_replay.js").read_text(encoding="utf-8"))
    document = document.replace("__REPORT_DATA__", encoded)
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(document, encoding="utf-8")
    verification = {
        "report_version": payload["report_version"],
        "rendering": "recorded_xy_trajectory_canvas_replay",
        "simulation_rerun": False,
        "episode_count": len(payload["episodes"]),
        "recorded_frame_count": sum(len(episode["trace"]) for episode in payload["episodes"]),
        "source_sha256": payload["source_hashes"],
        "comparisons": payload["comparisons"],
        "terminal_state": "recorded terminal frame when present; no terminal frame synthesized",
    }
    (output / "replay_verification.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def rebuild_saved_report(output: str | Path) -> Path:
    output = Path(output)
    source = next((output / name for name in (
        "history_counterfactual_summary.json", "counterfactual_summary.json",
        "paired_summary.json", "summary.json") if (output / name).exists()), None)
    if source is None:
        raise FileNotFoundError(f"没有可重建的实验汇总：{output}")
    summary = json.loads(source.read_text(encoding="utf-8"))
    return write_continuous_report(output, summary["episodes"])
