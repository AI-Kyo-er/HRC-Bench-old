#!/usr/bin/env python3
"""校准物理接触手与显示骨架；几何教师仅用于 Data generation / 工程检查。"""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from hrc_pilot.backend_options import add_backend_options, backend_provenance, configure_backend
from hrc_pilot.continuous import HumanCommand, PartnerOutput, run_continuous_episode
from hrc_pilot.continuous_report import write_continuous_report
from hrc_pilot.history_probe import make_history_probe
from hrc_pilot.protocol import Action
from hrc_pilot.video_verification import finalize_video_verification


class ParkedRobot:
    continuous_control = True

    def reset(self):
        self.home = None

    def act(self, observation):
        if self.home is None:
            self.home = observation.robot_qpos
        return Action("joint_position", joints=self.home, duration_steps=1)


class ContactHandTeacher:
    def __init__(self, scenario):
        self.scenario = scenario

    def reset(self, seed):
        pass

    def initial_messages(self):
        return self.scenario.initial_messages()

    def step(self, observation):
        return PartnerOutput(HumanCommand("carry" if "blue" in observation.held_by_human else "approach",
                                         "blue", "tray_blue", speed_mps=0.38, acceleration_mps2=0.9))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_backend_options(parser)
    parser.set_defaults(backend="genesis", experiment_tier="important", robot_grasp_model="friction_contact",
                        human_manipulation_model="articulated_contact_hand", resolution=640, render_stride=4)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    args.policy = "parked_robot_joint_hold"
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("请使用新的输出目录")
    factory = configure_backend(args, parser, args.output_dir)
    scenario = replace(make_history_probe(), name="human_contact_calibration", max_steps=600, tick_hz=15.0,
                       human_targets={"blue": "tray_blue"}, robot_targets={}, activity=None,
                       description="校准人体物理接触手：连续接近蓝块，受力夹持，搬运并稳定释放；机器人保持原位。")
    result = run_continuous_episode(scenario, ParkedRobot(), ContactHandTeacher(scenario), seed=args.seed,
                                    output=args.output_dir / scenario.name, backend_factory=factory,
                                    partner_mode="contact_hand_calibration_teacher")
    provenance = {**backend_provenance(args), "policy": args.policy, "seed": args.seed,
                  "experiment": "human_contact_hand_calibration", "trained_model": False,
                  "purpose": "校准关节接触手真实摩擦持握、连续搬运、释放及显示骨架对齐。",
                  "controlled": "人类动作命令由几何教师产生，机器人仅保持关节；不测试模型策略性能。",
                  "interpretation": "物理手代理与 Avatar IK 校准，不是完整人体动力学、真人效度或 HRC 能力结果。"}
    (args.output_dir / "summary.json").write_text(json.dumps({"episodes": [result]}, ensure_ascii=False, indent=2))
    (args.output_dir / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2))
    finalize_video_verification(args.output_dir, required=True)
    print(f"接触手校准活动成功：{result['task_success']}", flush=True)
    print(write_continuous_report(args.output_dir, [result]))


if __name__ == "__main__":
    main()
