#!/usr/bin/env python3
"""运行多 seed 的接管恢复、自行恢复、持续失败和无失败对照，保留真实 Sim 视频。"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

from hrc_pilot.backend_options import add_backend_options, backend_provenance, configure_backend
from hrc_pilot.continuous import CONTINUOUS_SCENARIOS, run_catalog, scenario_to_dict
from hrc_pilot.continuous_report import write_continuous_report
from hrc_pilot.dataset import aggregate_results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_backend_options(parser)
    parser.set_defaults(backend="genesis", resolution=480)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--conditions", nargs="+", choices=(
        "failure_handoff", "failure_no_handoff", "no_failure", "persistent_failure"),
        default=None)
    args = parser.parse_args()
    args.policy = "greedy_public"
    if len(args.seeds) != len(set(args.seeds)):
        parser.error("seeds 不能重复")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("输出目录已有内容，请使用新的目录保留历史证据")
    backend = configure_backend(args, parser, args.output_dir)
    base = replace(CONTINUOUS_SCENARIOS["relay"], max_steps=30)
    scenarios = [
        replace(base, name=name, description=description,
                dynamics=replace(base.dynamics, robot_failure_budget=budget,
                                 robot_failure_probability=probability,
                                 handoff_on_failure_probability=handoff))
        for name, description, budget, probability, handoff in (
            ("failure_handoff", "一次动作启动失败后，伙伴可接管剩余贡献。", 1, 0.0, 1.0),
            ("failure_no_handoff", "相同失败条件，伙伴不通过失败消息接管；检查基线能否自行恢复。", 1, 0.0, 0.0),
            ("no_failure", "相同任务、布局分布和时限，无合成失败预算。", 0, 0.0, 1.0),
            ("persistent_failure", "每次机器人搬运均合成失败且伙伴不接管；仅用于核查未恢复分类。", 0, 1.0, 0.0),
        )
        if args.conditions is None or name in args.conditions
    ]
    results = []
    for seed in args.seeds:
        results.extend(run_catalog(policy_spec=args.policy, seed=seed,
                                   output=args.output_dir / f"seed_{seed:03d}",
                                   scenarios=scenarios, partner_mode="adaptive", backend_factory=backend))
    summary = aggregate_results(results)
    summary["by_scenario"] = {
        scenario.name: aggregate_results([row for row in results if row["scenario"] == scenario.name])["overall"]
        for scenario in scenarios
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps({
        "episodes": results, "aggregate": summary,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "provenance.json").write_text(json.dumps({
        **backend_provenance(args), "policy": args.policy, "seeds": args.seeds,
        "partner_mode": "adaptive", "run_count": len(results),
        "scenario_count": len(scenarios), "observation_boundary": "public_observation_only",
        "experiment": "failure_recovery_controls",
        "purpose": "检查合成失败是否改变公开分工和活动结果，区分接管恢复、自行恢复、未恢复与无失败。",
        "controlled": "同一 seed 内布局、初始目标、活动前置依赖和 30 tick 时限相同。",
        "conditions": [scenario_to_dict(scenario) for scenario in scenarios],
        "negative_control": "persistent_failure 改变失败持续性，仅用于核查分类，不用于估计一次失败后接管的因果效果。",
        "interpretation": "手写策略与模拟伙伴的机制验证，不是 VLA/WLA 性能或真人效度证据。",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary["by_scenario"], ensure_ascii=False, indent=2))
    print(f"[recovery] 报告：{write_continuous_report(args.output_dir, results, scenarios)}")


if __name__ == "__main__":
    main()
