"""安装后可调用的持续 benchmark CLI。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .continuous import generate_scenarios, run_catalog
from .continuous_report import write_continuous_report


def main() -> None:
    parser = argparse.ArgumentParser(description="HRC-Continuous v2 连续协作参考 benchmark")
    parser.add_argument("--output-dir", type=Path,
                        default=Path("/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/formal"))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--policy", default="greedy_public")
    parser.add_argument("--generated", type=int, default=0,
                        help="生成多少个随机任务实例；0 表示运行六个参考条件")
    parser.add_argument("--scenario-seed", type=int, default=None,
                        help="任务实例生成种子，默认沿用 --seed")
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("输出目录已有内容，请使用新的目录，避免覆盖已有实验。")
    scenarios = generate_scenarios(args.generated,
                                   seed=args.seed if args.scenario_seed is None else args.scenario_seed)
    results = run_catalog(policy_spec=args.policy, seed=args.seed, output=args.output_dir,
                          scenarios=scenarios or None)
    (args.output_dir / "provenance.json").write_text(json.dumps({
        "runtime": "hrc_pilot.continuous", "backend": "ContinuousWorld",
        "policy": args.policy, "seed": args.seed,
        "generated": args.generated,
        "scenario_seed": args.seed if args.scenario_seed is None else args.scenario_seed,
        "observation_boundary": "public_observation_only", "scenario_count": len(results),
    }, ensure_ascii=False, indent=2))
    print(f"[continuous] 结果：{write_continuous_report(args.output_dir, results, scenarios or None)}")


if __name__ == "__main__":
    main()
