"""Minimal shared workspace using VC AvatarController and VC's pinned Genesis.

Grasp/placement is a kinematic skill abstraction, matching VC's attachment model.
Arm motion uses joint controllers; no force/grasp-quality claim is made.
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .protocol import Action, EventLog, Message, Observation


class VCWorkspace:
    def __init__(self, *, assets: Path, backend: str = "gpu", resolution: int = 800,
                 render_stride: int = 3, viewer: bool = False, scenario=None,
                 minimum_transfer_phase_steps: int = 12,
                 robot_grasp_model: str = "kinematic_attachment",
                 human_manipulation_model: str = "avatar_kinematic_attachment"):
        import genesis as gs
        from vico.modules.avatar.avatar_controller import AvatarController
        from .assets import mug_mesh

        self.gs = gs
        self.robot_grasp_model = robot_grasp_model
        self.human_manipulation_model = human_manipulation_model
        gs.init(seed=0, backend=gs.gpu if backend == "gpu" else gs.cpu,
                logging_level=logging.WARNING, theme="dumb")
        self.scene = gs.Scene(
            sim_options=gs.options.SimOptions(dt=1 / 60, substeps=4),
            rigid_options=gs.options.RigidOptions(enable_collision=True,
                max_collision_pairs=1024 if human_manipulation_model == "articulated_contact_hand" else 512),
            avatar_options=gs.options.AvatarOptions(enable_collision=False),
            vis_options=gs.options.VisOptions(background_color=(0.88, 0.92, 0.96),
                ambient_light=(0.5, 0.5, 0.5), shadow=True, segmentation_level="entity"),
            show_viewer=viewer,
        )
        self.entity_info = {}
        self.add_entity("structure", "floor", gs.morphs.Plane(),
                        surface=gs.surfaces.Default(color=(0.81, 0.84, 0.86)))
        self.add_entity("structure", "table", gs.morphs.Box(size=(1.35, 1.05, 0.07),
                        pos=(0.25, 0, 0.725), fixed=True),
                        surface=gs.surfaces.Default(color=(0.58, 0.43, 0.30)))
        for x in (-0.30, 0.80):
            for y in (-0.40, 0.40):
                self.add_entity("structure", "leg", gs.morphs.Box(size=(0.06, 0.06, 0.69),
                                pos=(x, y, 0.345), fixed=True),
                                surface=gs.surfaces.Default(color=(0.28, 0.31, 0.35)))
        self.scenario = scenario
        self.regions = (dict(scenario.regions) if scenario is not None else
                        {"tray_red": (0.55, -0.28, 0.82), "tray_blue": (0.37, -0.32, 0.82),
                         "keep_red": (0.53, 0.24, 0.82)})
        self.add_entity("region", "tray", gs.morphs.Box(size=(0.43, 0.24, 0.012),
                        pos=(0.46, -0.30, 0.765), fixed=True, collision=False),
                        surface=gs.surfaces.Default(color=(0.25, 0.43, 0.72)))
        self.add_entity("region", "personal_area", gs.morphs.Box(size=(0.25, 0.22, 0.012),
                        pos=(0.53, 0.24, 0.765), fixed=True, collision=False),
                        surface=gs.surfaces.Default(color=(0.37, 0.68, 0.48)))
        self.objects = {}
        mug_file = str(mug_mesh(assets))
        default_objects = [("red", (0.42, 0.12, 0.82), (0.86, 0.18, 0.19)),
                           ("blue", (0.35, -0.08, 0.82), (0.16, 0.48, 0.84))]
        object_specs = ([(spec.name, spec.position,
                          tuple(float(x) for x in ((0.86, 0.18, 0.19) if i % 3 == 0
                                                   else (0.16, 0.48, 0.84) if i % 3 == 1
                                                   else (0.22, 0.65, 0.35))))
                        for i, spec in enumerate(scenario.objects)]
                       if scenario is not None else default_objects)
        for name, pos, color in object_specs:
            if robot_grasp_model == "friction_contact":
                # A convex container proxy is a free rigid body, never bound to the robot.
                morph = gs.morphs.Box(size=(0.05, 0.05, 0.10), pos=pos, fixed=False, collision=True)
                material = gs.materials.Rigid(rho=400, friction=0.8)
            else:
                morph = gs.morphs.Mesh(file=mug_file, pos=pos, fixed=True, collision=False,
                                       decimate=False, convexify=False)
                material = None
            self.objects[name] = self.add_entity("object", name,
                morph, material=material,
                surface=gs.surfaces.Default(color=color))
        self.robot = self.add_entity("robot", "franka",
            gs.morphs.MJCF(file="xml/franka_emika_panda/panda.xml", pos=(-0.10, 0, 0.76)))
        self.avatar = AvatarController(
            env=self, name="pilot_partner", motion_data_path="avatars/motions/motion.pkl",
            skin_options={"glb_path": str(assets / "avatars/models/mixamo_Alex_Jefferson.glb"),
                          "euler": (-90, 0, 90), "pos": (0, 0, -0.959008030)},
            frame_ratio=0.30, enable_collision=False,
        )
        self._build_partner_entities(assets)
        self.camera = self.scene.add_camera(res=(resolution, resolution * 3 // 4),
            pos=(2.05, -2.35, 2.30), lookat=(0.35, 0.20, 0.94), fov=48, GUI=False)
        self.robot_camera = self.scene.add_camera(res=(320, 240),
            pos=(-0.48, -0.42, 1.50), lookat=(0.48, 0.12, 0.88), fov=65, GUI=False)
        self.wrist_camera = self.scene.add_camera(res=(320, 240),
            pos=(0.3, 0, 1.3), lookat=(0.3, 0, 0.8), fov=75, GUI=False)
        self.scene.build()
        self.ee = self.robot.get_link("hand")
        self.robot.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
        self.robot.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))
        self.robot.set_dofs_force_range(np.array([-87, -87, -87, -87, -12, -12, -12, -100, -100]),
                                        np.array([87, 87, 87, 87, 12, 12, 12, 100, 100]))
        self.home = np.array([0, -0.5, 0, -2.1, 0, 1.6, 0.8, 0.04, 0.04])
        self.stride = render_stride
        self.font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 19)
        self.small_font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 16)
        self.writer = None
        self.step_count = 0
        self.log = EventLog()
        self.messages = []
        self.completed_skills = []
        self.current_robot_action = "初始化"
        self.attachment = None
        self.trace = []
        self.output = None
        self.continuous_execution = None
        self.continuous_human_command = None
        self.continuous_human_phase = None
        self.active_scenario = self.scenario
        self.last_observation_path = None
        self.observation_index = 0
        self.last_wrist_observation_path = None
        self.continuous_delay_frames = 0
        self.continuous_pending_placement = None
        self.continuous_rng = np.random.default_rng(0)
        self.remaining_failure_budget = 0
        self.video_frames = []
        self.video_phase = "warmup"
        self.minimum_transfer_phase_steps = max(0, int(minimum_transfer_phase_steps))

    def add_entity(self, type, name, morph, material=None, surface=None, **kwargs):
        entity = self.scene.add_entity(morph=morph, material=material, surface=surface, **kwargs)
        self.entity_info[entity.idx] = {"type": type, "name": name}
        return entity

    def _build_partner_entities(self, assets):
        pass

    def _continuous_human_step(self):
        pass

    def positions(self):
        return {k: v.get_pos().detach().cpu().numpy().astype(float).tolist() for k, v in self.objects.items()}

    def begin_episode(self, output: Path, scenario: str, policy: str, seed: int):
        self.gs.utils.set_random_seed(seed)
        self.scene.reset()
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        self.log, self.messages, self.completed_skills, self.trace = EventLog(), [], [], []
        self.step_count = 0
        self.attachment = None
        self.continuous_execution = None
        self.continuous_human_command = None
        self.continuous_human_phase = None
        self.last_observation_path = None
        self.observation_index = 0
        self.last_wrist_observation_path = None
        self.continuous_delay_frames = 0
        self.continuous_pending_placement = None
        self.continuous_rng = np.random.default_rng(seed)
        self.remaining_failure_budget = int(max(
            0, getattr(getattr(self.scenario, "dynamics", None), "robot_failure_budget", 0)))
        self.video_frames = []
        self.video_phase = "warmup"
        self.current_robot_action = "观察共同工作空间"
        self.title = f"{scenario} · {policy} · seed {seed}"
        self.video_fps = 60 / self.stride
        self.writer = imageio.get_writer(str(output / "demo.mp4"), fps=self.video_fps,
                                        codec="libx264", quality=7, macro_block_size=2)
        jitter = np.random.default_rng(seed).uniform(-0.015, 0.015, 2)
        if self.scenario is not None:
            self.initial_positions = {
                spec.name: (spec.position[0] + jitter[0], spec.position[1] + jitter[1], spec.position[2])
                for spec in self.scenario.objects
            }
        else:
            self.initial_positions = {"red": (0.42 + jitter[0], 0.12 + jitter[1], 0.82),
                                      "blue": (0.35 + jitter[0], -0.08 + jitter[1], 0.82)}
        for name, pos in self.initial_positions.items():
            self.objects[name].set_pos(np.array(pos))
            self.objects[name].set_quat(np.array([1., 0., 0., 0.]))
        self.robot.set_qpos(self.home)
        self.robot.control_dofs_position(self.home)
        self.avatar.reset(np.array([0.50, 0.90, 0.0]), self.gs.utils.geom.euler_to_R([0, 0, -90]))
        self.tick(20)
        self.capture(force=True)
        self.log.add(self.step_count, "initial_state", positions=self.positions(),
                     human_position=self.avatar.get_global_pose()[:3].tolist())

    def say(self, message: Message):
        self.messages.append(message)
        self.log.add(self.step_count, "public_message", speaker=message.speaker,
                     message_kind=message.kind, text=message.text,
                     object_id=message.object_id, value=message.value)

    def held_by_human(self):
        return tuple(name for name, obj in self.objects.items()
                     if any(held is obj for held in self.avatar.robot.attached_object))

    def observe(self) -> Observation:
        image_path = self.output / f"observation_{self.step_count:06d}_{self.observation_index:06d}.png"
        self.observation_index += 1
        rgb = self.robot_camera.render(rgb=True)[0]
        Image.fromarray(np.asarray(rgb, dtype=np.uint8)).save(image_path)
        self.last_observation_path = image_path.name
        from .robot_control import hand_rotation
        rotation = hand_rotation(self.ee.get_quat().cpu().numpy())
        hand = self.ee.get_pos().cpu().numpy()
        self.wrist_camera.set_pose(pos=hand + rotation @ np.array([0.035, 0, 0.025]),
                                   lookat=hand + rotation @ np.array([0, 0, 0.40]),
                                   up=rotation @ np.array([0, -1, 0]))
        wrist_rgb = np.asarray(self.wrist_camera.render(rgb=True)[0], dtype=np.uint8).copy()
        wrist_path = image_path.with_name(image_path.stem + "_wrist.png")
        Image.fromarray(wrist_rgb).save(wrist_path)
        self.last_wrist_observation_path = wrist_path.name
        execution = self.continuous_execution
        active_action = "idle" if execution is None else execution["action"].kind
        if execution is not None and active_action == "transfer":
            active_action = f"transfer:{execution['action'].object_id}"
        phase = "idle" if execution is None else execution.get("phase", "execute")
        return Observation(
            objects={k: tuple(v) for k, v in self.positions().items()}, regions=dict(self.regions),
            messages=tuple(self.messages), robot_ee=tuple(self.ee.get_pos().cpu().numpy().tolist()),
            human_position=tuple(self.avatar.get_global_pose()[:3].tolist()),
            held_by_human=self.held_by_human(), completed_skills=tuple(self.completed_skills),
            robot_qpos=tuple(self.robot.get_qpos().cpu().numpy().tolist()),
            rgb=np.asarray(rgb, dtype=np.uint8).copy(),
            wrist_rgb=wrist_rgb,
            time_s=float(self.step_count) / 60.0,
            active_robot_action=active_action,
            action_phase=phase,
            visible_human_action=(getattr(self.continuous_human_command, "intent", "observe")
                                  if self.continuous_human_command is not None else "observe"),
            task_family=getattr(self.scenario, "task_family", "object_transport"),
            task_description=getattr(self.scenario, "description", ""),
            scene_id=getattr(self.scenario, "name", ""),
            human_hand_position=(tuple(self.human_hand.get_qpos().cpu().numpy()[:3].tolist())
                                 if getattr(self, "human_hand", None) is not None else None),
            human_motor_phase=(self.human_executor.phase if getattr(self, "human_executor", None) is not None else "unknown"),
        )

    def joint_position_step(self, joints):
        """Direct action entry for future IL/VLA adapters; attachment remains a separate abstraction."""
        values = np.asarray(joints, dtype=float)
        if values.shape != (9,) or not np.isfinite(values).all():
            raise ValueError("joint_position 需要 9 个有限关节值（7 臂关节 + 2 指关节）。")
        self.current_robot_action = "执行模型输出的关节位置目标"
        self.robot.control_dofs_position(values)
        self.tick(6)

    def continuous_start_action(self, action: Action):
        """启动一个可被逐 tick 推进或被新公开观测打断的动作块。"""
        if self.continuous_execution is not None:
            self.log.add(self.step_count, "robot_action_preempted",
                         previous=self.continuous_execution["action"].kind, next=action.kind)
            self.attachment = None
        self.log.add(self.step_count, "policy_action", action=action.kind,
                     object_id=action.object_id, destination=action.destination,
                     duration_steps=action.duration_steps)
        if action.kind == "transfer":
            if action.object_id not in self.objects or action.destination not in self.regions:
                raise ValueError(f"连续搬运目标不存在: {action}")
            source = np.asarray(self.positions()[action.object_id])
            destination = np.asarray(self.regions[action.destination])
            self.continuous_execution = {"action": action, "phase": "approach", "source": source,
                                         "destination": destination, "qgoal": None, "progress": 0,
                                         "phase_steps": 0}
            dynamics = self.scenario.dynamics
            delay = (int(self.continuous_rng.integers(1, dynamics.max_delay_steps + 1))
                     if dynamics.max_delay_steps > 0
                     and self.continuous_rng.random() < dynamics.robot_delay_probability else 0)
            self.continuous_execution["delay"] = delay * int(60 / self.scenario.tick_hz)
            budget_failure = self.remaining_failure_budget > 0
            if budget_failure:
                self.remaining_failure_budget -= 1
            self.continuous_execution["failed"] = budget_failure or bool(
                self.continuous_rng.random() < dynamics.robot_failure_probability)
            self.current_robot_action = f"连续搬运 {action.object_id} 到 {action.destination}"
        elif action.kind == "joint_position":
            values = np.asarray(action.joints, dtype=float)
            if values.shape != (9,) or not np.isfinite(values).all():
                raise ValueError("joint_position 需要 9 个有限关节值。")
            self.continuous_execution = {"action": action, "phase": "execute", "qgoal": values,
                                         "progress": 0}
        elif action.kind in {"request_help", "acknowledge"}:
            self.say(Message("robot", action.kind, action.text, action.object_id, None, action.destination))
            self.continuous_execution = {"action": action, "phase": "communicate", "progress": 0}
        elif action.kind in {"wait", "finish"}:
            self.continuous_execution = {"action": action, "phase": "execute", "progress": 0}
        else:
            raise ValueError(f"未知连续动作: {action.kind}")

    def continuous_apply_human_command(self, command):
        """把伙伴的当前意图映射到 AvatarController 的非阻塞动作。"""
        self.continuous_human_command = command
        self.log.add(self.step_count, "human_command", intent=command.intent,
                     object_id=command.object_id, destination=command.destination,
                     target=command.target, speed_mps=float(command.speed_mps),
                     acceleration_mps2=float(command.acceleration_mps2),
                     gaze_target=command.gaze_target)
        from .continuous import _prerequisites_satisfied
        if not self.avatar.spare():
            return
        if command.intent in {"away", "yield", "return"} and command.target is not None:
            delta = np.asarray(command.target)[:2] - self.avatar.get_global_pose()[:2]
            distance = float(np.linalg.norm(delta))
            if distance > 0.07:
                direction = delta / distance
                self.avatar.robot.global_rot = np.array([
                    [direction[0], -direction[1], 0],
                    [direction[1], direction[0], 0], [0, 0, 1]])
                tick_hz = float(getattr(self.scenario, "tick_hz", 10.0))
                self.avatar.walk(min(distance, max(0.07, float(command.speed_mps) / tick_hz)))
            return
        if not command.object_id:
            return
        held = self.held_by_human()
        if command.intent == "approach" and not held and command.object_id in self.objects:
            execution = self.continuous_execution
            if execution is not None and execution["action"].object_id == command.object_id:
                self.log.add(self.step_count, "human_blocked_by_robot_claim", object_id=command.object_id)
                return
            self.avatar.pick(1, self.objects[command.object_id])
            self.continuous_human_phase = "picking"
        elif command.intent == "carry" and command.object_id in held and command.destination in self.regions:
            if not _prerequisites_satisfied(self.scenario, "human", command.object_id,
                                           command.destination, self.completed_skills):
                return
            self.avatar.put(1, np.asarray(self.regions[command.destination]), rotation=np.eye(3, dtype=float))
            self.continuous_human_phase = "placing"
            self.continuous_pending_placement = (command.object_id, command.destination)

    def _continuous_fail(self, execution, reason, *, blocked=False):
        action = execution["action"]
        self.attachment = None
        self.say(Message("robot", "action_blocked" if blocked else "action_failed",
                         "当前搬运未提交，需要等待或重新分工。", action.object_id,
                         reason, action.destination))
        self.log.add(self.step_count, "robot_transfer_blocked" if blocked else "robot_action_failed",
                     object_id=action.object_id, destination=action.destination, reason=reason)
        self.continuous_execution = None

    def _continuous_robot_step(self):
        execution = self.continuous_execution
        if execution is None:
            return
        action = execution["action"]
        execution["progress"] += 1
        execution["phase_steps"] = execution.get("phase_steps", 0) + 1
        if action.kind == "transfer":
            from .continuous import _prerequisites_satisfied
            if execution.get("delay", 0) > 0:
                if execution["phase"] != "delayed":
                    self.say(Message("robot", "action_delayed", "当前动作出现可见延迟。",
                                     action.object_id, "synthetic_delay", action.destination))
                    self.log.add(self.step_count, "robot_action_delayed", object_id=action.object_id,
                                 destination=action.destination, source="scenario_synthetic_dynamics")
                execution["phase"] = "delayed"
                execution["delay"] -= 1
                self.continuous_delay_frames += 1
                return
            if execution.get("failed"):
                self._continuous_fail(execution, "scenario_synthetic_failure")
                return
            if execution["phase"] == "delayed":
                execution["phase"] = "approach"
                execution["progress"] = 0
                execution["phase_steps"] = 0
            if execution["progress"] > 240:
                self._continuous_fail(execution, "ik_tracking_timeout")
                return
            phase = execution["phase"]
            source = execution["source"]
            destination = execution["destination"]
            if phase == "approach":
                if action.object_id in self.held_by_human():
                    self._continuous_fail(execution, "human_holding", blocked=True)
                    return
                target = source + [0, 0, 0.20]
                execution["qgoal"] = self._continuous_ik(target, 0.04)
                if (self._continuous_at(target)
                        and execution["phase_steps"] >= self.minimum_transfer_phase_steps):
                    execution["phase"] = "grasp"
                    execution["progress"] = 0
                    execution["phase_steps"] = 0
            elif phase == "grasp":
                target = source + [0, 0, 0.10]
                execution["qgoal"] = self._continuous_ik(target, 0.025)
                if action.object_id in self.held_by_human():
                    self._continuous_fail(execution, "human_holding", blocked=True)
                    return
                if (execution["progress"] >= 10 and self._continuous_at(target)
                        and execution["phase_steps"] >= self.minimum_transfer_phase_steps):
                    self.attachment = (action.object_id, source - self.ee.get_pos().cpu().numpy())
                    execution["phase"] = "carry"
                    execution["progress"] = 0
                    execution["phase_steps"] = 0
                    self.log.add(self.step_count, "abstract_grasp_attached", object_id=action.object_id)
            elif phase == "carry":
                target = destination + [0, 0, 0.14]
                execution["qgoal"] = self._continuous_ik(target, 0.025)
                if (self._continuous_at(target)
                        and execution["phase_steps"] >= self.minimum_transfer_phase_steps):
                    execution["phase"] = "release"
                    execution["progress"] = 0
                    execution["phase_steps"] = 0
            elif phase == "release":
                if execution["phase_steps"] < self.minimum_transfer_phase_steps:
                    execution["qgoal"] = self._continuous_ik(destination + [0, 0, 0.14], 0.04)
                    if execution.get("qgoal") is not None:
                        self._control_robot_position(execution["qgoal"])
                    return
                if not _prerequisites_satisfied(self.scenario, "robot", action.object_id,
                                               action.destination, self.completed_skills):
                    self._continuous_fail(execution, "prerequisite", blocked=True)
                    return
                self.attachment = None
                self.objects[action.object_id].set_pos(destination)
                self.completed_skills.append(f"robot:{action.object_id}:{action.destination}")
                self.log.add(self.step_count, "robot_transfer_completed", object_id=action.object_id,
                             destination=action.destination, measured_position=self.positions()[action.object_id])
                execution["phase"] = "retreat"
                execution["progress"] = 0
                execution["phase_steps"] = 0
            elif phase == "retreat":
                target = destination + [0, 0, 0.30]
                execution["qgoal"] = self._continuous_ik(target, 0.04)
                if ((self._continuous_at(target)
                     and execution["phase_steps"] >= self.minimum_transfer_phase_steps)
                        or execution["progress"] >= 80):
                    self.continuous_execution = None
            if execution.get("qgoal") is not None:
                self._control_robot_position(execution["qgoal"])
        elif action.kind == "joint_position":
            self._control_robot_position(execution["qgoal"])
            self._continuous_joint_grasp()
            if execution["progress"] >= self._continuous_duration(action):
                self.continuous_execution = None
        elif execution["progress"] >= self._continuous_duration(action):
            self.continuous_execution = None

    def _continuous_duration(self, action):
        return max(1, action.duration_steps) * int(60 / getattr(self.scenario, "tick_hz", 60))

    def _control_robot_position(self, target):
        self.robot.control_dofs_position(target)

    def _after_physics_step(self):
        pass

    def _continuous_joint_grasp(self):
        """底层关节策略的几何抓放抽象，不读取动作中的语义目标。

        物体依然是运动学绑定，不表示接触或力闭合。闭合时仅考虑指间点附近
        的物体；打开时在当前实际位置释放，不能按私有目标自动移动到区域。
        """
        from .robot_control import hand_rotation, select_grasp_candidate
        qpos = self.robot.get_qpos().cpu().numpy()
        width = float(qpos[-2:].sum())
        if self.attachment is not None:
            if width >= 0.065:
                name, _ = self.attachment
                self.attachment = None
                self.log.add(self.step_count, "abstract_grasp_released", object_id=name,
                             source="joint_control", position=self.positions()[name])
                for destination, region in self.regions.items():
                    if math.dist(self.positions()[name], region) < 0.065:
                        from .continuous import _prerequisites_satisfied
                        if _prerequisites_satisfied(self.scenario, "robot", name, destination, self.completed_skills):
                            skill = f"robot:{name}:{destination}"
                            if skill not in self.completed_skills:
                                self.completed_skills.append(skill)
                                self.log.add(self.step_count, "robot_transfer_completed", object_id=name,
                                             destination=destination, source="joint_control")
                        else:
                            self.say(Message("robot", "action_blocked", "物体已释放，但前置贡献或交接约束尚未满足。",
                                             name, "prerequisite", destination))
                            self.log.add(self.step_count, "robot_transfer_blocked", object_id=name,
                                         destination=destination, source="joint_control")
            return
        if width > 0.045:
            return
        hand = self.ee.get_pos().cpu().numpy()
        point = hand + hand_rotation(self.ee.get_quat().cpu().numpy()) @ np.array([0, 0, 0.10])
        candidate = select_grasp_candidate(point, self.positions(), excluded=self.held_by_human())
        if candidate is not None:
            self.attachment = (candidate, np.asarray(self.positions()[candidate]) - hand)
            self.log.add(self.step_count, "abstract_grasp_attached", object_id=candidate, source="joint_control")

    def _continuous_ik(self, target, fingers):
        qgoal = self.robot.inverse_kinematics(link=self.ee, pos=np.asarray(target),
                                              quat=np.array([0., 1., 0., 0.])).cpu().numpy()
        qgoal[-2:] = fingers
        return qgoal

    def _continuous_at(self, target):
        return float(np.linalg.norm(self.ee.get_pos().cpu().numpy() - np.asarray(target))) < 0.065

    def tick(self, steps=1):
        for _ in range(steps):
            self._continuous_robot_step()
            self._continuous_human_step()
            self.avatar.step()
            self.avatar.robot.update()
            self.scene.step()
            self._after_physics_step()
            pending = self.continuous_pending_placement
            if pending is not None and self.avatar.spare():
                object_id, destination = pending
                if (object_id not in self.held_by_human()
                        and math.dist(self.positions()[object_id], self.regions[destination]) < 0.065):
                    self.completed_skills.append(f"human:{object_id}:{destination}")
                    self.log.add(self.step_count, "human_transfer_completed", object_id=object_id,
                                 destination=destination)
                self.continuous_pending_placement = None
            if self.attachment is not None:
                name, offset = self.attachment
                self.objects[name].set_pos(self.ee.get_pos().cpu().numpy() + offset)
                self.objects[name].set_quat(np.array([1., 0., 0., 0.]))
            self.step_count += 1
            self.capture()

    def capture(self, force=False):
        if self.writer is None:
            return
        if not force and self.step_count % self.stride:
            return
        rgb = np.asarray(self.camera.render(rgb=True)[0], dtype=np.uint8)
        canvas = Image.new("RGB", (rgb.shape[1], rgb.shape[0] + 124), "#101a2c")
        canvas.paste(Image.fromarray(rgb), (0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((12, 12, 300, 43), radius=5, fill="#101a2c")
        draw.text((21, 17), "蓝色底板：收纳区   绿色底板：留用区", font=self.small_font, fill="white")
        h = rgb.shape[0]
        draw.text((15, h + 6), "HRC · Continuous Collaboration / VC-Genesis", font=self.font, fill="#91d3ff")
        draw.text((15, h + 35), f"{self.title}   |   执行步 {self.step_count}", font=self.small_font, fill="white")
        draw.text((15, h + 60), f"机器人：{self.current_robot_action}", font=self.small_font, fill="#d5def0")
        latest = self.messages[-1] if self.messages else None
        if latest:
            draw.text((15, h + 85), f"{'人' if latest.speaker == 'human' else '机器人'}：{latest.text}",
                      font=self.small_font, fill="#ffe6a5")
        frame = np.asarray(canvas)
        self.writer.append_data(frame)
        self.video_frames.append({
            "frame_index": len(self.video_frames),
            "video_time_s": len(self.video_frames) / self.video_fps,
            "physics_step": self.step_count,
            "phase": self.video_phase,
            "benchmark_time_s": self.step_count / 60 if self.video_phase == "benchmark" else None,
        })
        if force:
            Image.fromarray(frame).save(self.output / "preview.png")
        r = self.avatar.robot
        self.trace.append({
            "step": self.step_count, "qpos": self.robot.get_qpos().cpu().numpy().copy(),
            "objects": np.array([self.positions()[name] for name in self.objects]),
            "human_pose": r.pose.copy(), "human_global_trans": r.global_trans.copy(),
            "human_global_rot": r.global_rot.copy(), "human_node_trans": np.array(r.node_trans).copy(),
            "human_global_mat": r.global_mat.copy(), "human_global_mat_inv": r.global_mat_inv.copy(),
        })

    def move_ee(self, target, *, fingers=0.04, probe=None):
        target = np.asarray(target, dtype=float)
        qgoal = self.robot.inverse_kinematics(link=self.ee, pos=target, quat=np.array([0., 1., 0., 0.]))
        qgoal = qgoal.cpu().numpy()
        qgoal[-2:] = fingers
        qstart = self.robot.get_qpos().cpu().numpy()
        for alpha in np.linspace(0, 1, 45):
            self.robot.control_dofs_position((1 - alpha) * qstart + alpha * qgoal)
            self.tick(1)
            if probe is not None and probe():
                self.robot.control_dofs_position(self.robot.get_qpos())
                return False
        self.robot.control_dofs_position(qgoal)
        self.tick(25)
        error = float(np.linalg.norm(self.ee.get_pos().cpu().numpy() - target))
        self.log.add(self.step_count, "robot_waypoint", target=target.tolist(), tracking_error_m=error)
        if error > 0.065:
            self.log.add(self.step_count, "skill_failed", reason="ee_tracking", error_m=error)
            return False
        return True

    def inspect_and_respond(self, partner):
        self.current_robot_action = "接近红杯观察；尚未抓取"
        intervention = None

        def probe():
            nonlocal intervention
            # This callback uses visible EE/object positions, not the robot target or plan.
            positions = self.positions()
            distance = math.dist(self.ee.get_pos().cpu().numpy(), positions["red"])
            intervention = partner.on_visible_approach("red", distance)
            return intervention is not None

        red = np.array(self.positions()["red"])
        self.move_ee(red + [0, 0, 0.20], probe=probe)
        if intervention:
            self.log.add(self.step_count, "robot_skill_interrupted", skill="inspect", cause="partner_response")
            if intervention == "information":
                before = self.positions()
                self.log.add(self.step_count, "partner_understanding_updated", previous="pack", current="keep",
                    evidence="伙伴收到红杯仍需本地使用的新信息", physical_state_unchanged=before == self.positions(),
                    before_positions=before, after_positions=self.positions())
                self.say(partner.correction_message())
                self.tick(36)
            else:
                self.move_ee([0.20, -0.18, 1.18])
                self.human_transfer("red", "keep_red")
                self.say(partner.movement_message())
                self.tick(36)
        self.move_ee([0.20, -0.18, 1.18])

    def human_transfer(self, name, destination):
        from vico.modules.avatar.utils import AvatarState
        self.log.add(self.step_count, "human_transfer_started", object_id=name, destination=destination)
        self.avatar.pick(1, self.objects[name])
        for _ in range(240):
            self.tick(1)
            if self.avatar.robot.action_state == AvatarState.NO_ACTION:
                break
        if self.avatar.robot.attached_object[1] is not self.objects[name]:
            self.log.add(self.step_count, "skill_failed", reason="human_pick", object_id=name)
            return False
        self.avatar.put(1, np.array(self.regions[destination]), rotation=np.eye(3, dtype=float))
        for _ in range(240):
            self.tick(1)
            if self.avatar.robot.action_state == AvatarState.NO_ACTION:
                break
        if self.avatar.robot.attached_object[1] is not None:
            self.log.add(self.step_count, "skill_failed", reason="human_put_timeout", object_id=name)
            return False
        self.completed_skills.append(f"human:{name}:{destination}")
        self.log.add(self.step_count, "human_transfer_completed", object_id=name, destination=destination,
                     measured_position=self.positions()[name])
        return True

    def robot_transfer(self, name, destination):
        self.current_robot_action = f"将{'红' if name == 'red' else '蓝'}杯放入收纳区"
        self.log.add(self.step_count, "robot_transfer_started", object_id=name, destination=destination)
        source = np.array(self.positions()[name])
        for target in (source + [0, 0, 0.23], source + [0, 0, 0.13]):
            if not self.move_ee(target):
                return False
        offset = source - self.ee.get_pos().cpu().numpy()
        self.attachment = (name, offset)
        self.log.add(self.step_count, "abstract_grasp_attached", object_id=name, offset=offset.tolist())
        destination_pos = np.array(self.regions[destination])
        for target in (source + [0, 0, 0.28], destination_pos - offset + [0, 0, 0.16], destination_pos - offset):
            if not self.move_ee(target, fingers=0.025):
                self.attachment = None
                return False
        self.attachment = None
        self.tick(8)
        self.completed_skills.append(f"robot:{name}:{destination}")
        self.log.add(self.step_count, "robot_transfer_completed", object_id=name, destination=destination,
                     measured_position=self.positions()[name])
        self.move_ee(destination_pos + [0, 0, 0.32])
        return True

    def finish_episode(self, settle_steps=24):
        self.tick(settle_steps)
        self.capture(force=True)
        self.writer.close()
        self.writer = None
        (self.output / "video_timeline.json").write_text(json.dumps({
            "fps": self.video_fps, "physics_hz": 60,
            "frame_count": len(self.video_frames), "frames": self.video_frames,
            "source": "runtime_genesis_camera", "grasp_model": self.robot_grasp_model,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        arrays = {key: np.stack([row[key] for row in self.trace]) for key in self.trace[0]}
        arrays["object_names"] = np.array(list(self.objects))
        np.savez_compressed(self.output / "trajectory.npz", **arrays)
        (self.output / "events.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in self.log.events) + "\n")

    def close(self):
        if self.writer is not None:
            self.writer.close()
            self.writer = None
        self.gs.destroy()
