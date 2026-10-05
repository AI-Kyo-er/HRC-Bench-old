"""VC/Genesis 的逐 tick 适配面。

模块延迟导入 Genesis，因而协议测试不需要 GPU。真实运行时可用这个适配
面替换 `ContinuousWorld`，仍沿用同一个 Policy、Partner 和 action chunk。
"""
from __future__ import annotations

from pathlib import Path
import math

from .backend import VCWorkspace
from .continuous import HumanCommand
from .protocol import Action, Message, Observation


class GenesisContinuousAdapter:
    def __init__(self, workspace: VCWorkspace, scenario=None, output_root: Path | None = None,
                 policy: str = "external_model"):
        self.workspace = workspace
        self.scenario = scenario or workspace.scenario
        self.output_root = output_root
        self.policy = policy
        self.episode_output = None
        self.physics_steps_per_tick = 60 / self.scenario.tick_hz
        if not self.physics_steps_per_tick.is_integer() or self.physics_steps_per_tick < 1:
            raise ValueError("Genesis 的 tick_hz 必须是 60 的正整数约数")
        self.physics_steps_per_tick = int(self.physics_steps_per_tick)

    def bind_output(self, output: Path | None) -> None:
        self.episode_output = output

    def reset(self, seed: int) -> None:
        if self.scenario is None:
            raise RuntimeError("GenesisContinuousAdapter 需要绑定 ContinuousScenario")
        output = self.episode_output or (self.output_root / self.scenario.name if self.output_root is not None
                                        else self.workspace.output)
        if output is None:
            raise RuntimeError("GenesisContinuousAdapter 需要 output_root 或 workspace.output")
        self.workspace.begin_episode(output, self.scenario.name, self.policy, seed)
        self.workspace.step_count = 0
        self.workspace.log.events.clear()
        self.workspace.trace.clear()
        self.workspace.video_phase = "benchmark"
        self.workspace.capture(force=True)
        self.record_event("initial_state", positions=self.workspace.positions())

    def observe(self) -> Observation:
        return self.workspace.observe()

    def start_action(self, action: Action) -> None:
        self.workspace.continuous_start_action(action)

    def say(self, message: Message) -> None:
        self.workspace.say(message)

    def record_event(self, kind: str, **data) -> None:
        data.pop("step", None)
        self.workspace.log.add(self.workspace.step_count, kind, **data)

    def apply_human_command(self, command: HumanCommand) -> None:
        self.workspace.continuous_apply_human_command(command)

    def tick(self) -> None:
        self.workspace.tick(self.physics_steps_per_tick)

    def finish_episode(self) -> None:
        self.workspace.finish_episode(settle_steps=0)

    def close(self) -> None:
        self.workspace.close()

    @property
    def last_observation_path(self):
        return self.workspace.last_observation_path

    @property
    def action_active(self) -> bool:
        return self.workspace.continuous_execution is not None

    @property
    def events(self):
        return [{**event, "physics_step": event["step"],
                 "step": event["step"] / self.physics_steps_per_tick}
                for event in self.workspace.log.events]

    @property
    def robot_failures(self):
        return sum(event["kind"] == "robot_action_failed" for event in self.events)

    @property
    def robot_delay_steps(self):
        return self.workspace.continuous_delay_frames / self.physics_steps_per_tick

    @property
    def interruptions(self):
        return sum(event["kind"] == "robot_action_preempted" for event in self.events)

    @property
    def robot_action_count(self):
        return sum(event["kind"] == "policy_action" for event in self.events)

    def _placed(self, object_id, destination) -> bool:
        positions = self.workspace.positions()
        held = set(self.workspace.held_by_human())
        attachment = getattr(self.workspace, "attachment", None)
        if attachment is not None:
            held.add(attachment[0])
        return (object_id in positions and object_id not in held
                and destination in self.workspace.regions
                and math.dist(positions[object_id], self.workspace.regions[destination]) < 0.065)

    @property
    def messages(self):
        return self.workspace.messages

    @property
    def completed_skills(self):
        return self.workspace.completed_skills

    def finished_robot(self) -> bool:
        if self.scenario is None:
            return False
        return all(self._placed(object_id, destination)
                   for object_id, destination in self.scenario.robot_targets.items())

    def finished_human(self) -> bool:
        if self.scenario is None:
            return False
        return all(self._placed(object_id, destination)
                   for object_id, destination in self.scenario.human_targets.items())

    def finished_activity(self) -> bool:
        """按 ActivityContract 的工作项检查真实后端终态。

        不能把机器人和人类的初始角色目标当作活动成功；失败后的接管
        仍然应该被计为成功，只要每个声明的工作项达到了其目标区域。
        """
        if self.scenario is None:
            return False
        for item in self.scenario.resolved_activity().work_items:
            if not self._placed(item.object_id, item.destination):
                return False
        return True


def make_genesis_backend_factory(*, assets: Path, output_root: Path, backend: str = "gpu",
                                 resolution: int = 800, render_stride: int = 3,
                                 viewer: bool = False, policy: str = "external_model"):
    """返回可直接交给 `run_continuous_episode` 的 Genesis backend 工厂。"""
    def factory(scenario):
        workspace = VCWorkspace(assets=assets, backend=backend, resolution=resolution,
                                render_stride=render_stride, viewer=viewer, scenario=scenario)
        return GenesisContinuousAdapter(workspace, scenario=scenario, output_root=output_root,
                                        policy=policy)
    return factory
