"""VC/Genesis 的逐 tick 适配面。

模块延迟导入 Genesis，因而协议测试不需要 GPU。真实运行时可用这个适配
面替换 `ContinuousWorld`，仍沿用同一个 Policy、Partner 和 action chunk。
"""
from __future__ import annotations

from pathlib import Path

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

    def reset(self, seed: int) -> None:
        if self.scenario is None:
            raise RuntimeError("GenesisContinuousAdapter 需要绑定 ContinuousScenario")
        output = (self.output_root / self.scenario.name if self.output_root is not None
                  else self.workspace.output)
        if output is None:
            raise RuntimeError("GenesisContinuousAdapter 需要 output_root 或 workspace.output")
        self.workspace.begin_episode(output, self.scenario.name, self.policy, seed)

    def observe(self) -> Observation:
        return self.workspace.observe()

    def start_action(self, action: Action) -> None:
        self.workspace.continuous_start_action(action)

    def say(self, message: Message) -> None:
        self.workspace.say(message)

    def record_event(self, kind: str, **data) -> None:
        self.workspace.log.add(self.workspace.step_count, kind, **data)

    def apply_human_command(self, command: HumanCommand) -> None:
        self.workspace.continuous_apply_human_command(command)

    def tick(self) -> None:
        self.workspace.tick(1)

    @property
    def action_active(self) -> bool:
        return self.workspace.continuous_execution is not None

    @property
    def events(self):
        return self.workspace.log.events

    @property
    def messages(self):
        return self.workspace.messages

    @property
    def completed_skills(self):
        return self.workspace.completed_skills

    def finished_robot(self) -> bool:
        if self.scenario is None:
            return False
        positions = self.workspace.positions()
        return all(object_id in positions and destination in self.workspace.regions
                   and sum((positions[object_id][i] - self.workspace.regions[destination][i]) ** 2
                           for i in range(3)) ** 0.5 < 0.065
                   for object_id, destination in self.scenario.robot_targets.items())

    def finished_human(self) -> bool:
        if self.scenario is None:
            return False
        positions = self.workspace.positions()
        held = set(self.workspace.held_by_human())
        return all(object_id in positions and object_id not in held and destination in self.workspace.regions
                   and sum((positions[object_id][i] - self.workspace.regions[destination][i]) ** 2
                           for i in range(3)) ** 0.5 < 0.065
                   for object_id, destination in self.scenario.human_targets.items())

    def finished_activity(self) -> bool:
        """按 ActivityContract 的工作项检查真实后端终态。

        不能把机器人和人类的初始角色目标当作活动成功；失败后的接管
        仍然应该被计为成功，只要每个声明的工作项达到了其目标区域。
        """
        if self.scenario is None:
            return False
        positions = self.workspace.positions()
        for item in self.scenario.resolved_activity().work_items:
            if item.object_id not in positions or item.destination not in self.workspace.regions:
                return False
            distance = sum((positions[item.object_id][i] - self.workspace.regions[item.destination][i]) ** 2
                           for i in range(3)) ** 0.5
            if distance >= 0.065:
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
