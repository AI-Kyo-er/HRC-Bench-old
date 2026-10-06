#!/usr/bin/env python3
"""以公开几何 IK 教师核查底层关节抓放接口，不运行训练模型。"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from hrc_pilot.backend_options import add_backend_options, backend_provenance, configure_backend
from hrc_pilot.continuous import AdaptivePartner, run_continuous_episode
from hrc_pilot.continuous_report import write_continuous_report
from hrc_pilot.history_probe import make_history_probe
from hrc_pilot.protocol import Action
from hrc_pilot.video_verification import finalize_video_verification


class JointCalibrationPolicy:
    continuous_control = True

    def __init__(self, workspace):
        self.workspace = workspace

    def reset(self):
        self.phase = "approach"
        self.source = None

    def act(self, observation):
        if self.source is None:
            self.source = np.asarray(observation.objects["blue"])
        workspace = self.workspace()
        destination = np.asarray(observation.regions["tray_blue"])
        ee = np.asarray(observation.robot_ee)
        if workspace.robot_grasp_model == "friction_contact":
            return self._contact_action(workspace, observation, destination, ee)
        if self.phase == "approach" and np.linalg.norm(ee - self.source - [0, 0, 0.20]) < 0.035:
            self.phase = "descend"
        if self.phase == "descend" and np.linalg.norm(ee - self.source - [0, 0, 0.10]) < 0.035:
            self.phase = "close"
        if self.phase == "close" and workspace.attachment is not None:
            self.phase = "carry"
        if self.phase == "carry" and np.linalg.norm(ee - destination - [0, 0, 0.10]) < 0.025:
            self.phase = "open"
        target = (destination + [0, 0, 0.10] if self.phase in {"carry", "open"}
                  else self.source + [0, 0, 0.20 if self.phase == "approach" else 0.10])
        fingers = 0.0 if self.phase in {"close", "carry"} else 0.04
        joints = workspace._continuous_ik(target, fingers)
        return Action("joint_position", joints=tuple(float(value) for value in joints), duration_steps=1,
                      control_mode="joint_position_absolute")

    def _contact_action(self, workspace, observation, destination, ee):
        # Geometry teacher for dataset generation and backend calibration only.
        if self.phase == "approach" and np.linalg.norm(ee - self.source - [0, 0, 0.25]) < 0.02:
            self.phase = "descend"
        if self.phase == "descend" and np.linalg.norm(ee - self.source - [0, 0, 0.10]) < 0.012:
            self.phase = "close"
        contacts = workspace.contact_records[-1]["objects"]["blue"] if workspace.contact_records else {}
        if self.phase == "close" and len(contacts.get("finger_links", [])) == 2:
            self.phase = "lift"
        if self.phase == "lift" and np.linalg.norm(ee - self.source - [0, 0, 0.25]) < 0.02:
            self.phase = "carry"
        if self.phase == "carry" and np.linalg.norm(ee - destination - [0, 0, 0.25]) < 0.02:
            self.phase = "lower"
        if self.phase == "lower" and np.linalg.norm(ee - destination - [0, 0, 0.10]) < 0.012:
            self.phase = "open"
        if self.phase == "open" and sum(observation.robot_qpos[-2:]) > 0.073:
            self.phase = "retreat"
        if self.phase in {"approach", "lift"}:
            target = self.source + [0, 0, 0.25]
        elif self.phase in {"carry", "retreat"}:
            target = destination + [0, 0, 0.25]
        elif self.phase in {"lower", "open"}:
            target = destination + [0, 0, 0.10]
        else:
            target = self.source + [0, 0, 0.10]
        fingers = 0.0 if self.phase in {"close", "lift", "carry", "lower"} else 0.04
        joints = workspace._continuous_ik(target, fingers)
        return Action("joint_position", joints=tuple(float(value) for value in joints), duration_steps=1,
                      control_mode="geometry_teacher_contact_calibration")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_backend_options(parser)
    parser.set_defaults(backend="genesis", experiment_tier="important", resolution=480)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.policy = "public_geometry_ik_calibration"
    if args.backend != "genesis":
        parser.error("此检查要求 Genesis 后端")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("请使用新输出目录")
    factory = configure_backend(args, parser, args.output_dir)
    active = {}

    def backend(scenario):
        world = factory(scenario)
        active["workspace"] = world.workspace
        return world

    scenario = replace(make_history_probe(), name="joint_grasp_calibration", tick_hz=15.0,
                       description="公开几何 IK 教师通过 9 维关节位置输出完成蓝杯收纳；不调用语义 transfer。",
                       max_steps=450 if args.robot_grasp_model == "friction_contact" else 150)
    result = run_continuous_episode(scenario, JointCalibrationPolicy(lambda: active["workspace"]),
                                    AdaptivePartner(scenario), output=args.output_dir / scenario.name,
                                    backend_factory=backend)
    (args.output_dir / "summary.json").write_text(json.dumps({"episodes": [result]}, ensure_ascii=False, indent=2))
    provenance = {
        **backend_provenance(args), "policy": args.policy, "seed": 0,
        "experiment": "joint_control_calibration",
        "purpose": "核查底层关节输出、实际闭合 / 接近抓放和双相机输入链路。",
        "interpretation": ("公开几何 IK 教师检查自由刚体摩擦抓放；不是训练模型或 HRC 能力证据。人体仍为运动学执行。"
                           if args.robot_grasp_model == "friction_contact" else
                           "公开几何 IK 教师检查，物体仍为运动学 attachment；不是 VLA 或真实接触证据。"),
    }
    (args.output_dir / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2))
    finalize_video_verification(args.output_dir, required=bool(provenance["sim_video_required"]),
                                require_timeline=True)
    print(f"活动成功：{result['task_success']}")
    print(write_continuous_report(args.output_dir, [result]))


if __name__ == "__main__":
    main()
