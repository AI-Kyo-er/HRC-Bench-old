"""自由刚体、夹爪摩擦接触与稳定放置观测；不绑定机器人和物体。

Avatar 的人体动作和拿放仍沿用 VC 的运动学执行器，单独披露。机器人只能
提交关节目标：抓取、滑落、碰撞和落地由 Genesis 求解，监测器只记录结果。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .backend import VCWorkspace
from .continuous import _prerequisites_satisfied


def tensor_array(value):
    if hasattr(value, "detach"):
        return value.detach().cpu().numpy()
    return np.asarray(value)


class ContactWorkspace(VCWorkspace):
    # Conservative limits for controlled motion; all requested/applied targets are retained.
    arm_speed_rad_s = 1.2
    finger_speed_m_s = 0.04
    placement_dwell_steps = 24

    def __init__(self, **kwargs):
        self.contact_records = []
        self.control_records = []
        self.contact_grasps = set()
        self.stable_placements = {}
        self.finger_touching = set()
        self.last_placement = {}
        self.monitor_active = False
        kwargs["robot_grasp_model"] = "friction_contact"
        super().__init__(**kwargs)
        self.finger_links = {self.robot.get_link(name).idx for name in ("left_finger", "right_finger")}
        self.support_links = {entity.links[0].idx for entity in self.scene.entities
                              if self.entity_info[entity.idx]["name"] in {"table", "floor"}}
        self.previous_control = self.home.copy()
        # Finger position control produces bounded squeezing force, not an object constraint.
        self.robot.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 800, 800]))
        self.robot.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 20, 20]))
        self.robot.set_dofs_force_range(np.array([-87, -87, -87, -87, -12, -12, -12, -20, -20]),
                                        np.array([87, 87, 87, 87, 12, 12, 12, 20, 20]))

    def begin_episode(self, *args, **kwargs):
        self.monitor_active = False
        self.previous_control = self.home.copy()
        super().begin_episode(*args, **kwargs)

    def begin_benchmark(self):
        self.contact_records = []
        self.control_records = []
        self.contact_grasps = set()
        self.stable_placements = {}
        self.finger_touching = set()
        self.last_placement = {}
        self.initial_physical_positions = self.positions()
        self.monitor_active = True

    def continuous_start_action(self, action):
        if action.kind == "transfer":
            raise ValueError("真实接触后端只接受关节动作，不能用语义 transfer 代替模型操作。")
        super().continuous_start_action(action)

    def _continuous_joint_grasp(self):
        # Intentionally no attachment, proximity snap, weld or object pose write.
        pass

    def _control_robot_position(self, target):
        target = np.asarray(target, dtype=float)
        limits = np.array([self.arm_speed_rad_s] * 7 + [self.finger_speed_m_s] * 2) / 60
        applied = self.previous_control + np.clip(target - self.previous_control, -limits, limits)
        self.robot.control_dofs_position(applied)
        self.previous_control = applied
        if self.monitor_active:
            self.control_records.append({"physics_step": self.step_count, "time_s": self.step_count / 60,
                                         "requested_target": target.tolist(), "applied_target": applied.tolist(),
                                         "rate_limited": bool(np.any(abs(applied - target) > 1e-6))})

    def _after_physics_step(self):
        if not self.monitor_active:
            return
        row = {"physics_step": self.step_count + 1, "time_s": (self.step_count + 1) / 60,
               "objects": {}, "robot_object_pose_writes": 0}
        held_by_human = set(self.held_by_human())
        finger_touching = set()
        for name, entity in self.objects.items():
            contacts = {key: tensor_array(value) for key, value in entity.get_contacts().items()}
            forces = contacts["force_a"]
            loaded = np.linalg.norm(forces, axis=-1) > 0.01
            links = set(int(value) for value in np.r_[contacts["link_a"][loaded], contacts["link_b"][loaded]])
            touched_fingers = links & self.finger_links
            position = tensor_array(entity.get_pos())
            velocity = tensor_array(entity.get_vel())
            contact = {"position": position.tolist(), "velocity": velocity.tolist(),
                       "finger_links": sorted(touched_fingers),
                       "supported": bool(links & self.support_links),
                       "human_held": name in held_by_human,
                       "contact_count": len(contacts["link_a"]),
                       "contact_pairs": [{"link_a": int(a), "link_b": int(b), "force_a_n": force.tolist()}
                                         for a, b, force in zip(contacts["link_a"], contacts["link_b"], forces)],
                       "max_contact_force_n": float(np.linalg.norm(forces, axis=-1).max()) if len(forces) else 0.0}
            row["objects"][name] = contact
            if touched_fingers:
                finger_touching.add(name)
            # A grasp witness requires both actual fingers and a lift from the table.
            lifted = float(position[2] - self.initial_physical_positions[name][2]) > 0.025
            if name not in held_by_human and len(touched_fingers) == 2 and lifted:
                if name not in self.contact_grasps:
                    self.log.add(self.step_count + 1, "robot_contact_grasp", object_id=name,
                                 measured_position=position.tolist(), finger_links=sorted(touched_fingers))
                self.contact_grasps.add(name)
            # Only a physically released, supported and stationary object can commit.
            stable = (name in self.contact_grasps and name not in held_by_human
                      and not touched_fingers and contact["supported"]
                      and float(np.linalg.norm(velocity)) < 0.04)
            destination = next((key for key, point in self.regions.items()
                                if np.linalg.norm(position - point) < 0.065), None) if stable else None
            prior_destination, dwell = self.stable_placements.get(name, (None, 0))
            dwell = dwell + 1 if destination is not None and destination == prior_destination else 1
            self.stable_placements[name] = (destination, dwell if destination else 0)
            if destination is not None and dwell >= self.placement_dwell_steps:
                if self.last_placement.get(name) == destination:
                    continue
                if _prerequisites_satisfied(self.scenario, "robot", name, destination, self.completed_skills):
                    skill = f"robot:{name}:{destination}"
                    if skill not in self.completed_skills:
                        self.completed_skills.append(skill)
                    self.last_placement[name] = destination
                    self.log.add(self.step_count + 1, "robot_transfer_completed", object_id=name,
                                 destination=destination, source="friction_contact",
                                 stable_duration_s=dwell / 60, measured_position=position.tolist())
        self.finger_touching = finger_touching
        self.contact_records.append(row)

    def finish_episode(self, settle_steps=24):
        super().finish_episode(settle_steps)
        for filename, rows in (("contacts.jsonl", self.contact_records), ("robot_control.jsonl", self.control_records)):
            (self.output / filename).write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        (self.output / "physics_contract.json").write_text(json.dumps({
            "robot_grasp_model": "friction_contact", "object_fixed": False, "object_collision": True,
            "object_shape_m": [0.05, 0.05, 0.10], "object_mass_kg": 0.10, "object_friction": 0.8,
            "robot_attachment": False, "robot_object_pose_writes_during_control": 0,
            "arm_target_speed_limit_rad_s": self.arm_speed_rad_s,
            "finger_target_speed_limit_m_s": self.finger_speed_m_s,
            "contact_grasp_objects": sorted(self.contact_grasps),
            "placement_dwell_s": self.placement_dwell_steps / 60,
            "human_manipulation_model": "avatar_kinematic_attachment",
            "interpretation": "机器人自由刚体摩擦抓放；人体动作和拿放仍为运动学抽象，尚未验证人体接触安全。",
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        from .motion_continuity import verify_motion_continuity
        verify_motion_continuity(self.output)
