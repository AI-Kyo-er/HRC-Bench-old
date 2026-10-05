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
                       max_steps=150)
    result = run_continuous_episode(scenario, JointCalibrationPolicy(lambda: active["workspace"]),
                                    AdaptivePartner(scenario), output=args.output_dir / scenario.name,
                                    backend_factory=backend)
    (args.output_dir / "summary.json").write_text(json.dumps({"episodes": [result]}, ensure_ascii=False, indent=2))
    (args.output_dir / "provenance.json").write_text(json.dumps({
        **backend_provenance(args), "policy": args.policy, "seed": 0,
        "experiment": "joint_control_calibration",
        "purpose": "核查底层关节输出、实际闭合 / 接近抓放和双相机输入链路。",
        "interpretation": "公开几何 IK 教师检查，物体仍为运动学 attachment；不是 VLA 或真实接触证据。",
    }, ensure_ascii=False, indent=2))
    print(f"活动成功：{result['task_success']}")
    print(write_continuous_report(args.output_dir, [result]))


if __name__ == "__main__":
    main()
