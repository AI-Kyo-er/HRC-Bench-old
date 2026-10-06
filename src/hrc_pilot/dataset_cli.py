"""HRC-Continuous 数据集生成与批量模型评测 CLI。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .backend_options import add_backend_options, backend_provenance, configure_backend
from .continuous_report import write_continuous_report
from .dataset import evaluate_dataset, generate_dataset
from .video_verification import verify_result


def _policy_output_name(policy_spec: str) -> str:
    return policy_spec.replace(":", "_").replace("/", "_").replace("\\", "_")


def finalize_dataset_run(output: Path, command: str, policy_spec: str,
                         provenance: dict) -> tuple[Path, Path | None]:
    """为数据集运行写入视频核验和离线报告；重要视频不完整时直接失败。"""
    output = Path(output)
    (output / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    video_verification = None
    if provenance.get("sim_video_required"):
        video_verification = output / "video_verification.json"
        verification = verify_result(output, require_timeline=True)
        video_verification.write_text(
            json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")
        if verification["status"] != "verified":
            raise RuntimeError(f"重要实验真实 Sim 视频核验失败：{video_verification}")
    summary_name = "summary.json" if command == "generate" else f"{_policy_output_name(policy_spec)}.summary.json"
    summary = json.loads((output / summary_name).read_text(encoding="utf-8"))
    report = write_continuous_report(output, summary["episodes"])
    return report, video_verification


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
    generate.add_argument("--task-catalog", action="store_true",
                          help="生成九类可组合任务族，而不是默认结构 suite")
    generate.add_argument("--count-per-family", type=int, default=1,
                          help="--task-catalog 每个任务族的实例数")
    generate.add_argument("--repeats", type=int, default=1)
    generate.add_argument("--no-suite", action="store_true")
    generate.add_argument("--partner-mode", choices=("fixed_replay", "reactive", "adaptive", "dynamic"), default="adaptive")
    generate.add_argument("--policy", default="greedy_public",
                          help="生成参考轨迹时使用的策略 spec；仅作为数据集基线")

    evaluate = subparsers.add_parser("evaluate", help="在已有 episode 上批量运行模型")
    evaluate.add_argument("--dataset", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.add_argument("--policy", required=True,
                          help="greedy_public 或 module:factory；factory 返回 Policy")
    evaluate.add_argument("--partner-mode", choices=("fixed_replay", "reactive", "adaptive", "dynamic"), default="adaptive")
    evaluate.add_argument("--split", choices=("train", "dev", "test"), default=None)
    evaluate.add_argument("--seed-offset", type=int, default=0)
    for subparser in (generate, evaluate):
        add_backend_options(subparser)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("输出目录已有内容，请使用新的目录，避免覆盖已有实验。")
    backend_factory = configure_backend(args, parser, args.output)
    if args.command == "generate":
        metadata = generate_dataset(
            output=args.output, count=args.count, seed=args.seed,
            suite=not args.no_suite and not args.task_catalog,
            task_catalog=args.task_catalog, count_per_family=args.count_per_family,
            repeats=args.repeats, partner_mode=args.partner_mode, policy_spec=args.policy,
            scenario_dir=args.scenario_dir,
            backend_factory=backend_factory,
        )
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
    else:
        summary = evaluate_dataset(
            dataset=args.dataset, output=args.output, policy_spec=args.policy,
            partner_mode=args.partner_mode, seed_offset=args.seed_offset, split=args.split,
            backend_factory=backend_factory,
        )
        print(json.dumps(summary["overall"], ensure_ascii=False, indent=2))
    provenance = {
        **backend_provenance(args), "command": args.command,
        "policy": args.policy, "partner_mode": args.partner_mode,
        "observation_boundary": "public_observation_only",
    }
    report, video_verification = finalize_dataset_run(
        args.output, args.command, args.policy, provenance)
    print(f"[dataset] 报告：{report}")
    if video_verification is not None:
        print(f"[dataset] 视频核验：{video_verification}")


if __name__ == "__main__":
    main()
