"""核查物理轨迹中的人体拿放跳变与机器人控制目标速度。

这是运行资格检查，不是策略得分。允许保存失败诊断报告，但出现跳变的
episode 不应进入正式能力排名。阈值、发生时间和来源文件均保留供复核。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_motion_continuity(directory: Path, *, human_transport_speed_limit_m_s=1.5):
    directory = Path(directory)
    contact_path = directory / "contacts.jsonl"
    if not contact_path.is_file():
        result = {"status": "unverified", "benchmark_eligible": False,
                  "reason": "缺少逐物理步 contacts.jsonl，不能核验物体运动连续性。"}
    else:
        rows = read_rows(contact_path)
        violations = []
        maximum_human_displacement = 0.0
        for first, second in zip(rows, rows[1:]):
            dt = second["time_s"] - first["time_s"]
            if dt <= 0:
                violations.append({"kind": "nonmonotonic_clock", "time_s": second["time_s"]})
                continue
            for name, state in second["objects"].items():
                prior = first["objects"].get(name)
                if prior is None or not (prior["human_held"] or state["human_held"]):
                    continue
                displacement = float(np.linalg.norm(np.asarray(state["position"]) - prior["position"]))
                maximum_human_displacement = max(maximum_human_displacement, displacement)
                if displacement > human_transport_speed_limit_m_s * dt + 1e-5:
                    violations.append({"kind": "human_object_transport_jump", "object_id": name,
                                       "time_s": second["time_s"], "displacement_m": displacement,
                                       "interval_s": dt, "implied_speed_m_s": displacement / dt,
                                       "was_held": prior["human_held"], "now_held": state["human_held"]})
        control_path = directory / "robot_control.jsonl"
        contract_path = directory / "physics_contract.json"
        control_verified = control_path.is_file() and contract_path.is_file()
        if control_verified:
            controls = read_rows(control_path)
            contract = json.loads(contract_path.read_text())
            limits = np.array([contract["arm_target_speed_limit_rad_s"]] * 7
                              + [contract["finger_target_speed_limit_m_s"]] * 2)
            for first, second in zip(controls, controls[1:]):
                dt = second["time_s"] - first["time_s"]
                delta = abs(np.asarray(second["applied_target"]) - first["applied_target"])
                if dt <= 0 or np.any(delta > limits * dt + 1e-6):
                    violations.append({"kind": "robot_control_target_speed", "time_s": second["time_s"]})
            control_verified = bool(controls)
        result = {
            "status": "failed" if violations else "verified" if rows and control_verified else "unverified",
            "benchmark_eligible": bool(rows and control_verified and not violations),
            "human_transport_speed_limit_m_s": human_transport_speed_limit_m_s,
            "maximum_human_object_displacement_per_physics_step_m": maximum_human_displacement,
            "robot_control_target_rate_verified": control_verified and not any(
                row["kind"] == "robot_control_target_speed" for row in violations),
            "violation_count": len(violations), "violations": violations,
            "source_artifacts": ["contacts.jsonl", "robot_control.jsonl", "physics_contract.json"],
            "interpretation": "检查人体拿放过程中物体的逐步位移与控制目标速度，不证明全身运动、接触安全或真人效度。",
        }
    (directory / "motion_verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
