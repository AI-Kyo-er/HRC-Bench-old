"""自由刚体、夹爪摩擦接触与稳定放置观测；不绑定机器人和物体。

机器人与可选接触手提交关节目标：抓取、滑落、碰撞和落地由 Genesis 求解。
人体的显示骨架仍为 IK 驱动，完整人体动力学与安全效度单独披露。
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
        self.human_hand = None
        self.human_executor = None
        self.human_finger_links = set()
        self.human_contact_grasps = set()
        self._human_held = set()
        self.last_grasp_role = {}
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
        if self.human_hand is not None:
            assert self.avatar.robot.box.geoms, "人体碰撞盒缺少实际几何"
            assert all(geom._contype == 2 and geom._conaffinity == 8 for geom in self.avatar.robot.box.geoms), "人体碰撞盒过滤未生效"
            from .human_contact import HumanContactExecutor
            self.human_finger_links = {self.human_hand.get_link(name).idx for name in ("left_finger", "right_finger")}
            self.human_executor = HumanContactExecutor(self)

    def _build_partner_entities(self, assets):
        if self.human_manipulation_model != "articulated_contact_hand":
            return
        from .human_contact import contact_hand_asset
        gs = self.gs
        self.human_hand = self.add_entity("human_hand", "physical_contact_hand",
            gs.morphs.URDF(file=str(contact_hand_asset(assets)), fixed=True, merge_fixed_links=False),
            material=gs.materials.Rigid(friction=0.8), surface=gs.surfaces.Default(color=(0.71, 0.53, 0.38)))
        # Pinned Genesis URDF parser assigns contact bits to each collision geom.
        # Keep hand/object and hand/robot collisions, exclude the actor's own box.
        for geom in self.human_hand.geoms:
            if geom._contype or geom._conaffinity:
                geom._contype = 4
                geom._conaffinity = 1 | 8
        for geom in self.robot.geoms:
            if geom._contype or geom._conaffinity:
                geom._contype = 8
                geom._conaffinity = 1 | 2 | 4 | 8
        # A complete room around the unchanged shared worktable, without downloaded assets.
        self.add_entity("structure", "back_wall", gs.morphs.Box(size=(4.0, 0.08, 2.7), pos=(0.4, 1.8, 1.35), fixed=True),
                        surface=gs.surfaces.Default(color=(0.86, 0.85, 0.80)))
        for x in (-0.65, 0.05, 0.75):
            self.add_entity("structure", f"cabinet_{x}", gs.morphs.Box(size=(0.66, 0.45, 0.9), pos=(x, 1.52, 0.45), fixed=True),
                            surface=gs.surfaces.Default(color=(0.43, 0.57, 0.53)))
            self.add_entity("structure", f"counter_{x}", gs.morphs.Box(size=(0.69, 0.50, 0.04), pos=(x, 1.52, 0.92), fixed=True),
                            surface=gs.surfaces.Default(color=(0.80, 0.76, 0.64)))
            self.add_entity("structure", f"upper_cabinet_{x}", gs.morphs.Box(size=(0.63, 0.30, 0.65), pos=(x, 1.60, 1.86), fixed=True),
                            surface=gs.surfaces.Default(color=(0.77, 0.82, 0.77)))

    def add_entity(self, type, name, morph, **kwargs):
        if (getattr(self, "human_manipulation_model", None) == "articulated_contact_hand"
                and type == "avatar_box" and isinstance(morph, self.gs.morphs.Box)):
            morph.contype = 2
            morph.conaffinity = 8
        elif (getattr(self, "human_manipulation_model", None) == "articulated_contact_hand"
                and type == "object" and isinstance(morph, self.gs.morphs.Box)):
            morph.contype = 1
            morph.conaffinity = 1 | 4 | 8
        return super().add_entity(type, name, morph, **kwargs)

    def held_by_human(self):
        if getattr(self, "human_executor", None) is not None:
            assert all(item is None for item in self.avatar.robot.attached_object), "接触手后端不得绑定物体到 Avatar"
            assert self.attachment is None, "接触后端不得绑定物体到机器人"
            return tuple(sorted(self._human_held))
        return super().held_by_human()

    def continuous_apply_human_command(self, command):
        if self.human_executor is None:
            return super().continuous_apply_human_command(command)
        self.continuous_human_command = command
        self.log.add(self.step_count, "human_command", intent=command.intent, object_id=command.object_id,
                     destination=command.destination, speed_mps=float(command.speed_mps),
                     source="partner_policy_to_contact_executor")
        self.human_executor.accept(command)

    def _continuous_human_step(self):
        if getattr(self, "settling_only", False):
            return
        if self.human_executor is not None:
            self.human_executor.step()

    def begin_episode(self, *args, **kwargs):
        self.settling_only = False
        self.monitor_active = False
        self.previous_control = self.home.copy()
        if self.human_executor is not None:
            self.human_executor.reset()
        self._human_held = set()
        super().begin_episode(*args, **kwargs)

    def begin_benchmark(self):
        self.contact_records = []
        self.control_records = []
        self.contact_grasps = set()
        self.stable_placements = {}
        self.finger_touching = set()
        self.last_placement = {}
        self.human_contact_grasps = set()
        self.last_grasp_role = {}
        self._human_held = set()
        if self.human_executor is not None:
            self.human_executor.records = []
        self.initial_physical_positions = self.positions()
        self.monitor_active = True

    def continuous_start_action(self, action):
        if action.kind == "transfer":
            raise ValueError("真实接触后端只接受关节动作，不能用语义 transfer 代替模型操作。")
        super().continuous_start_action(action)

    def _continuous_joint_grasp(self):
        # Intentionally no attachment, proximity snap, weld or object pose write.
        pass

    def in_goal_surface(self, object_id, destination):
        from .goal_regions import surface_for
        surface = surface_for(destination)
        return bool(surface and surface.contains(tensor_array(self.objects[object_id].get_AABB())))

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
        physical_human_held = set()
        finger_touching = set()
        for name, entity in self.objects.items():
            contacts = {key: tensor_array(value) for key, value in entity.get_contacts().items()}
            forces = contacts["force_a"]
            loaded = np.linalg.norm(forces, axis=-1) > 0.01
            links = set(int(value) for value in np.r_[contacts["link_a"][loaded], contacts["link_b"][loaded]])
            touched_fingers = links & self.finger_links
            touched_human_fingers = links & getattr(self, "human_finger_links", set())
            if len(touched_human_fingers) == 2:
                physical_human_held.add(name)
            human_held = (len(touched_human_fingers) == 2 if getattr(self, "human_executor", None) is not None
                          else name in held_by_human)
            position = tensor_array(entity.get_pos())
            velocity = tensor_array(entity.get_vel())
            contact = {"position": position.tolist(), "velocity": velocity.tolist(),
                       "finger_links": sorted(touched_fingers),
                       "supported": bool(links & self.support_links),
                       "human_held": human_held,
                       "human_finger_links": sorted(touched_human_fingers),
                       "contact_count": len(contacts["link_a"]),
                       "contact_pairs": [{"link_a": int(a), "link_b": int(b), "force_a_n": force.tolist()}
                                         for a, b, force in zip(contacts["link_a"], contacts["link_b"], forces)],
                       "max_contact_force_n": float(np.linalg.norm(forces, axis=-1).max()) if len(forces) else 0.0}
            row["objects"][name] = contact
            if touched_fingers:
                finger_touching.add(name)
            # A grasp witness requires both actual fingers and a lift from the table.
            lifted = float(position[2] - self.initial_physical_positions[name][2]) > 0.025
            if not human_held and len(touched_fingers) == 2 and lifted:
                if name not in self.contact_grasps:
                    self.log.add(self.step_count + 1, "robot_contact_grasp", object_id=name,
                                 measured_position=position.tolist(), finger_links=sorted(touched_fingers))
                self.contact_grasps.add(name)
                self.last_placement.pop(name, None)
                if hasattr(self, "last_grasp_role"):
                    self.last_grasp_role[name] = "robot"
            if human_held and lifted:
                if name not in self.human_contact_grasps:
                    self.log.add(self.step_count + 1, "human_contact_grasp", object_id=name,
                                 measured_position=position.tolist(), finger_links=sorted(touched_human_fingers))
                self.human_contact_grasps.add(name)
                self.last_placement.pop(name, None)
                self.last_grasp_role[name] = "human"
            # Only a physically released, supported and stationary object can commit.
            grasped = name in self.contact_grasps or name in getattr(self, "human_contact_grasps", set())
            stable = (grasped and not human_held
                      and not touched_fingers and not touched_human_fingers and contact["supported"]
                      and float(np.linalg.norm(velocity)) < 0.04)
            if stable and getattr(self, 'visible_surface_goals', False):
                destinations = [item.destination for item in self.scenario.resolved_activity().work_items
                                if item.object_id == name]
                destination = next((key for key in destinations if self.in_goal_surface(name, key)), None)
            else:
                destination = next((key for key, point in self.regions.items()
                                    if np.linalg.norm(position - point) < 0.065), None) if stable else None
            prior_destination, dwell = self.stable_placements.get(name, (None, 0))
            dwell = dwell + 1 if destination is not None and destination == prior_destination else 1
            self.stable_placements[name] = (destination, dwell if destination else 0)
            if destination is not None and dwell >= self.placement_dwell_steps:
                if self.last_placement.get(name) == destination:
                    continue
                role = getattr(self, "last_grasp_role", {}).get(name, "robot")
                if _prerequisites_satisfied(self.scenario, role, name, destination, self.completed_skills):
                    skill = f"{role}:{name}:{destination}"
                    if skill not in self.completed_skills:
                        self.completed_skills.append(skill)
                    self.last_placement[name] = destination
                    self.log.add(self.step_count + 1, f"{role}_transfer_completed", object_id=name,
                                 destination=destination, source="friction_contact",
                                 stable_duration_s=dwell / 60, measured_position=position.tolist())
                else:
                    from .protocol import Message
                    self.last_placement[name] = destination
                    self.log.add(self.step_count + 1, f"{role}_transfer_blocked", object_id=name,
                                 destination=destination, reason="prerequisite_at_placement")
                    self.say(Message("environment", "action_blocked", "放置未提交：前置贡献尚未完成，需要满足前置后重新操作。",
                                     name, "prerequisite_at_placement", destination))
        self.finger_touching = finger_touching
        if getattr(self, "human_executor", None) is not None:
            self._human_held = physical_human_held
            rendered_hand = self.avatar.robot.get_hand_pos(1)
            actual_hand = tensor_array(self.human_hand.get_qpos())[:3]
            row["human_hand_alignment"] = {"rendered_wrist_xyz": rendered_hand.tolist(),
                                            "physical_palm_xyz": actual_hand.tolist(),
                                            "distance_m": float(np.linalg.norm(rendered_hand - actual_hand))}
        self.contact_records.append(row)

    def finish_episode(self, settle_steps=24):
        super().finish_episode(settle_steps)
        for filename, rows in (("contacts.jsonl", self.contact_records), ("robot_control.jsonl", self.control_records),
                               ("human_control.jsonl", self.human_executor.records if self.human_executor else [])):
            (self.output / filename).write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        (self.output / "physics_contract.json").write_text(json.dumps({
            "placement_geometry": 'visible_surface_footprint' if getattr(self, 'visible_surface_goals', False) else 'legacy_point_radius_65mm',
            "public_goal_surfaces": self.scenario.assets.get('public_goal_surfaces', {}),
            "robot_grasp_model": "friction_contact", "object_fixed": False, "object_collision": True,
            "object_shape_m": [0.05, 0.05, 0.10], "object_mass_kg": 0.10, "object_friction": 0.8,
            "robot_attachment": False, "robot_object_pose_writes_during_control": 0,
            "arm_target_speed_limit_rad_s": self.arm_speed_rad_s,
            "finger_target_speed_limit_m_s": self.finger_speed_m_s,
            "contact_grasp_objects": sorted(self.contact_grasps),
            "placement_dwell_s": self.placement_dwell_steps / 60,
            "human_manipulation_model": self.human_manipulation_model,
            "human_contact_grasp_objects": sorted(self.human_contact_grasps),
            "human_object_pose_writes_during_control": 0 if self.human_executor else None,
            "human_hand_model": "six_dof_yaw_pinch_contact_proxy" if self.human_executor else None,
            "human_hand_controller": self.human_executor.controller if self.human_executor else None,
            "human_linear_velocity_request_limit_m_s": 0.65 if self.human_executor else None,
            "human_yaw_velocity_request_limit_rad_s": 1.0 if self.human_executor else None,
            "interpretation": "机器人与可选接触手通过关节受力操作自由刚体；显示人体骨架是 IK，手代理不是完整人体动力学或真人接触安全证据。",
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        from .motion_continuity import verify_motion_continuity
        verify_motion_continuity(self.output)
