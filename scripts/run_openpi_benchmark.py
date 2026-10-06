#!/usr/bin/env python3
"""使用真实 π0.5-DROID 输出驱动 Genesis，保存双相机、动作块、视频和独立评分。"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import subprocess

from openpi_client.websocket_client_policy import WebsocketClientPolicy

from hrc_pilot.backend_options import add_backend_options, backend_provenance, configure_backend
from hrc_pilot.continuous import (AdaptivePartner, DynamicHumanPolicy, ReactivePartner,
                                   FixedReplayPartner, run_continuous_episode,
                                   CONTINUOUS_SCENARIOS, make_extended_task_catalog, load_scenario)
from hrc_pilot.continuous_report import write_continuous_report
from hrc_pilot.dataset import aggregate_results
from hrc_pilot.video_verification import finalize_video_verification
from hrc_pilot.history_probe import make_history_probe
from hrc_pilot.openpi_adapter import DroidVLAAdapter
from hrc_pilot.motion_continuity import verify_motion_continuity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_backend_options(parser)
    parser.set_defaults(backend="genesis", experiment_tier="important", resolution=480, render_stride=4)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--ticks", type=int, default=90)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--execution-horizon", type=int, default=8)
    parser.add_argument("--partner-mode", choices=("dynamic", "adaptive", "reactive", "fixed_replay", "qwen_llm"),
                        default="dynamic",
                        help="伙伴条件；重要纵切片默认使用带 profile/意图/记忆的动态伙伴")
    parser.add_argument("--human-profile", choices=("balanced", "assertive", "careful", "supportive"),
                        default="balanced", help="动态伙伴的稳定行为倾向")
    parser.add_argument("--deterministic-human", action="store_true",
                        help="关闭动态伙伴的 episode 内随机采样，便于调试")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--scenes", nargs="+", choices=tuple(CONTINUOUS_SCENARIOS))
    selection.add_argument("--task-catalog", action="store_true", help="运行九类活动契约任务族")
    selection.add_argument("--scenario-dir", type=Path, help="运行目录内的 JSON 活动契约")
    parser.add_argument("--count-per-family", type=int, default=1)
    parser.add_argument("--seeds", nargs="+", type=int, help="批量场景 seed；省略时使用 --seed")
    parser.add_argument("--human-model", type=Path,
                        default=Path("/data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B"))
    parser.add_argument("--human-persona", choices=("cooperative", "independent", "cautious", "assertive"),
                        default="cooperative")
    parser.add_argument("--human-decision-interval", type=int, default=15)
    args = parser.parse_args()
    args.policy = "pi05_droid_native"
    if args.backend != "genesis":
        parser.error("原生双相机模型实验要求 Genesis")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("请使用新输出目录")
    factory = configure_backend(args, parser, args.output_dir)
    client = WebsocketClientPolicy(host="127.0.0.1", port=args.port)
    metadata = client.get_server_metadata()
    if metadata.get("config") != "pi05_droid":
        parser.error("本地服务没有声明 pi05_droid 配置")
    if args.scenes:
        scenarios = [CONTINUOUS_SCENARIOS[name] for name in args.scenes]
    elif args.task_catalog:
        scenarios = make_extended_task_catalog(count_per_family=args.count_per_family, seed=args.seed)
    elif args.scenario_dir:
        scenarios = [load_scenario(path) for path in sorted(args.scenario_dir.glob("*.json"))]
    else:
        scenarios = [replace(make_history_probe(), name="pi05_droid_native",
                             human_targets={"red": "tray_red"}, robot_targets={"blue": "tray_blue"})]
    if not scenarios or args.ticks < 1 or args.count_per_family < 1:
        parser.error("需要非空场景目录、正的 ticks 和 count-per-family")
    scenarios = [replace(scenario, tick_hz=15.0, max_steps=args.ticks) for scenario in scenarios]
    results, episode_calls = [], []
    seeds = args.seeds or [args.seed]
    if len(seeds) != len(set(seeds)) or len(scenarios) != len({scenario.name for scenario in scenarios}):
        parser.error("场景名称和 seeds 必须各自唯一，避免覆盖已记录的 episode")
    generative_partner = None
    if args.partner_mode == "qwen_llm":
        from hrc_pilot.llm_human import QwenHumanPolicy
        generative_partner = QwenHumanPolicy(scenarios[0], model_path=args.human_model,
                                            persona_id=args.human_persona,
                                            decision_interval_steps=args.human_decision_interval)
    for scenario in scenarios:
        for seed in seeds:
            if args.partner_mode == "dynamic":
                partner = DynamicHumanPolicy(scenario, profile_id=args.human_profile,
                                             stochastic=not args.deterministic_human)
            elif args.partner_mode == "qwen_llm":
                partner = generative_partner
                partner.scenario = scenario
            elif args.partner_mode == "adaptive":
                partner = AdaptivePartner(scenario)
            elif args.partner_mode == "reactive":
                partner = ReactivePartner(scenario)
            else:
                partner = FixedReplayPartner(scenario)
            instruction = public_robot_instruction(scenario, physical=args.robot_grasp_model == "friction_contact")
            policy = DroidVLAAdapter(client.infer, instruction=instruction, execution_horizon=args.execution_horizon)
            directory = args.output_dir / scenario.name
            if len(seeds) > 1:
                directory /= f"seed_{seed:04d}"
            result = run_continuous_episode(scenario, policy, partner, seed=seed, output=directory,
                                            backend_factory=factory, partner_mode=args.partner_mode)
            if args.robot_grasp_model == "friction_contact":
                motion = verify_motion_continuity(directory)
                result["motion_verification_status"] = motion["status"]
                result["motion_check_passed"] = motion["benchmark_eligible"]
                (directory / "metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
            results.append(result)
            policy_io = [json.loads(line) for line in (directory / "policy_io.jsonl").read_text().splitlines()]
            calls = {row["adapter"]["model_call"]: row["adapter"] for row in policy_io}
            episode_calls.append({"scenario": scenario.name, "seed": seed, "model_calls": len(calls),
                                  "action_chunks": [len(call["raw_action_chunk"]) for call in calls.values()]})
            print(f"[native] {scenario.name} seed={seed}: 模型调用 {len(calls)}，活动成功 {result['task_success']}", flush=True)
    openpi = Path("/data1/sieniwgroup/sieniw/projects/HRC-Bench/external/openpi")
    provenance = {
        **backend_provenance(args), "policy": args.policy, "seed": args.seed, "seeds": seeds,
        "experiment": "native_vla_dynamic_partner_benchmark", "trained_model": True,
        "scenario_count": len(scenarios), "run_count": len(results), "episode_model_calls": episode_calls,
        "partner_mode": args.partner_mode,
        "human_profile": args.human_profile if args.partner_mode == "dynamic" else None,
        "deterministic_human": args.deterministic_human if args.partner_mode == "dynamic" else None,
        "human_model": str(args.human_model) if args.partner_mode == "qwen_llm" else None,
        "human_persona": args.human_persona if args.partner_mode == "qwen_llm" else None,
        "human_decision_interval": args.human_decision_interval,
        "model_server_metadata": metadata,
        "openpi_commit": subprocess.check_output(["git", "-C", str(openpi), "rev-parse", "HEAD"], text=True).strip(),
        "control_hz": 15, "execution_horizon": args.execution_horizon,
        "model_calls": sum(row["model_calls"] for row in episode_calls),
        "action_chunks": [value for row in episode_calls for value in row["action_chunks"]],
        "purpose": "在多种活动契约中执行真实训练模型，记录动态伙伴、物理操作和共同活动的原始结果。",
        "controlled": "模型只看真实外部 / 腕部 RGB、7 个臂关节、夹爪状态和公开任务语言。没有几何坐标、伙伴私有 profile/意图/记忆或 evaluator 状态输入，也不调用语义 transfer；不同任务使用其初始公开分工构造操作指令。",
        "interpretation": ("原生 VLA + 动态伙伴的真实接触运行。人体拿放仍为运动学抽象，场景与 DROID 实机训练分布存在差异；需先报告基础操作表现，再讨论交互能力，不能以基础操作失败直接推断没有 HRC 能力。"
                           if args.robot_grasp_model == "friction_contact" else
                           "原生 VLA + 动态伙伴运行，机器人抓放仍为运动学绑定，不是接触证据或成熟 HRC 排行榜。"),
        "sampling": "官方 OpenPI Policy 使用从 0 初始化并随调用推进的采样 RNG；本次未把场景 seed 声称为模型采样重置。",
    }
    passed_motion = [row for row in results if row.get("motion_check_passed", True)]
    (args.output_dir / "summary.json").write_text(json.dumps({
        "episodes": results, "aggregate": aggregate_results(passed_motion),
        "aggregate_scope": ("仅动作连续性通过的 episode；通过这一项仍不等于完整研究效度。"
                            if args.robot_grasp_model == "friction_contact" else
                            "运动学操作的诊断汇总，不作为真实接触能力排名。"),
        "excluded_motion_episode_count": len(results) - len(passed_motion),
        "diagnostic_aggregate": aggregate_results(results),
    }, ensure_ascii=False, indent=2))
    (args.output_dir / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2))
    finalize_video_verification(args.output_dir, required=bool(provenance["sim_video_required"]),
                                require_timeline=True)
    print(write_continuous_report(args.output_dir, results, scenarios))


def public_robot_instruction(scenario, *, physical):
    """Instruction uses public assignments, never private evaluator work items."""
    assignments = [message for message in scenario.initial_messages()
                   if message.kind == "assignment" and message.value == "robot"]
    noun = "block" if physical else "cup"
    instructions = [f"Pick up the {message.object_id} {noun} and place it on the {'green' if str(message.destination).startswith('keep') else 'blue'} mat."
                    for message in assignments]
    return "Then ".join(instructions) if instructions else "Assist the human with the publicly assigned task."


if __name__ == "__main__":
    main()
