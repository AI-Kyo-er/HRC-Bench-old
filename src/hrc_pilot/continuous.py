"""逐 tick 的持续协作运行时与可组合场景。

该模块把场景条件、伙伴的潜在目标和机器人的公开输入分开。场景不再
通过一串预先安排的事件推进；机器人和伙伴在同一个连续时间轴上根据
当前公开观测重新选择动作。`ContinuousWorld` 是可测试的参考后端，真实
Genesis 后端只需要实现同样的 `observe/start_action/tick` 适配面即可接入。
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import importlib
import json
import math
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from .protocol import Action, Message, Observation, serialize


@dataclass(frozen=True)
class ObjectSpec:
    name: str
    position: tuple[float, float, float]
    radius: float = 0.045


@dataclass(frozen=True)
class InteractionStructure:
    """描述交互作用之间的关系，而不是规定逐步事件脚本。

    ``segments`` 是可观察的作用类型，``dependencies`` 表示后一作用需要
    保留前一作用形成的公开约定，``concurrency`` 表示两个作用可以在同一
    时间窗内成立。它们是数据集划分和评测标签，不是驱动世界的状态机。
    """

    family: str
    segments: tuple[str, ...]
    dependencies: tuple[tuple[str, str], ...] = ()
    concurrency: tuple[tuple[str, str], ...] = ()
    split: str = "dev"


@dataclass(frozen=True)
class ContinuousScenario:
    name: str
    description: str
    objects: tuple[ObjectSpec, ...]
    regions: dict[str, tuple[float, float, float]]
    robot_targets: dict[str, str]
    human_targets: dict[str, str]
    human_availability: float = 0.75
    max_steps: int = 260
    tick_hz: float = 10.0
    # These fields describe a latent partner condition, rather than a fixed
    # event schedule. They are sampled once per episode and only influence the
    # partner's utility calculation.
    leave_trigger: str | None = None
    leave_probability: float = 0.0
    leave_duration_steps: int = 12
    structure: InteractionStructure = field(
        default_factory=lambda: InteractionStructure("isolated", ("joint_execution",)))
    condition: str = "compositional"

    def initial_messages(self) -> tuple[Message, ...]:
        messages = []
        for object_id, destination in self.human_targets.items():
            messages.append(Message("human", "assignment", f"我先处理 {object_id}，目标是 {destination}。",
                                    object_id, "human", destination))
        for object_id, destination in self.robot_targets.items():
            messages.append(Message("human", "assignment", f"请你处理 {object_id}，目标是 {destination}。",
                                    object_id, "robot", destination))
        return tuple(messages)


def _scene(name: str, description: str, human: dict[str, str], robot: dict[str, str],
           availability: float = 0.75, max_steps: int = 260, *,
           leave_trigger: str | None = None, leave_probability: float = 0.0,
           leave_duration_steps: int = 12,
           structure: InteractionStructure | None = None,
           condition: str = "compositional") -> ContinuousScenario:
    return ContinuousScenario(
        name=name,
        description=description,
        objects=(
            ObjectSpec("red", (0.42, 0.12, 0.82)),
            ObjectSpec("blue", (0.35, -0.08, 0.82)),
            ObjectSpec("green", (0.25, 0.16, 0.82)),
        ),
        regions={
            "tray_red": (0.60, -0.30, 0.82),
            "tray_blue": (0.42, -0.30, 0.82),
            "tray_green": (0.24, -0.30, 0.82),
            "keep_red": (0.60, 0.24, 0.82),
            "keep_blue": (0.42, 0.24, 0.82),
            "keep_green": (0.24, 0.24, 0.82),
        },
        robot_targets=robot,
        human_targets=human,
        human_availability=availability,
        max_steps=max_steps,
        leave_trigger=leave_trigger,
        leave_probability=leave_probability,
        leave_duration_steps=leave_duration_steps,
        structure=structure or InteractionStructure("isolated", ("joint_execution",)),
        condition=condition,
    )


CONTINUOUS_SCENARIOS: dict[str, ContinuousScenario] = {
    "relay": _scene("relay", "人先整理红杯，机器人在公开进度后接力蓝杯。",
                     {"red": "tray_red"}, {"blue": "tray_blue"},
                     structure=InteractionStructure("matched_serial",
                                                     ("guidance", "joint_execution"),
                                                     (("guidance", "joint_execution"),))),
    "nested_support": _scene("nested_support", "机器人处理主任务时，人插入一个局部支持贡献。",
                               {"green": "keep_green"}, {"red": "tray_red", "blue": "tray_blue"},
                               structure=InteractionStructure("nested",
                                                               ("joint_execution", "guidance", "joint_execution"),
                                                               (("joint_execution", "guidance"), ("guidance", "joint_execution")))),
    "concurrent_overlay": _scene("concurrent_overlay", "两边并行处理不同物体，靠持续可见行为避免占用冲突。",
                                  {"blue": "keep_blue"}, {"red": "tray_red", "green": "tray_green"},
                                  structure=InteractionStructure("concurrent",
                                                                  ("joint_execution", "intervention"),
                                                                  concurrency=(("joint_execution", "intervention"),))),
    "history_reinterpretation": _scene("history_reinterpretation", "共同活动中保留公开约定，同时允许新的用途信息改变分工。",
                                        {"red": "keep_red"}, {"blue": "tray_blue", "green": "tray_green"},
                                        structure=InteractionStructure("reinterpretation",
                                                                        ("guidance", "intervention", "guidance"),
                                                                        (("guidance", "intervention"), ("intervention", "guidance")))),
    "robot_induced_rebalance": _scene("robot_induced_rebalance", "机器人出现延迟后，伙伴根据可见进度接手未完成贡献。",
                                       {"blue": "tray_blue"}, {"red": "tray_red", "green": "tray_green"},
                                       availability=0.9, max_steps=300,
                                       structure=InteractionStructure("robot_initiated_rebalance",
                                                                       ("joint_execution", "guidance", "joint_execution"),
                                                                       (("joint_execution", "guidance"),))),
    "leave_and_return": _scene("leave_and_return", "伙伴暂时离开工作区，返回后依据剩余工作恢复协作。",
                                {"red": "keep_red", "blue": "tray_blue"}, {"green": "tray_green"},
                                availability=0.55, max_steps=320,
                                leave_trigger="human:red:keep_red", leave_probability=1.0,
                                structure=InteractionStructure("leave_return",
                                                                ("joint_execution", "intervention", "joint_execution"),
                                                                (("joint_execution", "intervention"), ("intervention", "joint_execution")))),
}


def generate_scenarios(count: int, *, seed: int = 0) -> list[ContinuousScenario]:
    """生成布局、分工和关系条件均可变化的 benchmark 实例。

    生成器只定义可执行的活动约束，不生成某个时刻必须发生的事件。每个
    实例仍由同一套公开协议运行，因此可把训练、开发和结构留出条件写成
    稳定的场景实例文件，而无需为每种轨迹维护状态机。
    """
    if count < 1:
        return []
    rng = np.random.default_rng(seed)
    names = ("red", "blue", "green")
    generated: list[ContinuousScenario] = []
    structure_catalog = (
        InteractionStructure("isolated", ("joint_execution",), split="train"),
        InteractionStructure("matched_serial", ("guidance", "joint_execution"),
                             (("guidance", "joint_execution"),), split="train"),
        InteractionStructure("nested", ("joint_execution", "guidance", "joint_execution"),
                             (("joint_execution", "guidance"), ("guidance", "joint_execution")), split="dev"),
        InteractionStructure("concurrent", ("joint_execution", "intervention"),
                             concurrency=(("joint_execution", "intervention"),), split="dev"),
        InteractionStructure("reinterpretation", ("guidance", "intervention", "guidance"),
                             (("guidance", "intervention"), ("intervention", "guidance")), split="test"),
        InteractionStructure("robot_initiated_rebalance", ("joint_execution", "guidance", "joint_execution"),
                             (("joint_execution", "guidance"),), split="test"),
        InteractionStructure("leave_return", ("joint_execution", "intervention", "joint_execution"),
                             (("joint_execution", "intervention"), ("intervention", "joint_execution")), split="test"),
    )
    for index in range(count):
        table_xy = rng.uniform([-0.06, -0.04], [0.06, 0.04])
        object_xy = np.array([(0.42, 0.12), (0.35, -0.08), (0.25, 0.16)], dtype=float)
        object_xy += table_xy + rng.normal(0.0, 0.018, object_xy.shape)
        regions_xy = np.array([(0.60, -0.30), (0.42, -0.30), (0.24, -0.30),
                               (0.60, 0.24), (0.42, 0.24), (0.24, 0.24)], dtype=float)
        regions_xy += rng.normal(0.0, 0.012, regions_xy.shape)
        objects = tuple(ObjectSpec(name, (float(object_xy[i, 0]), float(object_xy[i, 1]), 0.82))
                        for i, name in enumerate(names))
        region_names = ("tray_red", "tray_blue", "tray_green", "keep_red", "keep_blue", "keep_green")
        regions = {name: (float(regions_xy[i, 0]), float(regions_xy[i, 1]), 0.82)
                   for i, name in enumerate(region_names)}
        owners = list(rng.choice(np.array(["human", "robot"]), size=len(names), p=[0.5, 0.5]))
        if all(owner == "human" for owner in owners):
            owners[0] = "robot"
        if all(owner == "robot" for owner in owners):
            owners[0] = "human"
        human, robot = {}, {}
        for name, owner in zip(names, owners):
            destination = str(rng.choice([f"tray_{name}", f"keep_{name}"]))
            (human if owner == "human" else robot)[name] = destination
        leave_trigger = None
        leave_probability = 0.0
        if index % 4 == 3 and human:
            trigger_object, trigger_destination = next(iter(human.items()))
            leave_trigger = f"human:{trigger_object}:{trigger_destination}"
            leave_probability = 0.65
        structure = structure_catalog[index % len(structure_catalog)]
        condition = {
            "isolated": "isolated",
            "matched_serial": "matched_serial",
        }.get(structure.family, "compositional")
        generated.append(ContinuousScenario(
            name=f"generated_{index:03d}",
            description="随机布局、分工和伙伴可用性下的持续共同整理实例。",
            objects=objects,
            regions=regions,
            robot_targets=robot,
            human_targets=human,
            human_availability=float(rng.uniform(0.55, 0.95)),
            max_steps=360,
            leave_trigger=leave_trigger,
            leave_probability=leave_probability,
            structure=structure,
            condition=condition,
        ))
    return generated


def generate_benchmark_suite(*, count_per_condition: int = 2, seed: int = 0,
                             include_reference: bool = True) -> list[ContinuousScenario]:
    """生成可比较的结构条件集合。

    每个条件共享同一种物体布局和动作接口，但通过结构标签和分工生成
    不同的交互关系。``held_out`` 只出现在测试结构中，加载器可依据
    ``scenario.json`` 的 ``structure.split`` 做划分，不需要 manifest。
    """
    if count_per_condition < 1:
        return list(CONTINUOUS_SCENARIOS.values()) if include_reference else []
    rng = np.random.default_rng(seed)
    conditions = ("isolated", "matched_serial", "compositional", "held_out")
    scenarios: list[ContinuousScenario] = []
    base_scenarios = generate_scenarios(
        count_per_condition,
        seed=int(rng.integers(0, 2**31 - 1)),
    )
    for condition in conditions:
        for base_index, base in enumerate(base_scenarios):
            if condition == "isolated":
                structure = InteractionStructure("isolated", ("joint_execution",), split="train")
            elif condition == "matched_serial":
                structure = InteractionStructure("matched_serial", ("guidance", "joint_execution"),
                                                 (("guidance", "joint_execution"),), split="train")
            elif condition == "compositional":
                structure = InteractionStructure("nested", ("joint_execution", "guidance", "joint_execution"),
                                                 (("joint_execution", "guidance"), ("guidance", "joint_execution")), split="dev")
            else:
                structure = InteractionStructure("held_out_reinterpretation",
                                                 ("guidance", "intervention", "joint_execution"),
                                                 (("guidance", "intervention"), ("intervention", "joint_execution")), split="test")
            scenarios.append(replace(base, name=f"{condition}_{base_index:03d}",
                                     condition=condition, structure=structure))
    if include_reference:
        scenarios.extend(CONTINUOUS_SCENARIOS.values())
    return scenarios


@dataclass(frozen=True)
class HumanCommand:
    intent: str
    object_id: str | None = None
    destination: str | None = None
    target: tuple[float, float, float] | None = None
    text: str = ""


@dataclass(frozen=True)
class PartnerOutput:
    command: HumanCommand
    messages: tuple[Message, ...] = ()


class ContinuousPartner(Protocol):
    def reset(self, seed: int) -> None: ...
    def initial_messages(self) -> tuple[Message, ...]: ...
    def step(self, observation: Observation) -> PartnerOutput: ...


class AdaptivePartner:
    """一个冻结参数、但行为随可见进度更新的伙伴基线。

    它没有读取机器人的目标或场景评测标签。伙伴把可用性、信任、距离、
    任务紧迫性和机器人当前占用作为连续效用，逐 tick 选择下一步贡献。
    """

    def __init__(self, scenario: ContinuousScenario, *, stochastic: bool = False):
        self.scenario = scenario
        self.stochastic = stochastic
        self.reset(0)

    def reset(self, seed: int) -> None:
        self.rng = np.random.default_rng(seed)
        self.seen_messages = 0
        self.trust = 0.70
        self.workload = 0.0
        self.commitments = dict(self.scenario.human_targets)
        self.accepted_requests: dict[str, str] = {}
        self.current_object: str | None = None
        self.current_destination: str | None = None
        self.left_until = 0
        self.has_left = False
        self.last_robot_progress = 0.0
        self.messages_sent: list[Message] = []

    def initial_messages(self) -> tuple[Message, ...]:
        return self.scenario.initial_messages()

    def _process_messages(self, observation: Observation) -> list[Message]:
        outgoing: list[Message] = []
        for message in observation.messages[self.seen_messages:]:
            if message.speaker == "robot" and message.kind == "request_help" and message.object_id:
                load = self.workload + 0.25 * len(self.commitments)
                probability = np.clip(self.scenario.human_availability * self.trust - load * 0.08, 0.0, 1.0)
                accepted = bool(self.rng.random() < probability) if self.stochastic else probability >= 0.35
                if accepted:
                    destination = message.destination or f"tray_{message.object_id}"
                    self.accepted_requests[message.object_id] = destination
                    self.commitments[message.object_id] = destination
                    outgoing.append(Message("human", "help_reply", "我可以接手这个贡献。",
                                             message.object_id, "accept"))
                else:
                    outgoing.append(Message("human", "help_reply", "我现在无法接手，请你继续完成。",
                                             message.object_id, "decline"))
                self.workload = min(1.0, self.workload + 0.08)
            elif message.speaker == "robot" and message.kind == "acknowledge":
                self.trust = min(1.0, self.trust + 0.015)
        self.seen_messages = len(observation.messages)
        return outgoing

    def _goal_candidates(self, observation: Observation) -> list[tuple[float, str, str]]:
        candidates = []
        for object_id, destination in self.commitments.items():
            if object_id in observation.held_by_human:
                continue
            object_position = np.asarray(observation.objects[object_id])
            region_position = np.asarray(observation.regions[destination])
            if float(np.linalg.norm(object_position - region_position)) <= 0.065:
                continue
            distance = float(np.linalg.norm(object_position[:2] - observation.human_position[:2]))
            remaining = float(np.linalg.norm(object_position[:2] - region_position[:2]))
            robot_distance = float(np.linalg.norm(object_position[:2] - observation.robot_ee[:2]))
            conflict = 0.65 if observation.active_robot_action == f"transfer:{object_id}" else 0.0
            score = 1.4 * remaining + 0.55 * distance + 0.25 * self.workload - conflict
            candidates.append((score, object_id, destination))
        return sorted(candidates)

    def step(self, observation: Observation) -> PartnerOutput:
        messages = self._process_messages(observation)
        if self.left_until > 0:
            self.left_until -= 1
            return PartnerOutput(HumanCommand("away", target=(0.50, 0.90, 0.0)), tuple(messages))
        if observation.active_robot_action.startswith("transfer:"):
            target_object = observation.active_robot_action.split(":", 1)[1]
            if target_object in self.commitments and target_object not in observation.held_by_human:
                self.trust = max(0.0, self.trust - 0.001)
                return PartnerOutput(HumanCommand("yield", target=(0.50, 0.78, 0.0)), tuple(messages))
        if observation.held_by_human:
            held_object = observation.held_by_human[0]
            destination = self.commitments.get(held_object, self.current_destination)
            if destination in observation.regions:
                region = observation.regions[destination]
                return PartnerOutput(HumanCommand("carry", held_object, destination,
                                                  (float(region[0]), float(region[1]), 0.0)), tuple(messages))
        candidates = self._goal_candidates(observation)
        if not candidates:
            self.workload = max(0.0, self.workload - 0.01)
            return PartnerOutput(HumanCommand("observe", target=observation.human_position), tuple(messages))
        _, object_id, destination = candidates[0]
        self.current_object = object_id
        self.current_destination = destination
        object_position = np.asarray(observation.objects[object_id])
        region_position = np.asarray(observation.regions[destination])
        trigger = self.scenario.leave_trigger
        if (trigger and trigger in observation.completed_skills and not self.has_left
                and self.scenario.leave_probability > 0.0):
            leave_score = self.scenario.leave_probability * self.trust
            should_leave = bool(self.rng.random() < leave_score) if self.stochastic else leave_score >= 0.5
            if should_leave:
                self.has_left = True
                self.left_until = self.scenario.leave_duration_steps
                messages.append(Message("human", "temporarily_away", "我暂时离开一下，稍后回来继续。"))
                return PartnerOutput(HumanCommand("away", target=(0.50, 0.90, 0.0)), tuple(messages))
        target_position = region_position if object_id in observation.held_by_human else object_position
        target = (float(target_position[0]), float(target_position[1]), 0.0)
        intent = "carry" if object_id in observation.held_by_human else "approach"
        return PartnerOutput(HumanCommand(intent, object_id, destination, target), tuple(messages))


class FixedReplayPartner:
    """不读取机器人行为的固定回放对照。

    它只按初始的人类分工依次完成贡献，仍然使用连续几何推进，因而可作为
    与反应式伙伴长度匹配的控制条件。它不会根据求助、占用、延迟或历史
    重新分配贡献。
    """

    def __init__(self, scenario: ContinuousScenario):
        self.scenario = scenario
        self.reset(0)

    def reset(self, seed: int) -> None:
        self.order = list(self.scenario.human_targets.items())
        self.index = 0

    def initial_messages(self) -> tuple[Message, ...]:
        return self.scenario.initial_messages()

    def step(self, observation: Observation) -> PartnerOutput:
        while self.index < len(self.order):
            object_id, destination = self.order[self.index]
            if f"human:{object_id}:{destination}" in observation.completed_skills:
                self.index += 1
            else:
                break
        if self.index >= len(self.order):
            return PartnerOutput(HumanCommand("observe", target=observation.human_position))
        object_id, destination = self.order[self.index]
        if object_id in observation.held_by_human:
            target = observation.regions[destination]
            return PartnerOutput(HumanCommand("carry", object_id, destination,
                                              (float(target[0]), float(target[1]), 0.0)))
        target = observation.objects[object_id]
        return PartnerOutput(HumanCommand("approach", object_id, destination,
                                          (float(target[0]), float(target[1]), 0.0)))


class ReactivePartner(FixedReplayPartner):
    """只依据当前公开行为反应的伙伴，不保留信任和长期负载状态。"""

    def reset(self, seed: int) -> None:
        super().reset(seed)
        self.seen_messages = 0
        self.commitments = dict(self.scenario.human_targets)
        self.accepted_requests: dict[str, str] = {}

    def _messages(self, observation: Observation) -> list[Message]:
        outgoing: list[Message] = []
        for message in observation.messages[self.seen_messages:]:
            if message.speaker == "robot" and message.kind == "request_help" and message.object_id:
                accepted = self.scenario.human_availability >= 0.5 and not observation.held_by_human
                if accepted:
                    destination = message.destination or f"tray_{message.object_id}"
                    self.accepted_requests[message.object_id] = destination
                    self.commitments[message.object_id] = destination
                    outgoing.append(Message("human", "help_reply", "我可以接手这个贡献。",
                                             message.object_id, "accept", destination))
                else:
                    outgoing.append(Message("human", "help_reply", "我现在无法接手。",
                                             message.object_id, "decline"))
        self.seen_messages = len(observation.messages)
        return outgoing

    def step(self, observation: Observation) -> PartnerOutput:
        messages = self._messages(observation)
        if observation.active_robot_action.startswith("transfer:"):
            object_id = observation.active_robot_action.split(":", 1)[1]
            if object_id in self.commitments and object_id not in observation.held_by_human:
                return PartnerOutput(HumanCommand("yield", target=(0.50, 0.78, 0.0)), tuple(messages))
        for object_id, destination in self.accepted_requests.items():
            if f"human:{object_id}:{destination}" not in observation.completed_skills:
                if object_id in observation.held_by_human:
                    target = observation.regions[destination]
                    return PartnerOutput(HumanCommand("carry", object_id, destination,
                                                      (float(target[0]), float(target[1]), 0.0)), tuple(messages))
                target = observation.objects[object_id]
                return PartnerOutput(HumanCommand("approach", object_id, destination,
                                                  (float(target[0]), float(target[1]), 0.0)), tuple(messages))
        output = super().step(observation)
        return PartnerOutput(output.command, tuple(messages) + output.messages)


def make_partner(scenario: ContinuousScenario, mode: str = "adaptive") -> ContinuousPartner:
    """按实验条件构造伙伴；模式只改变伙伴信息使用边界。"""
    if mode == "fixed_replay":
        return FixedReplayPartner(scenario)
    if mode == "reactive":
        return ReactivePartner(scenario)
    if mode == "adaptive":
        return AdaptivePartner(scenario)
    raise ValueError(f"未知伙伴模式: {mode}")


@dataclass
class _RobotExecution:
    action: Action
    phase: str = "approach"
    object_id: str | None = None
    destination: str | None = None
    progress: float = 0.0


class ContinuousWorld:
    """轻量可审计参考后端，模拟同一时间轴中的两方动作。

    它用于协议和场景的正式机制验证；Genesis 适配器可复用相同事件和
    action-chunk 记录，并把这里的几何推进替换成真实关节积分。
    """

    def __init__(self, scenario: ContinuousScenario, *, dt: float | None = None):
        self.scenario = scenario
        self.dt = dt or 1.0 / scenario.tick_hz
        self.reset(0)

    def reset(self, seed: int) -> None:
        self.rng = np.random.default_rng(seed)
        jitter = self.rng.uniform(-0.012, 0.012, 2)
        self.objects = {spec.name: np.asarray(spec.position, dtype=float).copy() for spec in self.scenario.objects}
        for position in self.objects.values():
            position[:2] += jitter
        self.regions = {key: np.asarray(value, dtype=float).copy() for key, value in self.scenario.regions.items()}
        self.robot_pos = np.array((-0.04, 0.0, 1.05), dtype=float)
        self.human_pos = np.array((0.50, 0.90, 0.0), dtype=float)
        self.robot_qpos = np.zeros(9, dtype=float)
        self.robot_execution: _RobotExecution | None = None
        self.human_command = HumanCommand("observe", target=tuple(self.human_pos))
        self.human_hold: str | None = None
        self.robot_hold: str | None = None
        self.messages: list[Message] = []
        self.events: list[dict[str, Any]] = []
        self.completed_skills: list[str] = []
        self.step_count = 0
        self.robot_action_count = 0
        self.interruptions = 0
        self.near_misses = 0

    @property
    def time_s(self) -> float:
        return self.step_count * self.dt

    def say(self, message: Message) -> None:
        self.messages.append(message)
        self.events.append({"step": self.step_count, "kind": "public_message", "speaker": message.speaker,
                            "message_kind": message.kind, "object_id": message.object_id, "value": message.value,
                            "text": message.text})

    def held_by_human(self) -> tuple[str, ...]:
        return (self.human_hold,) if self.human_hold else ()

    def observe(self, rgb: Any = None) -> Observation:
        execution = self.robot_execution
        active = "idle" if execution is None else (
            f"transfer:{execution.object_id}" if execution.action.kind == "transfer" and execution.object_id
            else execution.action.kind)
        phase = "idle" if execution is None else execution.phase
        visible_action = self.human_command.intent
        return Observation(
            objects={name: tuple(position.tolist()) for name, position in self.objects.items()},
            regions={name: tuple(position.tolist()) for name, position in self.regions.items()},
            messages=tuple(self.messages), robot_ee=tuple(self.robot_pos.tolist()),
            human_position=tuple(self.human_pos.tolist()), held_by_human=self.held_by_human(),
            completed_skills=tuple(self.completed_skills), robot_qpos=tuple(self.robot_qpos.tolist()), rgb=rgb,
            time_s=self.time_s, active_robot_action=active, action_phase=phase,
            visible_human_action=visible_action,
        )

    def apply_human_command(self, command: HumanCommand) -> None:
        self.human_command = command

    def start_action(self, action: Action) -> None:
        if self.robot_execution is not None:
            self.interruptions += 1
            self.events.append({"step": self.step_count, "kind": "robot_action_preempted",
                                "previous": self.robot_execution.action.kind, "next": action.kind})
        if action.kind == "request_help":
            self.say(Message("robot", "request_help", action.text, action.object_id, action.destination))
            self.robot_execution = _RobotExecution(action, phase="communicate", progress=0.0)
        elif action.kind == "acknowledge":
            self.say(Message("robot", "acknowledge", action.text, action.object_id))
            self.robot_execution = _RobotExecution(action, phase="communicate", progress=0.0)
        elif action.kind == "transfer":
            if action.object_id not in self.objects or action.destination not in self.regions:
                raise ValueError(f"连续场景中的动作目标不存在: {action}")
            self.robot_execution = _RobotExecution(action, phase="approach", object_id=action.object_id,
                                                    destination=action.destination, progress=0.0)
        elif action.kind in {"wait", "joint_position", "finish"}:
            self.robot_execution = _RobotExecution(action, phase="execute", progress=0.0)
        else:
            raise ValueError(f"未知连续动作: {action.kind}")
        self.robot_action_count += 1
        self.events.append({"step": self.step_count, "kind": "policy_action", "action": action.kind,
                            "object_id": action.object_id, "destination": action.destination,
                            "duration_steps": action.duration_steps})

    def _move(self, current: np.ndarray, target: np.ndarray, speed: float) -> bool:
        delta = target - current
        distance = float(np.linalg.norm(delta))
        if distance <= speed:
            current[:] = target
            return True
        current[:] += delta / distance * speed
        return False

    def _step_robot(self) -> None:
        execution = self.robot_execution
        if execution is None:
            return
        action = execution.action
        if action.kind == "transfer":
            source = self.objects[execution.object_id]
            destination = self.regions[execution.destination]
            if execution.phase == "approach":
                if self._move(self.robot_pos, source + np.array((0.0, 0.0, 0.12)), 0.075):
                    execution.phase = "grasp"
            elif execution.phase == "grasp":
                self.robot_pos[:] = source + np.array((0.0, 0.0, 0.07))
                self.robot_hold = execution.object_id
                execution.phase = "carry"
                self.events.append({"step": self.step_count, "kind": "robot_grasped",
                                    "object_id": execution.object_id})
            elif execution.phase == "carry":
                if self._move(self.robot_pos, destination + np.array((0.0, 0.0, 0.10)), 0.085):
                    execution.phase = "release"
                if self.robot_hold:
                    self.objects[self.robot_hold][:] = self.robot_pos - np.array((0.0, 0.0, 0.07))
            elif execution.phase == "release":
                self.objects[execution.object_id][:] = destination
                self.robot_hold = None
                self.completed_skills.append(f"robot:{execution.object_id}:{execution.destination}")
                self.events.append({"step": self.step_count, "kind": "robot_transfer_completed",
                                    "object_id": execution.object_id, "destination": execution.destination})
                self.robot_execution = None
        elif action.kind == "joint_position":
            target = np.asarray(action.joints, dtype=float)
            if target.shape == (9,):
                alpha = min(1.0, self.dt * 4.0)
                self.robot_qpos[:] = (1.0 - alpha) * self.robot_qpos + alpha * target
            execution.progress += 1.0
            if execution.progress >= max(1, action.duration_steps):
                self.robot_execution = None
        else:
            execution.progress += 1.0
            if execution.progress >= max(1, action.duration_steps):
                self.robot_execution = None

    def _step_human(self) -> None:
        command = self.human_command
        target = np.asarray(command.target if command.target is not None else self.human_pos, dtype=float).copy()
        target[2] = 0.0
        self._move(self.human_pos, target, 0.055 if command.intent != "away" else 0.075)
        if command.object_id is None or command.object_id not in self.objects:
            return
        object_position = self.objects[command.object_id]
        if self.human_hold is None and command.intent == "approach" and np.linalg.norm(object_position[:2] - self.human_pos[:2]) < 0.07:
            self.human_hold = command.object_id
            self.events.append({"step": self.step_count, "kind": "human_grasped", "object_id": command.object_id})
        if self.human_hold == command.object_id:
            object_position[:] = self.human_pos + np.array((0.0, 0.0, 0.78))
            if command.destination and np.linalg.norm(self.regions[command.destination][:2] - self.human_pos[:2]) < 0.08:
                object_position[:] = self.regions[command.destination]
                self.completed_skills.append(f"human:{command.object_id}:{command.destination}")
                self.events.append({"step": self.step_count, "kind": "human_transfer_completed",
                                    "object_id": command.object_id, "destination": command.destination})
                self.human_hold = None

    def tick(self) -> None:
        self._step_robot()
        self._step_human()
        if np.linalg.norm(self.robot_pos[:2] - self.human_pos[:2]) < 0.13:
            self.near_misses += 1
            self.events.append({"step": self.step_count, "kind": "proximity_warning",
                                "distance_m": float(np.linalg.norm(self.robot_pos[:2] - self.human_pos[:2]))})
        self.step_count += 1

    def finished_robot(self) -> bool:
        return all(np.linalg.norm(self.objects[name] - self.regions[destination]) < 0.065
                   for name, destination in self.scenario.robot_targets.items())

    def finished_human(self) -> bool:
        return all(np.linalg.norm(self.objects[name] - self.regions[destination]) < 0.065
                   for name, destination in self.scenario.human_targets.items())


def load_continuous_policy(spec: str):
    if spec == "greedy_public":
        return GreedyPublicPolicy()
    module, factory = spec.split(":", 1)
    return getattr(importlib.import_module(module), factory)()


class GreedyPublicPolicy:
    """只使用公开 assignment、像素/几何和当前动作状态的参考策略。"""

    def reset(self) -> None:
        self.assignments: dict[str, tuple[str, str]] = {}
        self.seen_messages = 0
        self.requested: set[str] = set()

    def act(self, observation: Observation) -> Action:
        for message in observation.messages[self.seen_messages:]:
            if message.kind == "assignment" and message.object_id:
                self.assignments[message.object_id] = (message.value or "robot",
                                                       message.destination or f"tray_{message.object_id}")
            if message.kind == "help_reply" and message.object_id and message.value == "decline":
                self.assignments[message.object_id] = ("robot", f"tray_{message.object_id}")
        self.seen_messages = len(observation.messages)
        candidates = []
        for object_id, (assignment, destination) in self.assignments.items():
            if assignment == "robot":
                if destination in observation.regions and math.dist(observation.objects[object_id], observation.regions[destination]) > 0.065:
                    candidates.append((math.dist(observation.robot_ee, observation.objects[object_id]), object_id, destination))
        if candidates:
            _, object_id, destination = min(candidates)
            return Action("transfer", object_id, destination, duration_steps=1)
        if observation.active_robot_action == "idle":
            return Action("wait", duration_steps=2)
        return Action("wait", duration_steps=2)


class ContinuousBackend(Protocol):
    """真实或参考后端都必须提供的逐 tick 接口。"""

    def reset(self, seed: int) -> None: ...
    def observe(self) -> Observation: ...
    def say(self, message: Message) -> None: ...
    def apply_human_command(self, command: HumanCommand) -> None: ...
    def start_action(self, action: Action) -> None: ...
    def tick(self) -> None: ...
    def finished_robot(self) -> bool: ...
    def finished_human(self) -> bool: ...


def run_continuous_episode(scenario: ContinuousScenario, policy, partner: ContinuousPartner,
                           *, seed: int = 0, output: Path | None = None,
                           decision_interval: int = 3,
                           backend_factory=ContinuousWorld,
                           partner_mode: str | None = None) -> dict[str, Any]:
    """在任意连续 backend 上运行一个 episode。

    `backend_factory` 只需要实现 `ContinuousBackend`。因此真实 Genesis、
    Isaac 或远程机器人环境可以复用同一场景、伙伴、策略和评测器，而不必
    把 benchmark 逻辑复制到某个仿真器内部。
    """
    world: ContinuousBackend = backend_factory(scenario)
    world.reset(seed)
    policy.reset()
    partner.reset(seed)
    for message in partner.initial_messages():
        world.say(message)
    trace: list[dict[str, Any]] = []
    policy_seen_messages = 0
    policy_io: list[dict[str, Any]] = []
    public_observations: list[dict[str, Any]] = []

    def observation_record(observation: Observation) -> dict[str, Any]:
        record = serialize(observation)
        artifact = getattr(world, "last_observation_path", None)
        if artifact is not None:
            record["rgb_artifact"] = str(artifact)
        return record

    for _ in range(scenario.max_steps):
        observation = world.observe()
        partner_output = partner.step(observation)
        for message in partner_output.messages:
            world.say(message)
        world.apply_human_command(partner_output.command)
        public_observation = world.observe()
        new_public_messages = public_observation.messages[policy_seen_messages:]
        public_reaction = any(message.kind in {"help_reply", "temporarily_away", "correction"}
                              for message in new_public_messages)
        can_decide = public_observation.active_robot_action == "idle" or public_reaction
        if can_decide:
            action = policy.act(public_observation)
            policy_seen_messages = len(public_observation.messages)
            policy_io.append({"step": public_observation.time_s,
                              "observation": observation_record(public_observation),
                              "action": serialize(action)})
            world.start_action(action)
            if action.kind == "finish":
                break
        public_observations.append(observation_record(public_observation))
        trace.append({"step": len(trace), "time_s": public_observation.time_s,
                      "objects": public_observation.objects,
                      "human_position": public_observation.human_position,
                      "robot_position": public_observation.robot_ee,
                      "active_robot_action": public_observation.active_robot_action,
                      "human_action": public_observation.visible_human_action})
        world.tick()
        if world.finished_robot() and world.finished_human():
            break
    robot_success = world.finished_robot()
    human_success = world.finished_human()
    events = list(getattr(world, "events", ()))
    completed_skills = list(getattr(world, "completed_skills", ()))
    mode = partner_mode or {
        "FixedReplayPartner": "fixed_replay",
        "ReactivePartner": "reactive",
        "AdaptivePartner": "adaptive",
    }.get(type(partner).__name__, type(partner).__name__)
    requests = [event for event in events if event.get("kind") == "public_message"
                and event.get("speaker") == "robot" and event.get("message_kind") == "request_help"]
    replies = [event for event in events if event.get("kind") == "public_message"
               and event.get("speaker") == "human" and event.get("message_kind") == "help_reply"]
    response_latencies = []
    for request in requests:
        matching = [reply for reply in replies if reply["step"] >= request["step"]
                    and (request.get("object_id") is None or reply.get("object_id") == request.get("object_id"))]
        if matching:
            response_latencies.append(matching[0]["step"] - request["step"])
    human_actions = [row["human_action"] for row in trace]
    adaptation_events = sum(event.get("kind") in {
        "robot_action_preempted", "proximity_warning"} for event in events)
    result = {
        "scenario": scenario.name, "seed": seed, "robot_success": robot_success,
        "human_success": human_success, "task_success": bool(robot_success and human_success),
        "condition": scenario.condition, "structure_family": scenario.structure.family,
        "structure_split": scenario.structure.split, "partner_mode": mode,
        "steps": len(trace), "robot_actions": int(getattr(world, "robot_action_count", len(policy_io))),
        "preemptions": int(getattr(world, "interruptions", 0)),
        "proximity_warnings": int(getattr(world, "near_misses", 0)),
        "public_messages": len(getattr(world, "messages", ())),
        "action_chunks": len(policy_io),
        "completion_time_s": trace[-1]["time_s"] if trace else 0.0,
        "completed_skills": completed_skills, "events": len(events),
        "response_latency_steps": (sum(response_latencies) / len(response_latencies)
                                    if response_latencies else None),
        "human_corrections": sum(event.get("message_kind") == "correction" for event in events),
        "human_yield_steps": human_actions.count("yield"),
        "human_idle_ratio": (human_actions.count("observe") / len(human_actions)
                              if human_actions else 0.0),
        "adaptation_events": adaptation_events,
        "coordination_cost": float(len(policy_io) + 2 * len(response_latencies)
                                    + 3 * result_preemptions(events)),
    }
    if output is not None:
        output.mkdir(parents=True, exist_ok=True)
        (output / "scenario.json").write_text(
            json.dumps({"name": scenario.name, "description": scenario.description,
                        "objects": [spec.__dict__ for spec in scenario.objects],
                        "regions": scenario.regions, "robot_targets": scenario.robot_targets,
                        "human_targets": scenario.human_targets,
                        "human_availability": scenario.human_availability,
                        "max_steps": scenario.max_steps, "tick_hz": scenario.tick_hz,
                        "leave_trigger": scenario.leave_trigger,
                        "leave_probability": scenario.leave_probability,
                        "leave_duration_steps": scenario.leave_duration_steps,
                        "condition": scenario.condition,
                        "structure": {"family": scenario.structure.family,
                                      "segments": scenario.structure.segments,
                                      "dependencies": scenario.structure.dependencies,
                                      "concurrency": scenario.structure.concurrency,
                                      "split": scenario.structure.split}},
                       ensure_ascii=False, indent=2))
        (output / "trace.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in trace) + "\n")
        (output / "public_observations.jsonl").write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in public_observations) + "\n")
        (output / "policy_io.jsonl").write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in policy_io) + "\n")
        (output / "events.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n")
        (output / "metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def result_preemptions(events: list[dict[str, Any]]) -> int:
    return sum(event.get("kind") == "robot_action_preempted" for event in events)


def run_catalog(*, policy_spec: str = "greedy_public", seed: int = 0,
                output: Path | None = None, scenarios: list[ContinuousScenario] | None = None,
                backend_factory=ContinuousWorld, partner_mode: str = "adaptive") -> list[dict[str, Any]]:
    policy = load_continuous_policy(policy_spec)
    results = []
    scenario_list = scenarios or list(CONTINUOUS_SCENARIOS.values())
    for scenario in scenario_list:
        episode_output = output / scenario.name if output else None
        results.append(run_continuous_episode(scenario, policy, make_partner(scenario, partner_mode), seed=seed,
                                              output=episode_output, backend_factory=backend_factory,
                                              partner_mode=partner_mode))
    if output:
        output.mkdir(parents=True, exist_ok=True)
        (output / "summary.json").write_text(json.dumps({"episodes": results,
                                                          "scope": "continuous_benchmark_runtime",
                                                          "scenario_count": len(scenario_list)},
                                                         ensure_ascii=False, indent=2))
    return results
