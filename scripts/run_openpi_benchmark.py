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
from hrc_pilot.continuous import AdaptivePartner, run_continuous_episode
from hrc_pilot.continuous_report import write_continuous_report
from hrc_pilot.history_probe import make_history_probe
from hrc_pilot.openpi_adapter import DroidVLAAdapter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_backend_options(parser)
    parser.set_defaults(backend="genesis", experiment_tier="important", resolution=480, render_stride=4)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--ticks", type=int, default=90)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--execution-horizon", type=int, default=8)
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
    scenario = replace(make_history_probe(), name="pi05_droid_native", tick_hz=15.0,
                       description="Pick up the blue cup and place it on the blue mat.", max_steps=args.ticks)
    policy = DroidVLAAdapter(client.infer, execution_horizon=args.execution_horizon)
    result = run_continuous_episode(scenario, policy, AdaptivePartner(scenario),
                                    seed=args.seed, output=args.output_dir / scenario.name,
                                    backend_factory=factory)
    policy_io = [json.loads(line) for line in (args.output_dir / scenario.name / "policy_io.jsonl").read_text().splitlines()]
    calls = {row["adapter"]["model_call"]: row["adapter"] for row in policy_io}
    openpi = Path("/data1/sieniwgroup/sieniw/projects/HRC-Bench/external/openpi")
    provenance = {
        **backend_provenance(args), "policy": args.policy, "seed": args.seed,
        "experiment": "native_vla_pilot", "trained_model": True,
        "model_server_metadata": metadata,
        "openpi_commit": subprocess.check_output(["git", "-C", str(openpi), "rev-parse", "HEAD"], text=True).strip(),
        "control_hz": 15, "execution_horizon": args.execution_horizon,
        "model_calls": len(calls), "action_chunks": [len(call["raw_action_chunk"]) for call in calls.values()],
        "purpose": "核查真实训练模型接收运行时双相机和本体状态、输出动作块并闭环驱动机械臂的链路。",
        "controlled": "蓝杯收纳，伙伴仅观察；模型只看真实外部 / 腕部 RGB、7 个臂关节、夹爪状态和公开语言。没有几何坐标或内部伙伴状态输入，也不调用语义 transfer。",
        "interpretation": "单任务单 seed 的原生 VLA 接入实验，不是 HRC 能力排行榜。场景与 DROID 实机训练分布存在差异；抓放仍是运动学绑定，模型不会被包装器代替生成求助。",
        "sampling": "官方 OpenPI Policy 使用从 0 初始化并随调用推进的采样 RNG；本次未把场景 seed 声称为模型采样重置。",
    }
    (args.output_dir / "summary.json").write_text(json.dumps({"episodes": [result]}, ensure_ascii=False, indent=2))
    (args.output_dir / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2))
    print(f"真实模型调用 {len(calls)} 次；活动成功：{result['task_success']}")
    print(write_continuous_report(args.output_dir, [result]))


if __name__ == "__main__":
    main()
