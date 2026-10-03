"""Run the embodied pilot and write reviewable videos, policy inputs and metrics."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from .evaluation import evaluate
from .partner import ResponsivePartner
from .policies import load_policy
from .protocol import Message, serialize
from .scenarios import SCENARIOS

PROJECT_DATA = Path("/data1/sieniwgroup/sieniw/projects/HRC-Bench")


def run_episode(workspace, scenario, policy_spec, output, seed, max_decisions):
    policy = load_policy(policy_spec)
    policy.reset()
    partner = ResponsivePartner(scenario)
    workspace.begin_episode(output, scenario.name, policy_spec, seed)
    for message in partner.initial_messages():
        workspace.say(message)
    workspace.tick(30)
    workspace.inspect_and_respond(partner)
    checkpoint = {"objects": workspace.positions(), "robot_qpos": workspace.robot.get_qpos().cpu().tolist(),
                  "human_position": workspace.avatar.get_global_pose().tolist()}
    (output / "post_intervention_state.json").write_text(json.dumps(checkpoint, indent=2))
    (output / "initial_public_history.json").write_text(json.dumps(workspace.messages, default=serialize,
                                                                  ensure_ascii=False, indent=2))
    decision_log = []
    completed = False
    for decision in range(max_decisions):
        observation = workspace.observe()
        action = policy.act(observation)
        decision_log.append({"decision": decision, "step": workspace.step_count,
                             "observation": serialize(observation), "action": serialize(action)})
        workspace.log.add(workspace.step_count, "policy_action", action=serialize(action))
        if action.kind == "transfer":
            if action.object_id not in workspace.objects or action.destination not in workspace.regions:
                raise ValueError(f"Invalid transfer: {action}")
            workspace.robot_transfer(action.object_id, action.destination)
        elif action.kind in {"request_help", "acknowledge"}:
            workspace.log.add(workspace.step_count, "robot_message", action=action.kind, text=action.text)
            workspace.say(Message("robot", action.kind, action.text, action.object_id))
            workspace.tick(30)
            if action.kind == "request_help":
                reply, accepted = partner.on_public_request(action.object_id, workspace.held_by_human())
                workspace.say(reply)
                if accepted:
                    workspace.human_transfer(action.object_id, action.destination)
                workspace.tick(30)
        elif action.kind == "wait":
            workspace.current_robot_action = "等待伙伴贡献"
            workspace.tick(40)
        elif action.kind == "joint_position":
            workspace.joint_position_step(action.joints)
        elif action.kind == "finish":
            completed = True
            workspace.current_robot_action = "策略宣布完成；评测器检查实物位置"
            break
        else:
            raise ValueError(f"Unknown action: {action.kind}")
    workspace.finish_episode()
    metrics = evaluate(scenario, workspace.positions(), workspace.regions, workspace.log.events, completed)
    metrics.update({"scenario": scenario.name, "policy": policy_spec, "seed": seed,
                    "decisions": len(decision_log), "sim_steps": workspace.step_count})
    (output / "policy_io.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in decision_log) + "\n")
    (output / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2))
    return metrics


def write_report(output, results, provenance):
    from .report import write_dashboard
    import numpy as np
    scalar_keys = [k for k in results[0] if k != "final_positions"]
    with (output / "episodes.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=scalar_keys)
        writer.writeheader()
        writer.writerows({k: row[k] for k in scalar_keys} for row in results)
    expected = len(provenance["arguments"]["seeds"]) * len(provenance["arguments"]["scenarios"]) * len(provenance["arguments"]["policies"])
    summary = {"status": "complete" if len(results) == expected else "partial", "expected_episodes": expected,
               "scope": "mechanism_and_simulator_pilot_not_model_validation",
               "provenance": provenance, "episodes": results}
    pair_audits = []
    for policy in provenance["arguments"]["policies"]:
        for seed in provenance["arguments"]["seeds"]:
            paths = [output / f"{name}__{policy.replace(':', '_')}__seed{seed}" / "post_intervention_state.json"
                     for name in ("history_keep", "history_pack")]
            if all(path.exists() for path in paths):
                a, b = [json.loads(path.read_text()) for path in paths]
                differences = {"objects": max(float(np.max(np.abs(np.array(a["objects"][name])-b["objects"][name])))
                                               for name in ("red", "blue")),
                               "robot_qpos": float(np.max(np.abs(np.array(a["robot_qpos"])-b["robot_qpos"]))),
                               "human_position": float(np.max(np.abs(np.array(a["human_position"])-b["human_position"])))}
                pair_audits.append({"policy": policy, "seed": seed, "max_absolute_differences": differences,
                                    "matched_within_tolerance": differences["objects"] < 1e-5
                                    and differences["robot_qpos"] < 1e-3 and differences["human_position"] < 1e-5})
    summary["history_pair_audits"] = pair_audits
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    write_dashboard(output, results)


def main():
    parser = argparse.ArgumentParser(description="VC/Genesis 合作重平衡基础 demo")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_DATA / "results/pilot_v1/formal")
    parser.add_argument("--assets-dir", type=Path, default=PROJECT_DATA / "assets/virtual-community")
    parser.add_argument("--scenarios", nargs="+", choices=list(SCENARIOS), default=list(SCENARIOS))
    parser.add_argument("--policies", nargs="+", default=["memory", "static", "reactive"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[0])
    parser.add_argument("--backend", choices=["gpu", "cpu"], default="gpu")
    parser.add_argument("--resolution", type=int, default=800)
    parser.add_argument("--render-stride", type=int, default=3)
    parser.add_argument("--max-decisions", type=int, default=12)
    parser.add_argument("--viewer", action="store_true")
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("输出目录已有内容，请使用新的目录，避免覆盖已有实验。")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.backend == "gpu":
        gpu_rows = subprocess.check_output([
            "nvidia-smi", "--query-gpu=index,memory.free", "--format=csv,noheader,nounits"
        ], text=True)
        free = {row.split(",")[0].strip(): int(row.split(",")[1]) for row in gpu_rows.splitlines()}
        selected = os.environ.get("CUDA_VISIBLE_DEVICES")
        if selected is None:
            selected = max(free, key=free.get)
            os.environ["CUDA_VISIBLE_DEVICES"] = selected
        if selected not in free or free[selected] < 4096:
            parser.error("此小型仿真估计需要 4 GB 空闲显存；请指定一张有足够显存的 GPU。")
        print(f"[pilot] GPU {selected}: {free[selected]} MiB 空闲，仿真预估显存不超过 4 GB。", flush=True)
    # Must be set before importing Genesis/OpenGL. All runtime caches use the data disk.
    os.environ.setdefault("GS_CACHE_FILE_PATH", str(PROJECT_DATA / "cache/genesis-vico"))
    os.environ.setdefault("HF_HOME", str(PROJECT_DATA / "cache/huggingface"))
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    os.environ.setdefault("VICO_ASSET_PATHS", str(args.assets_dir))
    os.environ["VICO_PILOT_MINIMAL_IMPORTS"] = "1"
    from .backend import VCWorkspace
    provenance = {"genesis_revision": "cdbe596f23220b8134434dd0946039c4f493ab5a",
                  "vc_revision": "b1ace3b2d130746a52cac1ec0c1de05f4f90deec",
                  "asset_revision": "2325ce34be748231ab6d4197a2b525eef16cc10f",
                  "vc_patch": "patches/vc-pilot-minimal-imports.patch",
                  "backend": args.backend, "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                  "grasp_model": "kinematic_attachment", "perception": "simulator_semantic_geometry_and_rgb",
                  "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in Path(__file__).parent.glob("*.py")},
                  "arguments": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}}
    import importlib.metadata
    provenance["package_versions"] = {name: importlib.metadata.version(name)
        for name in ("genesis-world", "virtual-community", "torch", "numpy", "numba", "gstaichi")}
    (args.output_dir / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2))
    workspace = VCWorkspace(assets=args.assets_dir, backend=args.backend, resolution=args.resolution,
                            render_stride=args.render_stride, viewer=args.viewer)
    results = []
    try:
        for seed in args.seeds:
            for scenario_name in args.scenarios:
                for policy_spec in args.policies:
                    episode = f"{scenario_name}__{policy_spec.replace(':', '_')}__seed{seed}"
                    print(f"[pilot] 开始 {episode}", flush=True)
                    started = time.monotonic()
                    metrics = run_episode(workspace, SCENARIOS[scenario_name], policy_spec,
                                          args.output_dir / episode, seed, args.max_decisions)
                    results.append(metrics)
                    print(f"[pilot] 完成 {episode}: success={metrics['task_success']}, "
                          f"steps={metrics['sim_steps']}, elapsed={time.monotonic()-started:.1f}s", flush=True)
                    write_report(args.output_dir, results, provenance)
    finally:
        workspace.close()
    print(f"[pilot] 结果：{args.output_dir / 'index.html'}", flush=True)


if __name__ == "__main__":
    main()
