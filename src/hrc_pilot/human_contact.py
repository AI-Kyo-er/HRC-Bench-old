"""人类意图的接触动作执行器：受力手指、限速伸手、实际持握与释放。

任务、物体和目的地完全来自伙伴策略命令。本模块不选择人类目标、不读取
评测标签；接近/闭合/抬升等只是可被策略改变的底层运动原语。
"""
from __future__ import annotations

from pathlib import Path
import math

import numpy as np


def contact_hand_asset(assets: Path) -> Path:
    """生成 XYZ、腕部 yaw 和双指六自由度接触手，无物体绑定。"""
    path = assets / "pilot/contact_hand.urdf"
    inertia = '<inertial><mass value="0.08"/><inertia ixx="0.0001" ixy="0" ixz="0" iyy="0.0001" iyz="0" izz="0.0001"/></inertial>'
    body = ['<?xml version="1.0"?><robot name="human_contact_hand">', '<link name="base"/>']
    parent = "base"
    for name, axis, lower, upper in (("slide_x", "1 0 0", -2, 2), ("slide_y", "0 1 0", -2, 2), ("slide_z", "0 0 1", 0.3, 2)):
        body.append(f'<link name="{name}">{inertia}</link>')
        body.append(f'<joint name="{name}_joint" type="prismatic"><parent link="{parent}"/><child link="{name}"/>'
                    f'<axis xyz="{axis}"/><limit lower="{lower}" upper="{upper}" effort="80" velocity="0.65"/></joint>')
        parent = name
    body.append(f'<link name="palm">{inertia}<visual><geometry><box size="0.10 0.065 0.022"/></geometry></visual>'
                '<collision><geometry><box size="0.10 0.065 0.022"/></geometry></collision></link>')
    body.append('<joint name="wrist_yaw_joint" type="revolute"><parent link="slide_z"/><child link="palm"/>'
                '<axis xyz="0 0 1"/><limit lower="-6.3" upper="6.3" effort="6" velocity="1.0"/></joint>')
    for name, sign in (("left_finger", -1), ("right_finger", 1)):
        geometry = '<geometry><box size="0.016 0.030 0.075"/></geometry>'
        body.append(f'<link name="{name}">{inertia}<visual>{geometry}</visual><collision>{geometry}</collision></link>')
        body.append(f'<joint name="{name}_joint" type="prismatic"><parent link="palm"/><child link="{name}"/>'
                    f'<origin xyz="{sign * 0.01} 0 -0.09"/><axis xyz="{sign} 0 0"/>'
                    '<limit lower="0" upper="0.045" effort="12" velocity="0.035"/></joint>')
    body.append('</robot>')
    text = "\n".join(body)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text() != text:
        path.write_text(text, encoding="utf-8")
    return path


def bounded_motion(position, velocity, target, *, dt, speed, acceleration):
    """带制动距离的连续积分，限制速度和加速度，不瞬间到达目标。"""
    delta = np.asarray(target, dtype=float) - position
    distance = float(np.linalg.norm(delta))
    desired = delta / max(distance, 1e-12) * min(speed, distance * acceleration / max(speed, 0.05))
    change = desired - velocity
    change *= min(1.0, acceleration * dt / max(float(np.linalg.norm(change)), 1e-12))
    velocity = velocity + change
    return position + velocity * dt, velocity


