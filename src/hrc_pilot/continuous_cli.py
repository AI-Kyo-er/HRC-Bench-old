"""安装后可调用的持续 benchmark CLI。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .backend_options import add_backend_options, backend_provenance, configure_backend
from .continuous import (CONTINUOUS_SCENARIOS, generate_benchmark_suite, generate_scenarios, load_scenario,
                          load_scenario_catalog,
                          run_catalog, run_counterfactual_benchmark, run_paired_benchmark)
from .continuous_report import write_continuous_report


def main() -> None:
    parser = argparse.ArgumentParser(description="HRC-Continuous v2 连续协作参考 benchmark")
    parser.add_argument("--output-dir", type=Path,
                        default=Path("/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/formal"))
    parser.add_argument("--seed", type=int, default=0)
    add_backend_options(parser)
    parser.add_argument("--scenes", nargs="+", choices=tuple(CONTINUOUS_SCENARIOS), default=None)
    parser.add_argument("--policy", default="greedy_public")
    parser.add_argument("--generated", type=int, default=0,
                        help="生成多少个随机任务实例；0 表示运行六个参考条件")
    parser.add_argument("--scenario-file", type=Path, default=None,
                        help="读取一个用户定义的 JSON 活动契约；可与 --paired 一起使用")
    parser.add_argument("--scenario-dir", type=Path, default=None,
                        help="批量读取目录中的 JSON 场景契约；文件名决定稳定顺序")
    parser.add_argument("--scenario-seed", type=int, default=None,
                        help="任务实例生成种子，默认沿用 --seed")
    parser.add_argument("--partner-mode", choices=("fixed_replay", "reactive", "adaptive"),
                        default="adaptive", help="人类伙伴条件")
    parser.add_argument("--suite", action="store_true",
                        help="生成 isolated/matched_serial/compositional/held_out 条件集合")
    parser.add_argument("--paired", action="store_true",
                        help="在同一场景和 seed 上运行 fixed/reactive/adaptive 三种伙伴")
    parser.add_argument("--counterfactual-policies", default=None,
                        help="逗号分隔的策略 spec；同一场景/seed/伙伴下只改变机器人策略")
    parser.add_argument("--count-per-condition", type=int, default=2,
                        help="--suite 每个结构条件生成多少实例")
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("输出目录已有内容，请使用新的目录，避免覆盖已有实验。")
    scenario_seed = args.seed if args.scenario_seed is None else args.scenario_seed
    if args.scenario_file is not None and args.scenario_dir is not None:
        parser.error("--scenario-file 和 --scenario-dir 只能选择一个")
    if (args.scenario_file is not None or args.scenario_dir is not None) and (args.suite or args.generated):
        parser.error("自定义场景不能和 --suite/--generated 同时使用")
    if args.scenario_file is not None:
        scenarios = [load_scenario(args.scenario_file)]
    elif args.scenario_dir is not None:
        scenarios = load_scenario_catalog(args.scenario_dir)
    elif args.suite:
        scenarios = generate_benchmark_suite(count_per_condition=args.count_per_condition,
                                             seed=scenario_seed, include_reference=False)
    else:
        scenarios = generate_scenarios(args.generated, seed=scenario_seed)
    if args.scenes is not None:
        if args.scenario_file or args.scenario_dir or args.suite or args.generated:
            parser.error("--scenes 只用于选择内置场景")
        scenarios = [CONTINUOUS_SCENARIOS[name] for name in args.scenes]
    backend_factory = configure_backend(args, parser, args.output_dir)
    if args.paired and args.counterfactual_policies:
        parser.error("--paired 不能和 --counterfactual-policies 同时使用")
    if args.counterfactual_policies:
        policy_specs = tuple(spec.strip() for spec in args.counterfactual_policies.split(",") if spec.strip())
        results = run_counterfactual_benchmark(policy_specs=policy_specs, seed=args.seed,
                                               output=args.output_dir, scenarios=scenarios or None,
                                               partner_mode=args.partner_mode, backend_factory=backend_factory)
    elif args.paired:
        results = run_paired_benchmark(policy_spec=args.policy, seed=args.seed, output=args.output_dir,
                                       scenarios=scenarios or None, backend_factory=backend_factory)
    else:
        results = run_catalog(policy_spec=args.policy, seed=args.seed, output=args.output_dir,
                              scenarios=scenarios or None, partner_mode=args.partner_mode,
                              backend_factory=backend_factory)
    (args.output_dir / "provenance.json").write_text(json.dumps({
        "runtime": "hrc_pilot.continuous",
        **backend_provenance(args),
        "policy": args.policy, "seed": args.seed,
        "counterfactual_policies": args.counterfactual_policies,
        "generated": args.generated, "suite": args.suite,
        "scenario_file": str(args.scenario_file) if args.scenario_file else None,
        "scenario_dir": str(args.scenario_dir) if args.scenario_dir else None,
        "count_per_condition": args.count_per_condition,
        "partner_mode": ("counterfactual" if args.counterfactual_policies else
                          "paired" if args.paired else args.partner_mode),
        "paired": args.paired,
        "scenario_seed": scenario_seed,
        "observation_boundary": "public_observation_only",
        "scenario_count": len(scenarios), "run_count": len(results),
    }, ensure_ascii=False, indent=2))
    print(f"[continuous] 结果：{write_continuous_report(args.output_dir, results, scenarios or None)}")


if __name__ == "__main__":
    main()
