"""HRC-Continuous 数据集生成与批量模型评测 CLI。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dataset import evaluate_dataset, generate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="生成和评测 HRC-Continuous episode 数据集")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="生成 train/dev/test episode 数据集")
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--seed", type=int, default=0)
    generate.add_argument("--count", type=int, default=0,
                          help="只生成随机场景；默认使用四类结构 suite")
    generate.add_argument("--scenario-dir", type=Path, default=None,
                          help="读取用户定义的 JSON 场景目录；文件名排序决定稳定顺序")
    generate.add_argument("--count-per-condition", type=int, default=2)
    generate.add_argument("--repeats", type=int, default=1)
    generate.add_argument("--no-suite", action="store_true")
    generate.add_argument("--partner-mode", choices=("fixed_replay", "reactive", "adaptive"), default="adaptive")
    generate.add_argument("--policy", default="greedy_public",
                          help="生成参考轨迹时使用的策略 spec；仅作为数据集基线")

    evaluate = subparsers.add_parser("evaluate", help="在已有 episode 上批量运行模型")
    evaluate.add_argument("--dataset", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.add_argument("--policy", required=True,
                          help="greedy_public 或 module:factory；factory 返回 Policy")
    evaluate.add_argument("--partner-mode", choices=("fixed_replay", "reactive", "adaptive"), default="adaptive")
    evaluate.add_argument("--split", choices=("train", "dev", "test"), default=None)
    evaluate.add_argument("--seed-offset", type=int, default=0)
    args = parser.parse_args()
    if args.command == "generate":
        metadata = generate_dataset(
            output=args.output, count=args.count, seed=args.seed,
            suite=not args.no_suite, count_per_condition=args.count_per_condition,
            repeats=args.repeats, partner_mode=args.partner_mode, policy_spec=args.policy,
            scenario_dir=args.scenario_dir,
        )
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
    else:
        summary = evaluate_dataset(
            dataset=args.dataset, output=args.output, policy_spec=args.policy,
            partner_mode=args.partner_mode, seed_offset=args.seed_offset, split=args.split,
        )
        print(json.dumps(summary["overall"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