class HumanContactExecutor:
    palm_offset = np.array([0.0, 0.0, 0.09])
    home = np.array([0.65, 0.72, 1.03, 0.0, 0.035, 0.035])

    def __init__(self, workspace):
        self.workspace = workspace
        self.hand = workspace.human_hand
        self.hand.set_dofs_kp(np.array([2200, 2200, 2800, 60, 550, 550]))
        self.hand.set_dofs_kv(np.array([70, 70, 85, 1.0, 12, 12]))
        self.hand.set_dofs_force_range(np.array([-80, -80, -80, -1.5, -12, -12]), np.array([80, 80, 80, 1.5, 12, 12]))
        self.reset()

    def reset(self):
        self.phase = "idle"
        self.object_id = None
        self.destination = None
        self.source = None
        self.target = self.home[:3].copy()
        self.applied = self.home.copy()
        self.velocity = np.zeros(3)
        self.fingers = 0.035
        self.yaw = 0.0
        self.pending_command = None
        self.command = None
        self.body_velocity = np.zeros(2)
        self.body_target = np.array([0.50, 0.90])
        self.records = []
        self.phase_started = 0
        self.suspended_phase = None
        self.walk_cycle = 0.0
        self.body_state = {}
        self.hand.set_qpos(self.home)
        self.hand.control_dofs_position(self.home)

    def accept(self, command):
        if self.phase in {"release", "retreat"}:
            # Complete mechanical release/clearance before starting a new intent.
            # The newest generated command replaces the queued command.
            self.pending_command = command
            return
        self.command = command
        w = self.workspace
        if command.intent == "approach" and command.object_id in w.objects and not w.held_by_human():
            if self.phase in {"idle", "holding", "paused", "navigate", "navigate_holding"} or command.object_id != self.object_id:
                self.object_id = command.object_id
                self.destination = command.destination
                self.source = np.asarray(w.positions()[self.object_id])
                self.set_phase("approach")
            elif self.phase in {"approach", "descend", "close"}:
                actual_source = np.asarray(w.positions()[self.object_id])
                if np.linalg.norm(actual_source - self.source) > 0.015:
                    self.source = actual_source
                    self.fingers = 0.035
                    self.set_phase("approach")
        elif command.intent == "carry" and command.object_id in w.held_by_human():
            self.destination = command.destination
            if self.phase in {"holding", "paused", "navigate", "navigate_holding", "idle"}:
                self.set_phase("carry")
        elif command.intent in {"away", "yield", "return"} and command.target is not None:
            self.body_target = np.asarray(command.target[:2])
            if self.phase not in {"navigate", "navigate_holding"}:
                self.suspended_phase = self.phase
            self.set_phase("navigate_holding" if w.held_by_human() else "navigate")
        elif command.intent == "observe" and self.phase not in {"idle", "paused"}:
            self.suspended_phase = self.phase
            self.target = self.hand.get_qpos().detach().cpu().numpy()[:3].copy()
            self.body_target = w.avatar.robot.global_trans[:2].copy()
            self.set_phase("paused")

    def set_phase(self, phase):
        if phase == self.phase:
            return
        self.phase = phase
        if phase == "retreat":
            self.body_target = self.workspace.avatar.robot.global_trans[:2].copy()
        self.phase_started = self.workspace.step_count
        if self.workspace.monitor_active:
            self.workspace.log.add(self.workspace.step_count, "human_motor_phase", phase=phase,
                                   object_id=self.object_id, destination=self.destination)

    def _body_pose(self, hand_position):
        """沿工作台外边界移动并将显示手臂对齐实际接触手。"""
        w = self.workspace
        r = w.avatar.robot
        body = np.asarray(r.global_trans[:2], dtype=float).copy()
        if self.phase not in {"idle", "retreat", "paused", "navigate", "navigate_holding"}:
            # Reach from the nearer long edge; routes pass the right table edge.
            desired_y = 0.68 if self.target[1] >= 0 else -0.68
            destination = np.array([self.target[0], desired_y])
        else:
            destination = self.body_target
        if body[1] * destination[1] < 0 and body[0] < 1.11:
            waypoint = np.array([1.12, body[1]])
        elif abs(body[1] - destination[1]) > 0.05 and body[0] >= 1.1:
            waypoint = np.array([1.12, destination[1]])
        else:
            waypoint = destination
        position, self.body_velocity = bounded_motion(body, self.body_velocity, waypoint, dt=1/60,
                                                       speed=min(0.32, float(self.command.speed_mps)) if self.command else 0.30, acceleration=0.8)
        r.global_trans[:2] = position
        direction = self.body_velocity if np.linalg.norm(self.body_velocity) > 0.08 else hand_position[:2] - position
        if np.linalg.norm(direction) > 0.02:
            desired_yaw = math.atan2(direction[1], direction[0])
            yaw = math.atan2(r.global_rot[1, 0], r.global_rot[0, 0])
            difference = (desired_yaw - yaw + math.pi) % (2 * math.pi) - math.pi
            yaw += float(np.clip(difference, -0.85 / 60, 0.85 / 60))
            r.global_rot = np.array([[math.cos(yaw), -math.sin(yaw), 0], [math.sin(yaw), math.cos(yaw), 0], [0, 0, 1]])
        from scipy.spatial.transform import Rotation
        from vico.modules.avatar.utils import Mixamo_global_processing
        from genesis.utils import geom
        walk = w.avatar.motion_modules["walk"]
        if np.linalg.norm(self.body_velocity) > 0.025:
            stride_length = max(0.1, float(np.linalg.norm(walk.data[-1][:3] - walk.data[0][:3])))
            self.walk_cycle += np.linalg.norm(position - body) * (len(walk.data) - 1) / stride_length
            frame = int(self.walk_cycle) % (len(walk.data) - 1)
            r.pose = walk.data[frame].copy()
            r.pose[:3] = r.stop_pose[:3]
            r.global_mat = walk.global_mat.copy()
            r.global_mat_inv = walk.global_mat_inv.copy()
            r.node_trans = walk.node_data[frame].copy()
        else:
            r.pose = r.stop_pose.copy()
            r.global_mat = r.stop_mat.copy()
            r.global_mat_inv = r.stop_mat_inv.copy()
            r.node_trans = r.stop_node.copy()
        r.update()
        shoulder = r.skin.get_global_translation("RightShoulder")[0]
        rest_hand = r.get_hand_pos(1).copy()
        ik_root = r.skin.get_global_translation("Spine")[0]
        points = [r.skin.get_global_translation(name)[0] for name in ("Spine", "Spine1", "Spine2", "RightShoulder", "RightArm", "RightForeArm", "RightHand")]
        reach = sum(float(np.linalg.norm(b - a)) for a, b in zip(points, points[1:]))
        arm_reach = sum(float(np.linalg.norm(b - a)) for a, b in zip(points[-4:], points[-3:]))
        reachable = np.linalg.norm(self.target - ik_root) < reach * 0.98
        self.body_state = {"shoulder_position": shoulder.tolist(), "arm_reach_m": reach,
                           "ik_root_position": ik_root.tolist(), "ik_chain": "Spine_to_RightHand",
                           "work_target_distance_from_shoulder_m": float(np.linalg.norm(self.target - shoulder))}
        pose = r.pose
        translation = r.global_rot @ r.base_rot @ pose[:3] + r.global_trans
        rotation = geom.R_to_quat(geom.euler_to_R(
            Rotation.from_matrix(r.global_rot).as_euler('xyz', degrees=True)[[0, 2, 1]]) @ geom.quat_to_R(pose[3:7]))
        r.skin.calculate_real_pos(rotation=Mixamo_global_processing(pose[3:].reshape(-1, 4), r.global_mat, r.global_mat_inv, rotation),
                                  base_translation=translation[[1, 2, 0]])
        ik_root_name = "RightShoulder" if np.linalg.norm(hand_position - shoulder) < arm_reach * 0.99 else "Spine"
        r.node_trans = r.skin.ik_solve("RightHand", ik_root_name, hand_position.copy())
        return rest_hand, reachable

    def step(self):
        w = self.workspace
        actual = self.hand.get_qpos().detach().cpu().numpy()
        centre = actual[:3]
        state = (w.contact_records[-1]["objects"].get(self.object_id, {})
                 if w.contact_records and self.object_id else {})
        contact = len(state.get("human_finger_links", [])) == 2
        holding = self.object_id in w.held_by_human()
        destination = np.asarray(w.regions[self.destination]) if self.destination in w.regions else None
        at = lambda target: np.linalg.norm(centre - target) < 0.012
        phase = self.phase
        if phase in {"approach", "descend"} and not holding:
            self.source = np.asarray(w.positions()[self.object_id])
            from .robot_control import hand_rotation
            orientation = hand_rotation(w.objects[self.object_id].get_quat().detach().cpu().numpy())
            jaw_axis = max((orientation[:, 0], orientation[:, 1]), key=lambda axis: np.linalg.norm(axis[:2]))
            raw_yaw = math.atan2(jaw_axis[1], jaw_axis[0])
            self.yaw = actual[3] + (raw_yaw - actual[3] + math.pi / 2) % math.pi - math.pi / 2
            # Pads must clear the tabletop even after the object has tipped.
            self.source[2] = max(self.source[2], 0.8005)
        if phase == "approach":
            self.target = self.source + self.palm_offset + [0, 0, 0.16]
            self.fingers = 0.035
            if at(self.target):
                self.set_phase("descend")
        elif phase == "descend":
            self.target = self.source + self.palm_offset
            if at(self.target):
                self.set_phase("close")
        elif phase == "close":
            self.fingers = 0.0
            if contact:
                self.set_phase("lift")
        elif phase == "lift":
            self.target = self.source + self.palm_offset + [0, 0, 0.16]
            if at(self.target):
                self.set_phase("holding" if holding else "idle")
        elif phase == "holding":
            if self.command and self.command.intent == "carry" and holding and destination is not None:
                self.set_phase("carry")
        elif phase == "carry" and destination is not None:
            self.target = destination + self.palm_offset + [0, 0, 0.16]
            if at(self.target):
                self.set_phase("lower")
        elif phase == "lower" and destination is not None:
            self.target = destination + self.palm_offset
            if at(self.target):
                self.set_phase("release")
        elif phase == "release":
            self.fingers = 0.035
            if not holding and actual[-2:].min() > 0.032:
                self.set_phase("retreat")
        elif phase == "retreat" and destination is not None:
            self.target = destination + self.palm_offset + [0, 0, 0.20]
            if at(self.target):
                self.set_phase("idle")
                self.object_id = None
                if self.pending_command is not None:
                    pending = self.pending_command
                    self.pending_command = None
                    self.accept(pending)
        speed = min(0.55, float(self.command.speed_mps)) if self.command else 0.3
        rest_hand, reachable = self._body_pose(centre)
        if self.phase in {"idle", "navigate", "navigate_holding"}:
            drive_target = rest_hand.copy()
            drive_target[2] = max(1.00, drive_target[2])
            speed = 0.65 if not holding else speed
        elif self.phase == "paused":
            drive_target = self.target
        elif reachable:
            drive_target = self.target
        elif holding:
            drive_target = np.array([np.clip(w.avatar.robot.global_trans[0], -0.28, 0.78),
                                     np.clip(w.avatar.robot.global_trans[1], -0.30, 0.30), max(1.05, self.target[2])])
        else:
            drive_target = rest_hand.copy()
            drive_target[2] = max(1.00, drive_target[2])
        self.applied[:3], self.velocity = bounded_motion(self.applied[:3], self.velocity, drive_target,
                                                        dt=1/60, speed=speed, acceleration=1.4 if self.phase in {"idle", "navigate"} else 0.9)
        self.applied[-2:] += np.clip(self.fingers - self.applied[-2:], -0.035/60, 0.035/60)
        self.applied[3] += float(np.clip(self.yaw - self.applied[3], -1/60, 1/60))
        self.hand.control_dofs_position(self.applied)
        if w.monitor_active:
            self.records.append({"time_s": w.step_count / 60, "phase": self.phase,
                                 "object_id": self.object_id, "destination": self.destination,
                                 "requested_palm_xyz": self.target.tolist(), "applied_joint_target": self.applied.tolist(),
                                 "actual_qpos": actual.tolist(), "human_position": w.avatar.get_global_pose()[:3].tolist(),
                                 "reachable_work_target": bool(reachable),
                                 "body_state": self.body_state,
                                 "human_object_pose_writes": 0})
