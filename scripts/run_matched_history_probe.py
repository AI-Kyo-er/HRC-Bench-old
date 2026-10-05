#!/usr/bin/env python3
"""运行真实历史来源与匹配当前输入的伙伴状态消融，保存 Genesis 视频。"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

from hrc_pilot.backend_options import add_backend_options, backend_provenance, configure_backend
from hrc_pilot.continuous import AdaptivePartner, GreedyPublicPolicy, run_continuous_episode, load_scenario
from hrc_pilot.continuous_report import write_continuous_report
from hrc_pilot.history_probe import (HelpThenExecutePolicy, HistoryCarryoverPartner,
                                    make_history_prefix, make_history_probe, read_public_history)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_backend_options(parser)
    parser.set_defaults(backend="genesis", experiment_tier="important", resolution=480)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--prefix-source", type=Path, default=None,
                        help="复用完整既有 prefix 的公开记录；复制原始产物并保留来源，不重新生成历史")
    args = parser.parse_args()
    if len(args.seeds) != len(set(args.seeds)):
        parser.error("seeds 不能重复")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("输出目录已有内容，请使用新目录保留历史证据")
    args.policy = "greedy_public / help_then_execute"
    backend = configure_backend(args, parser, args.output_dir)
    results = []
    probe = make_history_probe()
    comparisons = []

    def record(scenario, policy, partner, seed, directory, **labels):
        result = run_continuous_episode(scenario, policy, partner, seed=seed, output=directory,
                                        backend_factory=backend,
                                        partner_mode="adaptive_frozen" if getattr(partner, "frozen", False) else "adaptive")
        result.update(labels)
        (directory / "metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        results.append(result)
        return result

    for seed in args.seeds:
        seed_dir = args.output_dir / f"seed_{seed:03d}"
        sources = {}
        for history, failures in (("reliable", 0), ("failures", 3)):
            scenario = make_history_prefix(f"prefix_{history}", failures=failures)
            directory = seed_dir / "prefix" / scenario.name
            if args.prefix_source is not None:
                source = args.prefix_source / f"seed_{seed:03d}" / "prefix" / scenario.name
                scenario = load_scenario(source / "scenario.json")
                prefix = json.loads((source / "metrics.json").read_text())
                if prefix["seed"] != seed or prefix.get("backend") != backend_provenance(args)["backend"]:
                    raise ValueError(f"历史来源 seed / 后端不匹配：{source}")
                shutil.copytree(source, directory)
                results.append(prefix)
            else:
                prefix = record(scenario, GreedyPublicPolicy(), AdaptivePartner(scenario), seed,
                                directory, policy_name="greedy_public", history_condition=history)
            if not prefix["task_success"]:
                raise RuntimeError(f"历史来源任务未完成，不能形成完成度匹配：{directory}")
            sources[history] = (scenario, directory)

        group = []
        for frozen in (False, True):
            for history, (source_scenario, source_directory) in sources.items():
                mode = "frozen" if frozen else "adaptive"
                directory = seed_dir / "probe" / f"{history}_{mode}" / probe.name
                partner = HistoryCarryoverPartner(probe, history_scenario=source_scenario,
                                                 history_records=read_public_history(source_directory), frozen=frozen)
                result = record(probe, HelpThenExecutePolicy(), partner, seed, directory,
                                policy_name="help_then_execute", history_condition=history,
                                probe_kind="matched_current_input")
                calls = [json.loads(line) for line in (directory / "policy_io.jsonl").read_text().splitlines()]
                first_input = dict(calls[0]["observation"])
                image = first_input.pop("rgb_artifact", None)
                first_hash = sha256(json.dumps(first_input, sort_keys=True).encode()).hexdigest()
                image_hash = sha256((directory / image).read_bytes()).hexdigest() if image else None
                events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
                replies = [event for event in events if event["kind"] == "public_message"
                           and event.get("message_kind") == "help_reply"]
                request_input = next(row for row in partner.probe_inputs if any(
                    message["speaker"] == "robot" and message["kind"] == "request_help"
                    for message in row["observation"]["messages"]))
                audit = {
                    "seed": seed, "history_condition": history, "frozen": frozen,
                    "source_episode": source_directory.relative_to(args.output_dir).as_posix(),
                    "source_public_observations_sha256": sha256((source_directory / "public_observations.jsonl").read_bytes()).hexdigest(),
                    "learned_source_state": partner.source_state,
                    "probe_initial_state": partner.probe_initial_state,
                    "history_state_updates": partner.history_updates,
                    "first_model_input_sha256": first_hash, "first_rgb_sha256": image_hash,
                    "first_action": calls[0]["action"],
                    "request_partner_input_sha256": request_input["public_input_sha256"],
                    "request_partner_rgb_sha256": request_input["rgb_pixels_sha256"],
                    "help_reply": replies[0].get("value") if replies else None,
                    "activity_success": result["task_success"],
                    "robot_role_success": result["robot_role_success"],
                    "interpretation": "重新构造匹配世界和协议上下文，仅带入公开历史形成的 trust / reliability；不是无重置自然活动。",
                }
                (directory / "history_probe.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2))
                (directory / "partner_inputs.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False)
                    for row in partner.probe_inputs) + "\n")
                group.append(audit)
        comparison = {
            "seed": seed,
            "same_first_model_input": len({row["first_model_input_sha256"] for row in group}) == 1,
            "same_first_rgb": len({row["first_rgb_sha256"] for row in group}) == 1,
            "same_first_action": all(row["first_action"] == group[0]["first_action"] for row in group),
            "same_request_partner_input": len({row["request_partner_input_sha256"] for row in group}) == 1,
            "same_request_partner_rgb": len({row["request_partner_rgb_sha256"] for row in group}) == 1,
            "adaptive_reply_divergence": len({row["help_reply"] for row in group if not row["frozen"]}) > 1,
            "frozen_reply_divergence": len({row["help_reply"] for row in group if row["frozen"]}) > 1,
            "probes": group,
        }
        comparisons.append(comparison)
    (args.output_dir / "summary.json").write_text(json.dumps({"episodes": results}, ensure_ascii=False, indent=2))
    (args.output_dir / "matched_history_verification.json").write_text(json.dumps({
        "comparisons": comparisons,
        "verified_matching": all(row["same_first_model_input"] and row["same_first_rgb"] and row["same_first_action"]
                                 and row["same_request_partner_input"] and row["same_request_partner_rgb"] for row in comparisons),
    }, ensure_ascii=False, indent=2))
    (args.output_dir / "provenance.json").write_text(json.dumps({
        **backend_provenance(args), "policy": args.policy, "seeds": args.seeds,
        "experiment": "matched_history_probe", "run_count": len(results),
        "prefix_source": str(args.prefix_source.resolve()) if args.prefix_source else None,
        "purpose": "检查真实公开历史形成的伙伴判断是否改变后续相同求助的回答，并与冻结状态对照。",
        "controlled": "同 seed 探针固定当前物理状态、当前消息、任务、首次动作与相机；只带入 trust / reliability 或冻结其更新。",
        "interpretation": "模拟伙伴机制诊断，世界和协议在探针前重建；不是持续无重置 benchmark，也不是真人或训练具身模型证据。",
    }, ensure_ascii=False, indent=2))
    print(json.dumps([{key: value for key, value in row.items() if key != "probes"} for row in comparisons], ensure_ascii=False, indent=2))
    print(write_continuous_report(args.output_dir, results))


if __name__ == "__main__":
    main()
