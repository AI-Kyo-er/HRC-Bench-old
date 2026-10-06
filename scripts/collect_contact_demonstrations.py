#!/usr/bin/env python3
"""用几何教师采集实际接触示范，供原生模型校准与训练；不是模型评测成绩。"""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from hrc_pilot.backend_options import add_backend_options, backend_provenance, configure_backend
from hrc_pilot.continuous import HumanCommand, PartnerOutput, run_continuous_episode
from hrc_pilot.continuous_report import write_continuous_report
from hrc_pilot.history_probe import make_history_probe
from hrc_pilot.video_verification import finalize_video_verification
from scripts.run_joint_calibration import JointCalibrationPolicy
from experiments.continuous_v2.physical_frame_dataset import (PhysicalFrameDataset, export_physical_frames,
                                                            export_applied_position_frames)


class ObservingPartner:
    def __init__(self, scenario):
        self.scenario = scenario

    def reset(self, seed):
        pass

    def initial_messages(self):
        return self.scenario.initial_messages()

    def step(self, observation):
        return PartnerOutput(HumanCommand("observe"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_backend_options(parser)
    parser.set_defaults(backend="genesis", experiment_tier="important", robot_grasp_model="friction_contact",
                        human_manipulation_model="articulated_contact_hand", resolution=480, render_stride=4)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--objects", nargs="+", choices=("red", "blue", "green"), default=["red", "blue", "green"])
    parser.add_argument("--visible-surfaces", action="store_true", help="使用可见表面足迹目标与独立变化的物体布局")
    args = parser.parse_args()
    args.policy = "public_geometry_contact_demonstrator"
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("请使用新的输出目录")
    if args.backend != "genesis" or args.robot_grasp_model != "friction_contact":
        parser.error("实际接触示范要求 Genesis 摩擦接触后端")
    factory = configure_backend(args, parser, args.output_dir)
    active = {}

    def backend(scenario):
        world = factory(scenario)
        active["workspace"] = world.workspace
        return world

    results, exports = [], []
    for color in args.objects:
        for seed in args.seeds:
            split = "dev" if seed == max(args.seeds) else "train"
            name = f"contact_{color}_seed_{seed:04d}"
            instruction = f"Pick up the {color} block and place it on the blue mat."
            scenario = replace(make_history_probe(), name=name, tick_hz=15.0, max_steps=450,
                               human_targets={}, robot_targets={color: f"tray_{color}"}, activity=None,
                               description=instruction)
            if args.visible_surfaces:
                from hrc_pilot.goal_regions import visible_goal_scenario
                scenario = visible_goal_scenario(scenario, seed=seed)
            directory = args.output_dir / split / name
            policy = JointCalibrationPolicy(lambda: active["workspace"], color, f"tray_{color}")
            result = run_continuous_episode(scenario, policy, ObservingPartner(scenario), seed=seed,
                                            output=directory, backend_factory=backend,
                                            partner_mode="observing_data_collection_partner")
            results.append(result)
            motion = json.loads((directory / "motion_verification.json").read_text())
            count = export_physical_frames(directory, instruction) if result["task_success"] and motion["status"] == "verified" else 0
            position_count = export_applied_position_frames(directory) if count else 0
            exports.append({"episode": f"{split}/{name}", "exported_frames": count, "position_frames": position_count,
                            "task_success": result["task_success"]})
            print(f"[demonstrations] {split}/{name}: 物理操作 {result['task_success']}，示范帧 {count}", flush=True)
    provenance = {**backend_provenance(args), "policy": args.policy, "seeds": args.seeds,
                  "visible_surfaces": args.visible_surfaces,
                  "experiment": "physical_contact_demonstration_dataset", "trained_model": False,
                  "purpose": "采集真实接触操作及双相机、关节状态、动作块监督，为训练模型建立基础操作校准数据。",
                  "controlled": "几何教师仅产生关节目标；人体观察，操作物体不使用 attachment 或坐标搬运。",
                  "interpretation": "Data generation pipeline 的教师示范，不是先进模型或 HRC 性能。"}
    (args.output_dir / "summary.json").write_text(json.dumps({"episodes": results}, ensure_ascii=False, indent=2))
    (args.output_dir / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2))
    finalize_video_verification(args.output_dir, required=True)
    verification = {}
    for split in ("train", "dev"):
        dataset = PhysicalFrameDataset(args.output_dir, split=split)
        for index in range(len(dataset)):
            sample = dataset[index]
            assert sample["actions"].shape == (15, 8) and sample["action_valid"][0]
        verification[split] = len(dataset)
    (args.output_dir / "dataset.json").write_text(json.dumps({
        "format": "physical_frame_stem_pairs_v1", "action_horizon": 15, "control_hz": 15,
        "pairing_rule": "input stem → _wrist.png / .state.npy / .action.npy",
        "split_rule": "最大 seed 为 dev，其余为 train；本轮没有测试留出泛化。",
        "source": "actual_next_physics_joint_state", "exports": exports,
        "verified_samples": verification, "interpretation": "只验证真实数据与加载器，不声明已训练任何模型。",
    }, ensure_ascii=False, indent=2))
    print(write_continuous_report(args.output_dir, results))


if __name__ == "__main__":
    main()
