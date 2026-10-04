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
                 render_stride: int = 3, viewer: bool = False, scenario=None):
        import genesis as gs
        from vico.modules.avatar.avatar_controller import AvatarController
        from .assets import mug_mesh

        self.gs = gs
        gs.init(seed=0, backend=gs.gpu if backend == "gpu" else gs.cpu,
                logging_level=logging.WARNING, theme="dumb")
        self.scene = gs.Scene(
            sim_options=gs.options.SimOptions(dt=1 / 60, substeps=4),
            rigid_options=gs.options.RigidOptions(enable_collision=True, max_collision_pairs=512),
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
            # Fixed collision-free props explicitly implement the abstract grasp layer.
            self.objects[name] = self.add_entity("object", name,
                gs.morphs.Mesh(file=mug_file, pos=pos, fixed=True, collision=False,
                               decimate=False, convexify=False),
                surface=gs.surfaces.Default(color=color))
        self.robot = self.add_entity("robot", "franka",
            gs.morphs.MJCF(file="xml/franka_emika_panda/panda.xml", pos=(-0.10, 0, 0.76)))
        self.avatar = AvatarController(
            env=self, name="pilot_partner", motion_data_path="avatars/motions/motion.pkl",
            skin_options={"glb_path": str(assets / "avatars/models/mixamo_Alex_Jefferson.glb"),
                          "euler": (-90, 0, 90), "pos": (0, 0, -0.959008030)},
            frame_ratio=0.30, enable_collision=False,
        )
        self.camera = self.scene.add_camera(res=(resolution, resolution * 3 // 4),
            pos=(2.05, -2.35, 2.30), lookat=(0.35, 0.20, 0.94), fov=48, GUI=False)
        self.robot_camera = self.scene.add_camera(res=(320, 240),
            pos=(-0.48, -0.42, 1.50), lookat=(0.48, 0.12, 0.88), fov=65, GUI=False)
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

    def add_entity(self, type, name, morph, material=None, surface=None, **kwargs):
        entity = self.scene.add_entity(morph=morph, material=material, surface=surface, **kwargs)
        self.entity_info[entity.idx] = {"type": type, "name": name}
        return entity

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
        self.current_robot_action = "观察共同工作空间"
        self.title = f"{scenario} · {policy} · seed {seed}"
        self.writer = imageio.get_writer(str(output / "demo.mp4"), fps=60 // self.stride,
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
        execution = self.continuous_execution
        active_action = "idle" if execution is None else execution["action"].kind
        phase = "idle" if execution is None else execution.get("phase", "execute")
        return Observation(
            objects={k: tuple(v) for k, v in self.positions().items()}, regions=dict(self.regions),
            messages=tuple(self.messages), robot_ee=tuple(self.ee.get_pos().cpu().numpy().tolist()),
            human_position=tuple(self.avatar.get_global_pose()[:3].tolist()),
            held_by_human=self.held_by_human(), completed_skills=tuple(self.completed_skills),
            robot_qpos=tuple(self.robot.get_qpos().cpu().numpy().tolist()),
            rgb=np.asarray(rgb, dtype=np.uint8).copy(),
            time_s=float(self.step_count) / 60.0,
            active_robot_action=active_action,
            action_phase=phase,
            visible_human_action=(getattr(self.continuous_human_command, "intent", "observe")
                                  if self.continuous_human_command is not None else "observe"),
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
        if action.kind == "transfer":
            if action.object_id not in self.objects or action.destination not in self.regions:
                raise ValueError(f"连续搬运目标不存在: {action}")
            source = np.asarray(self.positions()[action.object_id])
            destination = np.asarray(self.regions[action.destination])
            self.continuous_execution = {"action": action, "phase": "approach", "source": source,
                                         "destination": destination, "qgoal": None, "progress": 0}
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
        try:
            from vico.modules.avatar.utils import AvatarState
        except ImportError:
            return
        if self.avatar.robot.action_state != AvatarState.NO_ACTION or not command.object_id:
            return
        held = self.held_by_human()
        if command.intent == "approach" and not held and command.object_id in self.objects:
            self.avatar.pick(1, self.objects[command.object_id])
            self.continuous_human_phase = "picking"
        elif command.intent == "carry" and command.object_id in held and command.destination in self.regions:
            self.avatar.put(1, np.asarray(self.regions[command.destination]), rotation=np.eye(3, dtype=float))
            self.continuous_human_phase = "placing"

    def _continuous_robot_step(self):
        execution = self.continuous_execution
        if execution is None:
            return
        action = execution["action"]
        execution["progress"] += 1
        if action.kind == "transfer":
            phase = execution["phase"]
            source = execution["source"]
            destination = execution["destination"]
            if phase == "approach":
                target = source + [0, 0, 0.20]
                execution["qgoal"] = self._continuous_ik(target, 0.04)
                if self._continuous_at(target):
                    execution["phase"] = "grasp"
                    execution["progress"] = 0
            elif phase == "grasp":
                target = source + [0, 0, 0.10]
                execution["qgoal"] = self._continuous_ik(target, 0.025)
                if execution["progress"] >= 10:
                    self.attachment = (action.object_id, source - self.ee.get_pos().cpu().numpy())
                    execution["phase"] = "carry"
                    execution["progress"] = 0
                    self.log.add(self.step_count, "abstract_grasp_attached", object_id=action.object_id)
            elif phase == "carry":
                target = destination + [0, 0, 0.14]
                execution["qgoal"] = self._continuous_ik(target, 0.025)
                if self._continuous_at(target):
                    execution["phase"] = "release"
                    execution["progress"] = 0
            elif phase == "release":
                self.attachment = None
                self.objects[action.object_id].set_pos(destination)
                self.completed_skills.append(f"robot:{action.object_id}:{action.destination}")
                self.log.add(self.step_count, "robot_transfer_completed", object_id=action.object_id,
                             destination=action.destination, measured_position=self.positions()[action.object_id])
                execution["phase"] = "retreat"
                execution["progress"] = 0
            elif phase == "retreat":
                target = destination + [0, 0, 0.30]
                execution["qgoal"] = self._continuous_ik(target, 0.04)
                if self._continuous_at(target) or execution["progress"] >= 80:
                    self.continuous_execution = None
            if execution.get("qgoal") is not None:
                self.robot.control_dofs_position(execution["qgoal"])
        elif action.kind == "joint_position":
            self.robot.control_dofs_position(execution["qgoal"])
            if execution["progress"] >= max(1, action.duration_steps):
                self.continuous_execution = None
        elif execution["progress"] >= max(1, action.duration_steps):
            self.continuous_execution = None

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
            self.avatar.step()
            self.avatar.robot.update()
            self.scene.step()
            if self.attachment is not None:
                name, offset = self.attachment
                self.objects[name].set_pos(self.ee.get_pos().cpu().numpy() + offset)
                self.objects[name].set_quat(np.array([1., 0., 0., 0.]))
            self.step_count += 1
            self.capture()

    def capture(self, force=False):
        if not force and self.step_count % self.stride:
            return
        rgb = np.asarray(self.camera.render(rgb=True)[0], dtype=np.uint8)
        canvas = Image.new("RGB", (rgb.shape[1], rgb.shape[0] + 124), "#101a2c")
        canvas.paste(Image.fromarray(rgb), (0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((12, 12, 300, 43), radius=5, fill="#101a2c")
        draw.text((21, 17), "蓝色底板：收纳区   绿色底板：留用区", font=self.small_font, fill="white")
        h = rgb.shape[0]
        draw.text((15, h + 6), "HRC · Progressively Rebalanced Collaboration / Pilot v1", font=self.font, fill="#91d3ff")
        draw.text((15, h + 35), f"{self.title}   |   执行步 {self.step_count}", font=self.small_font, fill="white")
        draw.text((15, h + 60), f"机器人：{self.current_robot_action}", font=self.small_font, fill="#d5def0")
        latest = self.messages[-1] if self.messages else None
        if latest:
            draw.text((15, h + 85), f"{'人' if latest.speaker == 'human' else '机器人'}：{latest.text}",
                      font=self.small_font, fill="#ffe6a5")
        frame = np.asarray(canvas)
        self.writer.append_data(frame)
        if force:
            Image.fromarray(frame).save(self.output / "preview.png")
        r = self.avatar.robot
        self.trace.append({
            "step": self.step_count, "qpos": self.robot.get_qpos().cpu().numpy().copy(),
            "objects": np.array([self.positions()[n] for n in ("red", "blue")]),
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

    def finish_episode(self):
        self.tick(24)
        self.capture(force=True)
        self.writer.close()
        self.writer = None
        arrays = {key: np.stack([row[key] for row in self.trace]) for key in self.trace[0]}
        np.savez_compressed(self.output / "trajectory.npz", **arrays)
        (self.output / "events.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in self.log.events) + "\n")

    def close(self):
        if self.writer is not None:
            self.writer.close()
        self.gs.destroy()
