#!/usr/bin/env python3
"""独立读取保存的原生 VLA 产物，核对像素、动作块、关节转换和视频解码。"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image

from hrc_pilot.robot_control import droid_action_to_joint_target


def verify_episode(directory):
    rows = [json.loads(line) for line in (directory / "policy_io.jsonl").read_text().splitlines()]
    assert rows, "没有实际策略记录，不能证明模型运行"
    checks = []
    calls = set()
    for row in rows:
        audit, observation = row["adapter"], row["observation"]
        index = audit["executed_chunk_index"]
        raw = audit["raw_action_chunk"][index]
        assert np.allclose(row["action"]["joints"], droid_action_to_joint_target(raw, observation["robot_qpos"]))
        assert row["action"]["kind"] == "joint_position"
        assert row["action"]["control_mode"] == "droid_velocity_to_joint_position"
        if audit["model_call"] in calls:
            continue
        calls.add(audit["model_call"])
        assert index == 0
        for artifact, hash_key in (("rgb_artifact", "exterior_rgb_sha256"),
                                   ("wrist_rgb_artifact", "wrist_rgb_sha256")):
            pixels = np.asarray(Image.open(directory / observation[artifact]).convert("RGB"))
            assert sha256(pixels.tobytes()).hexdigest() == audit[hash_key]
        assert audit["model_input_keys"] == ["observation/exterior_image_1_left", "observation/wrist_image_left",
                                             "observation/joint_position", "observation/gripper_position", "prompt"]
        chunk = np.asarray(audit["raw_action_chunk"])
        assert chunk.ndim == 2 and chunk.shape[1] == 8 and np.isfinite(chunk).all()
        checks.append({"model_call": audit["model_call"], "step_time_s": row["step"],
                       "chunk_shape": list(chunk.shape), "elapsed_ms": audit["elapsed_ms"],
                       "actual_exterior_and_wrist_pixels_match": True})
    reader = imageio.get_reader(directory / "demo.mp4")
    metadata = reader.get_meta_data()
    count = sum(1 for _ in reader)
    reader.close()
    timeline = json.loads((directory / "video_timeline.json").read_text())
    assert count == timeline["frame_count"] and abs(metadata["fps"] - timeline["fps"]) < 1e-8
    metrics = json.loads((directory / "metrics.json").read_text())
    verification = {
        "runtime_model_calls": len(calls), "native_joint_actions": len(rows),
        "all_joint_targets_reconstructed": True, "real_sim_pixels_verified": True,
        "model_input_boundary_verified": True, "calls": checks,
        "video": {"complete_decode": True, "decoded_frames": count, "fps": metadata["fps"]},
        "task_success": metrics["task_success"],
        "interpretation": "记录链路核查，不推断 HRC、真实接触或模型泛化能力。",
    }
    control_path = directory / "robot_control.jsonl"
    if control_path.exists():
        controls = [json.loads(line) for line in control_path.read_text().splitlines()]
        cursor = 0
        for control in controls:
            while cursor + 1 < len(rows) and rows[cursor + 1]["step"] <= control["time_s"] + 1e-8:
                cursor += 1
            assert np.allclose(control["requested_target"], rows[cursor]["action"]["joints"])
        assert controls, "缺少实际控制目标"
        verification["physics_control_requests_match_model_actions"] = True
    return verification


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.input_dir
    directories = sorted(path.parent for path in root.rglob("metrics.json"))
    assert directories, "没有 episode，不能证明模型运行"
    episodes = []
    for directory in directories:
        verification = verify_episode(directory)
        verification["episode"] = directory.relative_to(root).as_posix()
        episodes.append(verification)
    verification = {
        "status": "verified", "episode_count": len(episodes), "episodes": episodes,
        "runtime_model_calls": sum(row["runtime_model_calls"] for row in episodes),
        "native_joint_actions": sum(row["native_joint_actions"] for row in episodes),
        "all_joint_targets_reconstructed": all(row["all_joint_targets_reconstructed"] for row in episodes),
        "real_sim_pixels_verified": all(row["real_sim_pixels_verified"] for row in episodes),
        "model_input_boundary_verified": all(row["model_input_boundary_verified"] for row in episodes),
        "interpretation": "实际像素、动作块、关节转换和请求目标链路核查；不推断 HRC、真人效度或模型泛化能力。",
    }
    if len(episodes) == 1:
        verification.update({key: episodes[0][key] for key in ("calls", "video", "task_success")})
    (root / "model_execution_verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2))
    print(f"核查通过：{len(episodes)} 个 episode，{verification['runtime_model_calls']} 次模型推理，"
          f"{verification['native_joint_actions']} 个关节目标")


if __name__ == "__main__":
    main()
