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
class WorkItem:
    """活动中的一个可交接工作项。

    工作项只描述成功条件和公开协作边界，不描述某一步必须发生什么。
    ``prerequisites`` 是已经公开完成的 skill id；满足条件后，任一被允许
    的伙伴都可以通过真实动作完成该工作项。
    """

    item_id: str
    object_id: str
    destination: str
    preferred_role: str
    prerequisites: tuple[str, ...] = ()
    handoff: str = "open"
    priority: float = 1.0


@dataclass(frozen=True)
class InteractionAct:
    """活动中的一个可组合交互作用标注。

    交互作用只描述数据集中的可观察贡献和跨作用依赖，不规定某个
    时间点必须发生什么。运行时仍由双方根据公开观测选择动作。
    """

    act_id: str
    kind: str
    actor: str = "shared"
    target: str | None = None
    requires: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActivityContract:
    """描述持续共同活动的目标、依赖和可重规划边界。

    这是场景生成契约，不是状态机。运行时只在动作完成时检查依赖，
    人和机器人仍然根据当前公开观测决定是否执行、让行或接管。
    """

    objective: str
    work_items: tuple[WorkItem, ...]
    interaction_acts: tuple[InteractionAct, ...] = ()
    shared_resources: tuple[str, ...] = ()
    replanning_triggers: tuple[str, ...] = (
        "action_failed", "action_delayed", "help_request", "partner_returned",
    )
    success_policy: str = "all_work_items"

    def __post_init__(self) -> None:
        item_ids = [item.item_id for item in self.work_items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("ActivityContract 的 item_id 必须唯一")
        act_ids = [act.act_id for act in self.interaction_acts]
        if len(act_ids) != len(set(act_ids)):
            raise ValueError("ActivityContract 的 act_id 必须唯一")
        unknown_acts = {required for act in self.interaction_acts for required in act.requires} - set(act_ids)
        if unknown_acts:
            raise ValueError(f"交互作用引用了未知前置作用: {sorted(unknown_acts)}")
        known = set(item_ids) | {
            f"{role}:{item.object_id}:{item.destination}"
            for item in self.work_items
            for role in ("human", "robot")
        }
        for item in self.work_items:
            unknown = set(item.prerequisites) - known
            if unknown:
                raise ValueError(f"工作项 {item.item_id} 引用了未知前置条件: {sorted(unknown)}")


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
class DynamicsSpec:
    """场景的潜在动力学与伙伴适应参数。

    参数描述概率、阈值和可观察的恢复规则，不描述某个固定时间点要发生的
    事件。具体结果在动作开始、公开消息到达和当前几何状态下在线采样。
    """

    robot_delay_probability: float = 0.0
    robot_failure_probability: float = 0.0
    max_delay_steps: int = 0
    human_replan_sensitivity: float = 0.65
    leave_pressure: float = 0.0
    return_on_robot_idle: bool = True
    human_initiative: float = 0.65
    handoff_on_failure_probability: float = 1.0
    robot_failure_budget: int = 0


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
    dynamics: DynamicsSpec = field(default_factory=DynamicsSpec)
    structure: InteractionStructure = field(
        default_factory=lambda: InteractionStructure("isolated", ("joint_execution",)))
    condition: str = "compositional"
    activity: ActivityContract | None = None
    # Public task metadata and backend asset references.  Asset paths are
    # resolved by the selected backend; the reference backend only needs the
    # geometry above.
    task_family: str = "object_transport"
    assets: dict[str, Any] = field(default_factory=dict)

    def resolved_activity(self) -> ActivityContract:
        if self.activity is not None:
            return self.activity
        return make_activity_contract(self.human_targets, self.robot_targets,
                                      self.structure.family, self.description)

    def initial_messages(self) -> tuple[Message, ...]:
        messages = []
        activity = self.resolved_activity()
        for item in activity.work_items:
            if item.preferred_role == "human":
                text = f"我先处理 {item.object_id}，目标是 {item.destination}。"
            else:
                text = f"请你处理 {item.object_id}，目标是 {item.destination}。"
            if item.prerequisites:
                text += f" 前置贡献完成后再接手（{', '.join(item.prerequisites)}）。"
            messages.append(Message("human", "assignment", text, item.object_id,
                                    item.preferred_role, item.destination))
        return tuple(messages)


def _scene(name: str, description: str, human: dict[str, str], robot: dict[str, str],
           availability: float = 0.75, max_steps: int = 260, *,
           leave_trigger: str | None = None, leave_probability: float = 0.0,
           leave_duration_steps: int = 12,
           dynamics: DynamicsSpec | None = None,
           structure: InteractionStructure | None = None,
           condition: str = "compositional",
           activity: ActivityContract | None = None,
           task_family: str = "object_transport",
           assets: dict[str, Any] | None = None) -> ContinuousScenario:
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
        dynamics=dynamics or DynamicsSpec(),
        structure=structure or InteractionStructure("isolated", ("joint_execution",)),
        condition=condition,
        activity=activity,
        task_family=task_family,
        assets=assets or {},
    )


def make_activity_contract(human_targets: dict[str, str], robot_targets: dict[str, str],
                           family: str, objective: str) -> ActivityContract:
    """从角色分工和结构关系生成可执行的活动契约。

    依赖是声明式的：它们约束哪些贡献已经可以被接受，但不指定完成时间、
    伙伴动作或中间事件。因此同一契约可以由不同模型、不同伙伴和不同物理
    后端执行，适合生成 matched、compositional 和 held-out 数据。
    """
    human_items = [WorkItem(f"human:{object_id}:{destination}", object_id, destination,
                            "human", priority=1.0)
                   for object_id, destination in human_targets.items()]
    robot_items = [WorkItem(f"robot:{object_id}:{destination}", object_id, destination,
                            "robot", priority=1.0)
                   for object_id, destination in robot_targets.items()]
    if family in {"matched_serial", "nested", "reinterpretation", "robot_initiated_rebalance",
                  "leave_return", "held_out_reinterpretation"} and human_items and robot_items:
        anchor = human_items[-1].item_id
        robot_items = [replace(item, prerequisites=(anchor,)) for item in robot_items]
    if family in {"reinterpretation", "held_out_reinterpretation"} and len(robot_items) > 1:
        robot_items = [robot_items[0]] + [replace(item, prerequisites=(robot_items[0].item_id,))
                                          for item in robot_items[1:]]
    items = tuple(human_items + robot_items)
    acts: list[InteractionAct] = []
    if human_items:
        acts.append(InteractionAct("guidance", "guidance", "human",
                                   target=human_items[0].item_id))
    for item in items:
        kind = "joint_execution" if item.preferred_role == "robot" else "intervention"
        requires = ("guidance",) if item.preferred_role == "robot" and human_items else ()
        acts.append(InteractionAct(f"act:{item.item_id}", kind, item.preferred_role,
                                   target=item.item_id, requires=requires))
    if family in {"nested", "reinterpretation", "held_out_reinterpretation"} and robot_items:
        acts.append(InteractionAct("replan", "guidance", "shared",
                                   target=robot_items[0].item_id,
                                   requires=(f"act:{robot_items[0].item_id}",)))
    return ActivityContract(
        objective=objective,
        work_items=items,
        interaction_acts=tuple(acts),
        shared_resources=("shared_workspace", "public_commitment_channel"),
    )


def scenario_to_dict(scenario: ContinuousScenario) -> dict[str, Any]:
    """把场景契约写成可版本控制的 JSON 对象。"""
    activity = scenario.resolved_activity()
    return {
        "name": scenario.name,
        "description": scenario.description,
        "objects": [spec.__dict__ for spec in scenario.objects],
        "regions": scenario.regions,
        "robot_targets": scenario.robot_targets,
        "human_targets": scenario.human_targets,
        "human_availability": scenario.human_availability,
        "max_steps": scenario.max_steps,
        "tick_hz": scenario.tick_hz,
        "leave_trigger": scenario.leave_trigger,
        "leave_probability": scenario.leave_probability,
        "leave_duration_steps": scenario.leave_duration_steps,
        "dynamics": {
            "robot_delay_probability": scenario.dynamics.robot_delay_probability,
            "robot_failure_probability": scenario.dynamics.robot_failure_probability,
            "max_delay_steps": scenario.dynamics.max_delay_steps,
            "human_replan_sensitivity": scenario.dynamics.human_replan_sensitivity,
            "leave_pressure": scenario.dynamics.leave_pressure,
            "return_on_robot_idle": scenario.dynamics.return_on_robot_idle,
            "human_initiative": scenario.dynamics.human_initiative,
            "handoff_on_failure_probability": scenario.dynamics.handoff_on_failure_probability,
            "robot_failure_budget": scenario.dynamics.robot_failure_budget,
        },
        "activity": {
            "objective": activity.objective,
            "work_items": [item.__dict__ for item in activity.work_items],
            "interaction_acts": [act.__dict__ for act in activity.interaction_acts],
            "shared_resources": activity.shared_resources,
            "replanning_triggers": activity.replanning_triggers,
            "success_policy": activity.success_policy,
        },
        "condition": scenario.condition,
        "task_family": scenario.task_family,
        "assets": scenario.assets,
        "structure": {
            "family": scenario.structure.family,
            "segments": scenario.structure.segments,
            "dependencies": scenario.structure.dependencies,
            "concurrency": scenario.structure.concurrency,
            "split": scenario.structure.split,
        },
    }


def scenario_from_dict(data: dict[str, Any]) -> ContinuousScenario:
    """从 JSON 场景契约构造运行时实例。

    该入口让新任务通过数据定义即可加入 benchmark；未知字段被忽略，便于
    在数据集文件中保存额外的资产或标注信息。
    """
    objects = tuple(ObjectSpec(spec["name"], tuple(spec["position"]), float(spec.get("radius", 0.045)))
                    for spec in data.get("objects", ()))
    structure_data = data.get("structure", {})
    structure = InteractionStructure(
        structure_data.get("family", "isolated"),
        tuple(structure_data.get("segments", ("joint_execution",))),
        tuple(tuple(pair) for pair in structure_data.get("dependencies", ())),
        tuple(tuple(pair) for pair in structure_data.get("concurrency", ())),
        structure_data.get("split", "dev"),
    )
    dynamics_data = data.get("dynamics", {})
    dynamics_fields = {
        "robot_delay_probability", "robot_failure_probability", "max_delay_steps",
        "human_replan_sensitivity", "leave_pressure", "return_on_robot_idle",
        "human_initiative", "handoff_on_failure_probability", "robot_failure_budget",
    }
    dynamics = DynamicsSpec(**{key: dynamics_data[key] for key in dynamics_fields
                               if key in dynamics_data})
    activity_data = data.get("activity")
    activity = None
    if activity_data:
        activity = ActivityContract(
            objective=activity_data.get("objective", data.get("description", "持续共同活动")),
            work_items=tuple(WorkItem(
                item_id=item["item_id"], object_id=item["object_id"],
                destination=item["destination"], preferred_role=item.get("preferred_role", "robot"),
                prerequisites=tuple(item.get("prerequisites", ())),
                handoff=item.get("handoff", "open"), priority=float(item.get("priority", 1.0)),
            ) for item in activity_data.get("work_items", ())),
            interaction_acts=tuple(InteractionAct(
                act_id=act["act_id"], kind=act["kind"], actor=act.get("actor", "shared"),
                target=act.get("target"), requires=tuple(act.get("requires", ())),
            ) for act in activity_data.get("interaction_acts", ())),
            shared_resources=tuple(activity_data.get("shared_resources", ())),
            replanning_triggers=tuple(activity_data.get("replanning_triggers", (
                "action_failed", "action_delayed", "help_request", "partner_returned"))),
            success_policy=activity_data.get("success_policy", "all_work_items"),
        )
    return ContinuousScenario(
        name=data["name"], description=data.get("description", "持续共同活动"),
        objects=objects, regions={key: tuple(value) for key, value in data.get("regions", {}).items()},
        robot_targets=dict(data.get("robot_targets", {})), human_targets=dict(data.get("human_targets", {})),
        human_availability=float(data.get("human_availability", 0.75)),
        max_steps=int(data.get("max_steps", 260)), tick_hz=float(data.get("tick_hz", 10.0)),
        leave_trigger=data.get("leave_trigger"), leave_probability=float(data.get("leave_probability", 0.0)),
        leave_duration_steps=int(data.get("leave_duration_steps", 12)), dynamics=dynamics,
        structure=structure, condition=data.get("condition", "compositional"), activity=activity,
        task_family=data.get("task_family", "object_transport"),
        assets=dict(data.get("assets", {})),
    )


def load_scenario(path: str | Path) -> ContinuousScenario:
    """从单个 JSON 文件读取用户定义场景。"""
    source = Path(path)
    scenario = scenario_from_dict(json.loads(source.read_text(encoding="utf-8")))
    if not scenario.name or scenario.name in {".", ".."} or Path(scenario.name).name != scenario.name:
        raise ValueError("场景 name 必须是非空且不包含路径分隔符的目录名")
    return scenario


def load_scenario_catalog(path: str | Path) -> list[ContinuousScenario]:
    """加载一个场景文件或目录中的 JSON 场景契约。

    场景目录是 benchmark 作者扩展任务的入口：只需提供对象、区域、
    ActivityContract 和结构划分，运行器不会要求为每个任务再写一份
    固定事件脚本。聚合文件和隐藏文件会被跳过，排序保证实例顺序稳定。
    """
    source = Path(path)
    if source.is_file():
        return [load_scenario(source)]
    if not source.is_dir():
        raise FileNotFoundError(f"场景文件或目录不存在：{source}")
    paths = sorted(candidate for candidate in source.glob("*.json")
                   if not candidate.name.startswith(("_", "dataset", "summary")))
    if not paths:
        raise ValueError(f"场景目录没有可加载的 JSON 文件：{source}")
    scenarios = [load_scenario(candidate) for candidate in paths]
    names = [scenario.name for scenario in scenarios]
    if len(names) != len(set(names)):
        raise ValueError("场景目录中的 name 必须唯一")
    return scenarios


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
                                        dynamics=DynamicsSpec(robot_delay_probability=0.35,
                                                              robot_failure_probability=0.08,
                                                              max_delay_steps=5,
                                                              human_replan_sensitivity=0.8,
                                                              robot_failure_budget=1),
                                        structure=InteractionStructure("reinterpretation",
                                                                        ("guidance", "intervention", "guidance"),
                                                                        (("guidance", "intervention"), ("intervention", "guidance")))),
    "robot_induced_rebalance": _scene("robot_induced_rebalance", "机器人出现延迟后，伙伴根据可见进度接手未完成贡献。",
                                       {"blue": "tray_blue"}, {"red": "tray_red", "green": "tray_green"},
                                       availability=0.9, max_steps=300,
                                       dynamics=DynamicsSpec(robot_delay_probability=0.45,
                                                             robot_failure_probability=0.18,
                                                             max_delay_steps=8,
                                                             human_replan_sensitivity=0.85,
                                                             robot_failure_budget=1),
                                       structure=InteractionStructure("robot_initiated_rebalance",
                                                                       ("joint_execution", "guidance", "joint_execution"),
                                                                       (("joint_execution", "guidance"),))),
    "leave_and_return": _scene("leave_and_return", "伙伴暂时离开工作区，返回后依据剩余工作恢复协作。",
                                {"red": "keep_red", "blue": "tray_blue"}, {"green": "tray_green"},
                                availability=0.55, max_steps=320,
                                leave_trigger="human:red:keep_red", leave_probability=1.0,
                                dynamics=DynamicsSpec(leave_pressure=0.9,
                                                      human_replan_sensitivity=0.8),
                                structure=InteractionStructure("leave_return",
                                                                ("joint_execution", "intervention", "joint_execution"),
                                                                (("joint_execution", "intervention"), ("intervention", "joint_execution")))),
}


TASK_FAMILY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "serial_relay": {"base": "relay", "split": "train", "capability": "公开承诺后的连续接力"},
    "concurrent_overlay": {"base": "concurrent_overlay", "split": "train", "capability": "并行占用与让行"},
    "nested_support": {"base": "nested_support", "split": "dev", "capability": "嵌套支持与局部介入"},
    "interruption_reprioritization": {"base": "history_reinterpretation", "split": "dev", "capability": "失败、打断和优先级重排"},
    "leave_and_return": {"base": "leave_and_return", "split": "dev", "capability": "离开、回归和恢复"},
    "robot_induced_rebalance": {"base": "robot_induced_rebalance", "split": "test", "capability": "机器人诱发的重新分工"},
    "history_reinterpretation": {"base": "history_reinterpretation", "split": "test", "capability": "保留历史并解释新信息"},
    "trait_dependent_open_task": {"base": "concurrent_overlay", "split": "test", "capability": "伙伴特征条件下的开放任务"},
    "held_out_task_composition": {"base": "robot_induced_rebalance", "split": "test", "capability": "未见任务族组合泛化"},
}


def make_extended_task_catalog(*, count_per_family: int = 1, seed: int = 0,
                               include_reference: bool = False) -> list[ContinuousScenario]:
    """生成可选的任务族目录，不改变 ``run_catalog`` 默认六场景。

    任务族通过活动契约、布局扰动和结构标签组合而成；它们不携带逐 tick
    事件脚本。相同任务族可以在不同伙伴 profile、机器人策略和物理后端上
    重复运行，便于做 unseen human/scene/task 的划分。
    """
    if count_per_family < 1:
        return list(CONTINUOUS_SCENARIOS.values()) if include_reference else []
    rng = np.random.default_rng(seed)
    scenarios: list[ContinuousScenario] = []
    for family, definition in TASK_FAMILY_DEFINITIONS.items():
        base = CONTINUOUS_SCENARIOS[definition["base"]]
        for index in range(count_per_family):
            jitter = rng.normal(0.0, 0.012, 2)
            objects = tuple(replace(spec, position=(spec.position[0] + float(jitter[0]),
                                                     spec.position[1] + float(jitter[1]),
                                                     spec.position[2])) for spec in base.objects)
            regions = {name: (value[0] + float(jitter[0]), value[1] + float(jitter[1]), value[2])
                       for name, value in base.regions.items()}
            structure = replace(base.structure, family=family, split=definition["split"])
            scenarios.append(replace(
                base,
                name=f"{family}_{index:03d}",
                description=f"{definition['capability']}：{base.description}",
                objects=objects,
                regions=regions,
                structure=structure,
                condition=family,
                task_family=family,
            ))
    if include_reference:
        scenarios.extend(CONTINUOUS_SCENARIOS.values())
    return scenarios


def make_history_counterfactual_scenario(name: str = "history_counterfactual") -> ContinuousScenario:
    """构造用于历史反事实门槛的最小任务实例。

    失败预算只在机器人实际启动 transfer 时消耗，因此“直接执行”和
    “先公开求助”会在同一初始场景中形成不同历史；它不指定失败发生的
    tick，也不规定伙伴随后必须采取哪一步。
    """
    base = CONTINUOUS_SCENARIOS["relay"]
    return replace(
        base,
        name=name,
        description="相同 relay 几何下比较直接执行与先公开求助的历史依赖。",
        max_steps=260,
        dynamics=replace(base.dynamics, robot_failure_budget=1),
    )


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
        dynamics = DynamicsSpec(
            robot_delay_probability=float(rng.uniform(0.0, 0.35)
                                         if structure.family in {"robot_initiated_rebalance", "held_out_reinterpretation"}
                                         else 0.0),
            robot_failure_probability=float(rng.uniform(0.0, 0.12)
                                           if structure.family in {"robot_initiated_rebalance", "held_out_reinterpretation"}
                                           else 0.0),
            max_delay_steps=int(rng.integers(2, 9)),
            human_replan_sensitivity=float(rng.uniform(0.55, 0.9)),
            leave_pressure=float(rng.uniform(0.2, 0.8) if human else 0.0),
        )
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
            dynamics=dynamics,
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
    speed_mps: float = 0.55
    acceleration_mps2: float = 2.0
    gaze_target: tuple[float, float, float] | None = None


@dataclass
class HumanAdaptiveState:
    """伙伴对当前共同活动的可变信念与可用性。

    这些变量不是模型输入，也不是预写状态机；它们由公开的机器人动作、
    结果、求助和共同空间占用在线更新，并作为 evaluator trace 输出。
    """

    trust: float = 0.70
    reliability_belief: float = 0.70
    workload: float = 0.0
    commitment_stability: float = 0.80
    initiative: float = 0.65
    robot_dependency: float = 0.25
    willingness_to_help: float = 0.70
    available: float = 0.75

    def clipped(self) -> "HumanAdaptiveState":
        for field_name in (
            "trust", "reliability_belief", "workload", "commitment_stability",
            "initiative", "robot_dependency", "willingness_to_help", "available",
        ):
            setattr(self, field_name, float(np.clip(getattr(self, field_name), 0.0, 1.0)))
        return self

    def snapshot(self) -> dict[str, float]:
        return {
            field_name: round(float(getattr(self, field_name)), 6)
            for field_name in (
                "trust", "reliability_belief", "workload", "commitment_stability",
                "initiative", "robot_dependency", "willingness_to_help", "available",
            )
        }


@dataclass(frozen=True)
class PartnerOutput:
    command: HumanCommand
    messages: tuple[Message, ...] = ()
    state_updates: tuple[dict[str, Any], ...] = ()


def _work_item_for(scenario: ContinuousScenario, role: str, object_id: str,
                   destination: str) -> WorkItem | None:
    matches = [item for item in scenario.resolved_activity().work_items
               if item.object_id == object_id and item.destination == destination]
    return next((item for item in matches if item.preferred_role == role), matches[0] if matches else None)


def _work_item_roles(item: WorkItem) -> tuple[str, ...]:
    roles = [item.preferred_role]
    other_role = "robot" if item.preferred_role == "human" else "human"
    if item.handoff in {"open", f"{item.preferred_role}_{other_role}"}:
        roles.append(other_role)
    return tuple(roles)


def _work_item_completed(item: WorkItem, completed_skills) -> bool:
    return any(f"{role}:{item.object_id}:{item.destination}" in completed_skills
               for role in _work_item_roles(item))


def _prerequisites_satisfied(scenario: ContinuousScenario, role: str, object_id: str,
                             destination: str, completed_skills: tuple[str, ...] | list[str]) -> bool:
    item = _work_item_for(scenario, role, object_id, destination)
    if item is None:
        return True
    if role not in _work_item_roles(item):
        return False
    items = scenario.resolved_activity().work_items
    for prerequisite in item.prerequisites:
        source = next((candidate for candidate in items if prerequisite == candidate.item_id
                       or prerequisite in {f"human:{candidate.object_id}:{candidate.destination}",
                                           f"robot:{candidate.object_id}:{candidate.destination}"}), None)
        if source is None or not _work_item_completed(source, completed_skills):
            return False
    return True


def _handoff_allowed(scenario: ContinuousScenario, object_id: str, destination: str) -> bool:
    for item in scenario.resolved_activity().work_items:
        if item.object_id == object_id and item.destination == destination:
            return "human" in _work_item_roles(item)
    return True


class ContinuousPartner(Protocol):
    def reset(self, seed: int) -> None: ...
    def initial_messages(self) -> tuple[Message, ...]: ...
    def step(self, observation: Observation) -> PartnerOutput: ...


class AdaptivePartner:
    """一个冻结参数、但行为随可见进度更新的伙伴基线。

    它没有读取机器人的目标或场景评测标签。伙伴把可用性、信任、距离、
    任务紧迫性和机器人当前占用作为连续效用，逐 tick 选择下一步贡献。
    """

    def __init__(self, scenario: ContinuousScenario, *, stochastic: bool = False,
                 update_adaptation: bool = True):
        self.scenario = scenario
        self.stochastic = stochastic
        self.update_adaptation = update_adaptation
        self.reset(0)

    def reset(self, seed: int) -> None:
        self.rng = np.random.default_rng(seed)
        self.seen_messages = 0
        self.state = HumanAdaptiveState(
            available=self.scenario.human_availability,
            initiative=self.scenario.dynamics.human_initiative,
            willingness_to_help=self.scenario.human_availability,
        )
        self.state_updates: list[dict[str, Any]] = []
        self.pending_state_updates: list[dict[str, Any]] = []
        self.commitments = dict(self.scenario.human_targets)
        self.accepted_requests: dict[str, str] = {}
        self.current_object: str | None = None
        self.current_destination: str | None = None
        self.left_until = 0
        self.has_left = False
        self.last_robot_progress = 0.0
        self.last_robot_action = "idle"
        self.reassignments = 0
        self.recovery_wait_steps = 0
        self.messages_sent: list[Message] = []
        self.seen_robot_completions: set[str] = set()

    @property
    def trust(self) -> float:
        return self.state.trust

    @trust.setter
    def trust(self, value: float) -> None:
        if self.update_adaptation:
            self.state.trust = float(np.clip(value, 0.0, 1.0))

    @property
    def workload(self) -> float:
        return self.state.workload

    @workload.setter
    def workload(self, value: float) -> None:
        if self.update_adaptation:
            self.state.workload = float(np.clip(value, 0.0, 1.0))

    def _update_state(self, field_name: str, value: float, reason: str,
                      observation: Observation, evidence: dict[str, Any] | None = None) -> None:
        if not hasattr(self.state, field_name):
            raise ValueError(f"未知伙伴状态字段: {field_name}")
        if not self.update_adaptation:
            return
        before = self.state.snapshot()
        setattr(self.state, field_name, value)
        self.state.clipped()
        after = self.state.snapshot()
        if before == after:
            return
        update = {
            "step": int(round(observation.time_s * self.scenario.tick_hz)),
            "reason": reason,
            "field": field_name,
            "before": before,
            "after": after,
            "evidence": evidence or {},
        }
        self.state_updates.append(update)
        self.pending_state_updates.append(update)

    def _drain_state_updates(self) -> tuple[dict[str, Any], ...]:
        updates = tuple(self.pending_state_updates)
        self.pending_state_updates.clear()
        return updates

    def initial_messages(self) -> tuple[Message, ...]:
        return self.scenario.initial_messages()

    def _process_messages(self, observation: Observation) -> list[Message]:
        outgoing: list[Message] = []
        for message in observation.messages[self.seen_messages:]:
            if message.speaker == "robot" and message.kind == "request_help" and message.object_id:
                load = self.workload + 0.25 * len(self.commitments)
                probability = np.clip(self.state.willingness_to_help * (
                                          0.6 * self.trust + 0.4 * self.state.reliability_belief)
                                      + self.scenario.dynamics.human_replan_sensitivity * 0.12
                                      - load * 0.08, 0.0, 1.0)
                accepted = bool(self.rng.random() < probability) if self.stochastic else probability >= 0.35
                destination = message.destination or f"tray_{message.object_id}"
                if accepted and _handoff_allowed(self.scenario, message.object_id, destination):
                    self.accepted_requests[message.object_id] = destination
                    self.commitments[message.object_id] = destination
                    outgoing.append(Message("human", "help_reply", "我可以接手这个贡献。",
                                             message.object_id, "accept", destination))
                    self._update_state("willingness_to_help", self.state.willingness_to_help + 0.02,
                                       "help_request_accepted", observation,
                                       {"object_id": message.object_id})
                else:
                    outgoing.append(Message("human", "help_reply", "我现在无法接手，请你继续完成。",
                                             message.object_id, "decline"))
                    self._update_state("willingness_to_help", self.state.willingness_to_help - 0.06,
                                       "help_request_declined", observation,
                                       {"object_id": message.object_id})
                self._update_state("workload", self.workload + 0.08, "help_request_observed",
                                   observation, {"object_id": message.object_id})
                self._update_state("robot_dependency", self.state.robot_dependency + 0.05,
                                   "help_request_observed", observation,
                                   {"object_id": message.object_id})
            elif message.speaker == "robot" and message.kind == "action_failed" and message.object_id:
                destination = message.destination or f"tray_{message.object_id}"
                probability = self.scenario.dynamics.handoff_on_failure_probability
                should_take = bool(self.rng.random() < probability) if self.stochastic else probability >= 0.5
                self._update_state("trust", self.trust - 0.12, "robot_action_failed",
                                   observation, {"object_id": message.object_id})
                self._update_state("reliability_belief", self.state.reliability_belief - 0.18,
                                   "robot_action_failed", observation,
                                   {"object_id": message.object_id})
                if should_take and _handoff_allowed(self.scenario, message.object_id, destination):
                    self.commitments[message.object_id] = destination
                    self._update_state("robot_dependency", self.state.robot_dependency + 0.08,
                                       "robot_action_failed", observation,
                                       {"object_id": message.object_id})
                    self.reassignments += 1
                    self.recovery_wait_steps = max(self.recovery_wait_steps, 1)
                    outgoing.append(Message("human", "reassignment", "机器人未完成，我接手这个贡献。",
                                             message.object_id, "accept", destination))
            elif message.speaker == "robot" and message.kind == "action_delayed":
                self._update_state("trust", self.trust - 0.025, "robot_action_delayed",
                                   observation, {"object_id": message.object_id})
                self._update_state("reliability_belief", self.state.reliability_belief - 0.04,
                                   "robot_action_delayed", observation,
                                   {"object_id": message.object_id})
            elif message.speaker == "robot" and message.kind == "acknowledge":
                self._update_state("trust", self.trust + 0.015, "robot_acknowledged",
                                   observation)
                self._update_state("reliability_belief", self.state.reliability_belief + 0.01,
                                   "robot_acknowledged", observation)
        self.seen_messages = len(observation.messages)
        for skill in observation.completed_skills:
            if skill.startswith("robot:") and skill not in self.seen_robot_completions:
                self.seen_robot_completions.add(skill)
                self._update_state("trust", self.trust + 0.04, "robot_contribution_completed",
                                   observation, {"completed_skill": skill})
                self._update_state("reliability_belief", self.state.reliability_belief + 0.06,
                                   "robot_contribution_completed", observation,
                                   {"completed_skill": skill})
        return outgoing

    def _goal_candidates(self, observation: Observation) -> list[tuple[float, str, str]]:
        candidates = []
        for object_id, destination in self.commitments.items():
            if object_id in observation.held_by_human:
                continue
            object_position = np.asarray(observation.objects[object_id])
            region_position = np.asarray(observation.regions[destination])
            if not _prerequisites_satisfied(self.scenario, "human", object_id, destination,
                                            observation.completed_skills):
                continue
            if (float(np.linalg.norm(object_position - region_position)) <= 0.065
                    and any(f"{role}:{object_id}:{destination}" in observation.completed_skills
                            for role in ("human", "robot"))):
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
        self.last_robot_action = observation.active_robot_action
        if self.left_until > 0:
            self.left_until -= 1
            if self.left_until == 0 and self.scenario.dynamics.return_on_robot_idle:
                messages.append(Message("human", "returned", "我回来了，依据当前进度继续。"))
                self._update_state("available", self.scenario.human_availability,
                                   "returned", observation)
                self._update_state("initiative", self.state.initiative + 0.03,
                                   "returned", observation)
            return PartnerOutput(HumanCommand("away", target=(0.50, 0.90, 0.0)), tuple(messages),
                                 self._drain_state_updates())
        if self.recovery_wait_steps > 0:
            self.recovery_wait_steps -= 1
            return PartnerOutput(HumanCommand("observe", target=observation.human_position),
                                 tuple(messages), self._drain_state_updates())
        if (not self.has_left and self.scenario.dynamics.leave_pressure > 0.0
                and observation.active_robot_action != "idle"):
            stress = min(1.0, self.workload + (1.0 - self.trust)
                         + (0.35 if observation.action_phase == "delayed" else 0.0))
            leave_score = self.scenario.dynamics.leave_pressure * (0.45 + 0.55 * stress)
            if self.scenario.leave_probability > 0.0:
                leave_score = max(leave_score, self.scenario.leave_probability * stress)
            should_leave = bool(self.rng.random() < leave_score) if self.stochastic else leave_score >= 0.5
            if should_leave:
                self.has_left = True
                self.left_until = self.scenario.leave_duration_steps
                messages.append(Message("human", "temporarily_away", "我暂时离开一下，稍后依据进度回来。"))
                self._update_state("available", 0.0, "temporarily_away", observation)
                self._update_state("commitment_stability", self.state.commitment_stability - 0.04,
                                   "temporarily_away", observation)
                return PartnerOutput(HumanCommand("away", target=(0.50, 0.90, 0.0)), tuple(messages),
                                     self._drain_state_updates())
        if observation.active_robot_action.startswith("transfer:"):
            target_object = observation.active_robot_action.split(":", 1)[1]
            if target_object in self.commitments and target_object not in observation.held_by_human:
                self._update_state("trust", self.trust - 0.001, "shared_space_conflict",
                                   observation, {"object_id": target_object})
                messages.append(Message("human", "correction", "这个贡献由我处理，请让行。",
                                        target_object, "yield", self.commitments[target_object]))
                self._update_state("workload", self.workload + 0.02, "shared_space_conflict",
                                   observation, {"object_id": target_object})
                return PartnerOutput(HumanCommand("yield", target=(0.50, 0.78, 0.0)), tuple(messages),
                                     self._drain_state_updates())
        if observation.held_by_human:
            held_object = observation.held_by_human[0]
            destination = self.commitments.get(held_object, self.current_destination)
            if destination in observation.regions:
                region = observation.regions[destination]
                return PartnerOutput(HumanCommand("carry", held_object, destination,
                                                  (float(region[0]), float(region[1]), 0.0)), tuple(messages),
                                     self._drain_state_updates())
        candidates = self._goal_candidates(observation)
        if not candidates:
            self._update_state("workload", self.workload - 0.01, "no_available_contribution",
                               observation)
            return PartnerOutput(HumanCommand("observe", target=observation.human_position), tuple(messages),
                                 self._drain_state_updates())
        _, object_id, destination = candidates[0]
        self.current_object = object_id
        self.current_destination = destination
        object_position = np.asarray(observation.objects[object_id])
        region_position = np.asarray(observation.regions[destination])
        target_position = region_position if object_id in observation.held_by_human else object_position
        target = (float(target_position[0]), float(target_position[1]), 0.0)
        intent = "carry" if object_id in observation.held_by_human else "approach"
        self._update_state("workload", self.workload + 0.015, "contribution_selected", observation,
                           {"object_id": object_id, "destination": destination})
        return PartnerOutput(HumanCommand(intent, object_id, destination, target), tuple(messages),
                             self._drain_state_updates())


@dataclass
class HumanProfile:
    """单个伙伴的稳定行为倾向；它不是当前任务状态。"""

    profile_id: str = "balanced"
    pace: float = 1.0
    assertiveness: float = 0.55
    interruption_tolerance: float = 0.55
    cooperation: float = 0.75
    persistence: float = 0.72
    autonomy: float = 0.60

    def clipped(self) -> "HumanProfile":
        for field_name in ("pace", "assertiveness", "interruption_tolerance",
                           "cooperation", "persistence", "autonomy"):
            setattr(self, field_name, float(np.clip(getattr(self, field_name), 0.1, 1.0)))
        return self

    def snapshot(self) -> dict[str, float | str]:
        return {
            "profile_id": self.profile_id,
            "pace": round(self.pace, 6),
            "assertiveness": round(self.assertiveness, 6),
            "interruption_tolerance": round(self.interruption_tolerance, 6),
            "cooperation": round(self.cooperation, 6),
            "persistence": round(self.persistence, 6),
            "autonomy": round(self.autonomy, 6),
        }


@dataclass
class HumanIntention:
    """伙伴在当前时间窗内的长期目标假设和局部行动阶段。"""

    objective: str
    object_id: str | None
    destination: str | None
    phase: str
    reason: str
    commitment: float

    def snapshot(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "object_id": self.object_id,
            "destination": self.destination,
            "phase": self.phase,
            "reason": self.reason,
            "commitment": round(float(self.commitment), 6),
        }


class DynamicHumanPolicy(AdaptivePartner):
    """具有稳定个体特征、长期意图和事件记忆的动态人类策略。

    它只读取公开观察，但会把公开消息、机器人动作结果和共同进度写入
    有限记忆，并在线更新当前意图。配置中的 profile 只决定倾向；具体
    贡献、让行、接管和离返仍由当前观察中的效用重新选择。
    """

    def __init__(self, scenario: ContinuousScenario, *, profile_id: str = "balanced",
                 stochastic: bool = True):
        self.profile_id = profile_id
        super().__init__(scenario, stochastic=stochastic, update_adaptation=True)

    def reset(self, seed: int) -> None:
        super().reset(seed)
        profile_defaults = {
            "assertive": (1.05, 0.82, 0.35, 0.68, 0.78, 0.78),
            "careful": (0.82, 0.38, 0.82, 0.78, 0.84, 0.48),
            "supportive": (0.95, 0.48, 0.62, 0.94, 0.78, 0.50),
            "balanced": (1.00, 0.55, 0.55, 0.75, 0.72, 0.60),
        }
        values = profile_defaults.get(self.profile_id, profile_defaults["balanced"])
        jitter = self.rng.normal(0.0, 0.025, len(values))
        self.profile = HumanProfile(self.profile_id, *(np.asarray(values) + jitter)).clipped()
        self.memory: list[dict[str, Any]] = []
        self.memory_retrievals: list[dict[str, Any]] = []
        self.reflections: list[dict[str, Any]] = []
        self.episode_state: dict[str, Any] = {
            "phase": "orient",
            "open_commitments": sorted(self.commitments),
            "last_public_feedback": None,
            "last_reflection_time_s": None,
        }
        self.intention: HumanIntention | None = None
        self.intention_history: list[dict[str, Any]] = []
        self._last_intention_key: tuple[Any, ...] | None = None

    def _remember(self, observation: Observation, event: str, details: dict[str, Any],
                  salience: float = 0.5) -> None:
        self.memory.append({
            "memory_id": f"m{len(self.memory):05d}",
            "time_s": round(float(observation.time_s), 6),
            "event": event,
            "salience": round(float(np.clip(salience, 0.0, 1.0)), 6),
            "details": details,
            "access_count": 0,
            "last_access_time_s": None,
        })
        if len(self.memory) > 48:
            self.memory = sorted(self.memory, key=lambda item: (item["salience"], item["time_s"]))[-48:]

    def _retrieve_memories(self, observation: Observation, *, query: str,
                           object_id: str | None = None, top_k: int = 5) -> list[dict[str, Any]]:
        """按语义线索、时间新近性和显著性检索，而非简单截断尾部。"""
        query_terms = set(query.lower().split("_"))
        scored = []
        for item in self.memory:
            details = item.get("details", {})
            detail_terms = {str(value).lower() for value in details.values() if value is not None}
            semantic = 1.0 if query.lower() in str(item.get("event", "")).lower() else 0.0
            if object_id and object_id in detail_terms:
                semantic += 0.8
            semantic += 0.15 * len(query_terms & set(str(item.get("event", "")).lower().split("_")))
            age = max(0.0, float(observation.time_s) - float(item.get("time_s", 0.0)))
            recency = math.exp(-age / 12.0)
            score = 0.50 * semantic + 0.30 * recency + 0.20 * float(item.get("salience", 0.0))
            scored.append((score, item))
        scored.sort(key=lambda pair: (pair[0], pair[1].get("time_s", 0.0)), reverse=True)
        selected = []
        for score, item in scored[:max(1, top_k)]:
            item["access_count"] = int(item.get("access_count", 0)) + 1
            item["last_access_time_s"] = round(float(observation.time_s), 6)
            selected.append({"memory_id": item["memory_id"], "score": round(float(score), 6),
                             "event": item["event"]})
        self.memory_retrievals.append({"time_s": round(float(observation.time_s), 6),
                                       "query": query, "object_id": object_id,
                                       "selected": selected})
        if len(self.memory_retrievals) > 96:
            self.memory_retrievals = self.memory_retrievals[-96:]
        return [item for _, item in scored[:max(1, top_k)]]

    def _reflect(self, observation: Observation, trigger: str,
                 evidence: dict[str, Any], *, outcome: str) -> None:
        retrieved = self._retrieve_memories(observation, query=trigger,
                                             object_id=evidence.get("object_id"))
        record = {
            "time_s": round(float(observation.time_s), 6),
            "trigger": trigger,
            "outcome": outcome,
            "evidence": evidence,
            "intention": self.intention.snapshot() if self.intention else None,
            "retrieved_memory_ids": [item["memory_id"] for item in retrieved],
            "state": self.state.snapshot(),
        }
        self.reflections.append(record)
        self.episode_state["last_reflection_time_s"] = record["time_s"]
        self.episode_state["last_public_feedback"] = trigger
        if len(self.reflections) > 96:
            self.reflections = self.reflections[-96:]

    def _select_intention(self, observation: Observation, reason: str) -> None:
        self._retrieve_memories(observation, query=reason)
        candidates = []
        for object_id, destination in self.commitments.items():
            if object_id in observation.held_by_human:
                phase = "carry"
                distance = np.linalg.norm(np.asarray(observation.regions[destination])
                                          - np.asarray(observation.human_position))
            else:
                phase = "approach"
                distance = np.linalg.norm(np.asarray(observation.objects[object_id])
                                          - np.asarray(observation.human_position))
            if not _prerequisites_satisfied(self.scenario, "human", object_id, destination,
                                            observation.completed_skills):
                continue
            if any(f"{role}:{object_id}:{destination}" in observation.completed_skills
                   for role in ("human", "robot")):
                continue
            priority = next((item.priority for item in self.scenario.resolved_activity().work_items
                             if item.object_id == object_id and item.destination == destination), 1.0)
            conflict = 0.0
            if observation.active_robot_action == f"transfer:{object_id}":
                conflict = self.profile.assertiveness * 0.5
            score = (priority * (0.8 + self.profile.persistence)
                     + self.profile.autonomy * 0.25
                     - float(distance) * (0.5 + self.profile.pace * 0.2)
                     - conflict)
            candidates.append((score, object_id, destination, phase))
        candidates.sort(reverse=True)
        selected = candidates[0] if candidates else None
        if selected is None:
            new_intention = HumanIntention("maintain shared activity", None, None,
                                           "observe", reason, self.profile.persistence)
        else:
            _, object_id, destination, phase = selected
            new_intention = HumanIntention("complete committed contribution", object_id,
                                           destination, phase, reason,
                                           self.profile.persistence)
        key = (new_intention.objective, new_intention.object_id, new_intention.destination,
               new_intention.phase)
        if key != self._last_intention_key:
            self.intention_history.append({"time_s": observation.time_s,
                                           "reason": reason,
                                           "intention": new_intention.snapshot()})
            self._reflect(observation, "intention_switch", {"reason": reason},
                          outcome="replanned")
            self._last_intention_key = key
        self.intention = new_intention
        self.episode_state["phase"] = new_intention.phase
        self.episode_state["open_commitments"] = sorted(self.commitments)

    def _process_messages(self, observation: Observation) -> list[Message]:
        new_messages = observation.messages[self.seen_messages:]
        for message in new_messages:
            self._remember(observation, "public_message", {
                "speaker": message.speaker, "kind": message.kind,
                "object_id": message.object_id, "value": message.value,
            }, 0.85 if message.kind in {"action_failed", "correction", "reassignment"} else 0.55)
            if message.kind in {"action_failed", "action_delayed", "correction", "reassignment",
                                "temporarily_away", "returned"}:
                self._reflect(observation, message.kind,
                              {"object_id": message.object_id, "value": message.value},
                              outcome="public_feedback_processed")
        for skill in observation.completed_skills:
            if skill not in self.seen_robot_completions and skill.startswith("robot:"):
                self._remember(observation, "robot_contribution_completed", {"skill": skill}, 0.65)
        messages = super()._process_messages(observation)
        trigger = "public_feedback" if new_messages else "progress"
        self._select_intention(observation, trigger)
        return messages

    def _goal_candidates(self, observation: Observation) -> list[tuple[float, str, str]]:
        candidates = super()._goal_candidates(observation)
        if self.intention is None:
            return candidates
        adjusted = []
        for score, object_id, destination in candidates:
            if (object_id, destination) == (self.intention.object_id, self.intention.destination):
                score -= 0.45 * self.profile.persistence
            if observation.active_robot_action == f"transfer:{object_id}":
                score -= 0.45 * self.profile.assertiveness
            adjusted.append((score / self.profile.pace, object_id, destination))
        return sorted(adjusted)

    def step(self, observation: Observation) -> PartnerOutput:
        output = super().step(observation)
        if self.intention is None:
            self._select_intention(observation, "initial_observation")
        updates = list(output.state_updates)
        if self.intention_history and np.isclose(self.intention_history[-1]["time_s"], observation.time_s):
            updates.append({"field": "intention", "reason": self.intention_history[-1]["reason"],
                            "intention": self.intention.snapshot() if self.intention else None,
                            "profile": self.profile.snapshot(), "memory_size": len(self.memory)})
        return PartnerOutput(output.command, output.messages, tuple(updates))

    def audit_state(self) -> dict[str, Any]:
        return {"policy": "dynamic_human_policy", "profile": self.profile.snapshot(),
                "intention": self.intention.snapshot() if self.intention else None,
                "episode_state": self.episode_state,
                "memory_size": len(self.memory), "memory": self.memory,
                "memory_retrievals": self.memory_retrievals,
                "reflections": self.reflections,
                "intention_history": self.intention_history,
                "intention_switches": len(self.intention_history)}


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
            elif message.speaker == "robot" and message.kind == "action_failed" and message.object_id:
                destination = message.destination or f"tray_{message.object_id}"
                self.accepted_requests[message.object_id] = destination
                self.commitments[message.object_id] = destination
                outgoing.append(Message("human", "reassignment", "我接手未完成贡献。",
                                         message.object_id, "accept", destination))
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
    if mode == "dynamic":
        return DynamicHumanPolicy(scenario)
    raise ValueError(f"未知伙伴模式: {mode}")


@dataclass
class _RobotExecution:
    action: Action
    phase: str = "approach"
    object_id: str | None = None
    destination: str | None = None
    progress: float = 0.0
    delay_remaining: int = 0
    failed: bool = False
    status_reported: bool = False
    starting_position: np.ndarray | None = None


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
        self.human_velocity = np.zeros(3, dtype=float)
        self.human_heading = 0.0
        self.human_gaze_target: tuple[float, float, float] | None = None
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
        self.robot_failures = 0
        self.robot_delay_steps = 0
        self.interruptions = 0
        self.near_misses = 0
        self.remaining_failure_budget = int(max(0, self.scenario.dynamics.robot_failure_budget))

    @property
    def time_s(self) -> float:
        return self.step_count * self.dt

    def say(self, message: Message) -> None:
        self.messages.append(message)
        self.events.append({"step": self.step_count, "kind": "public_message", "speaker": message.speaker,
                            "message_kind": message.kind, "object_id": message.object_id, "value": message.value,
                            "text": message.text})

    def record_event(self, kind: str, **data: Any) -> None:
        """记录不进入模型输入的 evaluator 事件，例如伙伴潜在状态更新。"""
        self.events.append({"step": self.step_count, "kind": kind, **data})

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
            task_family=self.scenario.task_family,
            task_description=self.scenario.description,
            scene_id=self.scenario.name,
        )

    def apply_human_command(self, command: HumanCommand) -> None:
        self.human_command = command
        self.human_gaze_target = command.gaze_target

    def start_action(self, action: Action) -> None:
        if self.robot_execution is not None:
            self.interruptions += 1
            self.events.append({"step": self.step_count, "kind": "robot_action_preempted",
                                "previous": self.robot_execution.action.kind, "next": action.kind})
        if action.kind == "request_help":
            self.say(Message("robot", "request_help", action.text, action.object_id, None, action.destination))
            self.robot_execution = _RobotExecution(action, phase="communicate", progress=0.0)
        elif action.kind == "acknowledge":
            self.say(Message("robot", "acknowledge", action.text, action.object_id))
            self.robot_execution = _RobotExecution(action, phase="communicate", progress=0.0)
        elif action.kind == "transfer":
            if action.object_id not in self.objects or action.destination not in self.regions:
                raise ValueError(f"连续场景中的动作目标不存在: {action}")
            dynamics = self.scenario.dynamics
            delay = (int(self.rng.integers(1, dynamics.max_delay_steps + 1))
                     if dynamics.max_delay_steps > 0
                     and self.rng.random() < dynamics.robot_delay_probability else 0)
            budget_failure = self.remaining_failure_budget > 0
            if budget_failure:
                self.remaining_failure_budget -= 1
            failed = budget_failure or bool(self.rng.random() < dynamics.robot_failure_probability)
            self.robot_execution = _RobotExecution(action, phase="approach", object_id=action.object_id,
                                                    destination=action.destination, progress=0.0,
                                                    delay_remaining=delay, failed=failed,
                                                    starting_position=self.objects[action.object_id].copy())
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
        if execution.delay_remaining > 0:
            execution.phase = "delayed"
            execution.delay_remaining -= 1
            self.robot_delay_steps += 1
            if not execution.status_reported:
                self.say(Message("robot", "action_delayed", "当前动作出现可见延迟。",
                                 execution.object_id, "delay", execution.destination))
                self.events.append({"step": self.step_count, "kind": "robot_action_delayed",
                                    "object_id": execution.object_id,
                                    "destination": execution.destination})
                execution.status_reported = True
            return
        if execution.failed:
            self.robot_failures += 1
            self.say(Message("robot", "action_failed", "当前动作未完成，需要重新分工。",
                             execution.object_id, "failed", execution.destination))
            self.events.append({"step": self.step_count, "kind": "robot_action_failed",
                                "object_id": execution.object_id,
                                "destination": execution.destination})
            self.robot_execution = None
            return
        if execution.phase == "delayed":
            execution.phase = "approach"
        if action.kind == "transfer":
            source = self.objects[execution.object_id]
            destination = self.regions[execution.destination]
            if execution.phase == "approach":
                if self._move(self.robot_pos, source + np.array((0.0, 0.0, 0.12)), 0.075):
                    execution.phase = "grasp"
            elif execution.phase == "grasp":
                if self.human_hold == execution.object_id:
                    self.say(Message("robot", "action_blocked", "伙伴正在持有该物体，机器人让行。",
                                     execution.object_id, "human_holding", execution.destination))
                    self.events.append({"step": self.step_count, "kind": "robot_blocked_by_human",
                                        "object_id": execution.object_id})
                    self.robot_execution = None
                    return
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
                if not _prerequisites_satisfied(self.scenario, "robot", execution.object_id,
                                                execution.destination, self.completed_skills):
                    self.robot_hold = None
                    self.objects[execution.object_id][:] = execution.starting_position
                    self.say(Message("robot", "action_blocked", "前置贡献尚未公开完成，暂不能提交这个工作项。",
                                     execution.object_id, "prerequisite", execution.destination))
                    self.events.append({"step": self.step_count, "kind": "robot_transfer_blocked",
                                        "object_id": execution.object_id,
                                        "destination": execution.destination})
                    self.robot_execution = None
                    return
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
        delta = target - self.human_pos
        distance = float(np.linalg.norm(delta[:2]))
        desired = np.zeros(3, dtype=float)
        if distance > 1e-8:
            desired[:2] = delta[:2] / distance * max(0.0, float(command.speed_mps))
            self.human_heading = float(math.atan2(delta[1], delta[0]))
        max_delta_v = max(0.0, float(command.acceleration_mps2)) * self.dt
        velocity_delta = desired - self.human_velocity
        delta_norm = float(np.linalg.norm(velocity_delta))
        if delta_norm > max_delta_v > 0:
            velocity_delta *= max_delta_v / delta_norm
        elif max_delta_v <= 0:
            self.human_velocity[:] = desired
            velocity_delta = np.zeros(3, dtype=float)
        self.human_velocity += velocity_delta
        displacement = self.human_velocity * self.dt
        if np.linalg.norm(displacement[:2]) > distance > 0:
            displacement[:2] = delta[:2]
            self.human_velocity[:2] = displacement[:2] / self.dt
        self.human_pos[:] += displacement
        if distance <= 1e-8:
            self.human_velocity *= max(0.0, 1.0 - min(1.0, self.dt * 8.0))
        self.events.append({"step": self.step_count, "kind": "human_motion",
                            "intent": command.intent,
                            "position": self.human_pos.tolist(),
                            "velocity_mps": self.human_velocity.tolist(),
                            "speed_mps": float(command.speed_mps),
                            "acceleration_mps2": float(command.acceleration_mps2),
                            "heading_rad": float(self.human_heading),
                            "gaze_target": command.gaze_target})
        if command.object_id is None or command.object_id not in self.objects:
            return
        object_position = self.objects[command.object_id]
        robot_targeting = (self.robot_execution is not None
                           and self.robot_execution.object_id == command.object_id)
        if self.human_hold is None and command.intent == "approach" and robot_targeting:
            self.events.append({"step": self.step_count, "kind": "human_blocked_by_robot_claim",
                                "object_id": command.object_id})
            return
        if self.human_hold is None and command.intent == "approach" and np.linalg.norm(object_position[:2] - self.human_pos[:2]) < 0.07:
            self.human_hold = command.object_id
            self.events.append({"step": self.step_count, "kind": "human_grasped", "object_id": command.object_id})
        if self.human_hold == command.object_id:
            object_position[:] = self.human_pos + np.array((0.0, 0.0, 0.78))
            if command.destination and np.linalg.norm(self.regions[command.destination][:2] - self.human_pos[:2]) < 0.08:
                if _prerequisites_satisfied(self.scenario, "human", command.object_id,
                                            command.destination, self.completed_skills):
                    object_position[:] = self.regions[command.destination]
                    skill = f"human:{command.object_id}:{command.destination}"
                    if skill not in self.completed_skills:
                        self.completed_skills.append(skill)
                    self.events.append({"step": self.step_count, "kind": "human_transfer_completed",
                                        "object_id": command.object_id, "destination": command.destination})
                    self.human_hold = None
                else:
                    self.events.append({"step": self.step_count, "kind": "human_transfer_waiting",
                                        "object_id": command.object_id, "destination": command.destination})

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

    def finished_activity(self) -> bool:
        """检查活动契约的终态，不把贡献者身份误当作任务成功。"""
        activity = self.scenario.resolved_activity()
        for item in activity.work_items:
            if (item.object_id not in self.objects or item.destination not in self.regions
                    or item.object_id in {self.robot_hold, self.human_hold}
                    or np.linalg.norm(self.objects[item.object_id] - self.regions[item.destination]) >= 0.065
                    or not _work_item_completed(item, self.completed_skills)):
                return False
        return True


def load_continuous_policy(spec: str):
    if spec == "greedy_public":
        return GreedyPublicPolicy()
    if spec == "request_help_public":
        return RequestHelpPublicPolicy()
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
            if message.kind in {"help_reply", "reassignment"} and message.object_id:
                if message.value == "decline":
                    self.assignments[message.object_id] = ("robot", message.destination or f"tray_{message.object_id}")
                elif message.value == "accept":
                    self.assignments[message.object_id] = ("human", message.destination or f"tray_{message.object_id}")
        self.seen_messages = len(observation.messages)
        candidates = []
        for object_id, (assignment, destination) in self.assignments.items():
            if assignment == "robot":
                if (destination in observation.regions
                        and not any(f"{role}:{object_id}:{destination}" in observation.completed_skills
                                    for role in ("robot", "human"))):
                    candidates.append((math.dist(observation.robot_ee, observation.objects[object_id]), object_id, destination))
        if candidates:
            _, object_id, destination = min(candidates)
            return Action("transfer", object_id, destination, duration_steps=1)
        if observation.active_robot_action == "idle":
            return Action("wait", duration_steps=2)
        return Action("wait", duration_steps=2)


class RequestHelpPublicPolicy:
    """在执行机器人贡献前先公开请求接手的参考策略。

    这是历史反事实实验中的稳定对照：它只使用公开 assignment 和消息，
    不读取伙伴的信任或 evaluator 状态。通过公开协商避免触发机器人失败，
    可以和直接尝试 transfer 的策略形成同一场景的不同历史。
    """

    def reset(self) -> None:
        self.assignments: dict[str, tuple[str, str]] = {}
        self.seen_messages = 0
        self.requested: set[str] = set()

    def act(self, observation: Observation) -> Action:
        for message in observation.messages[self.seen_messages:]:
            if message.kind == "assignment" and message.object_id:
                self.assignments[message.object_id] = (message.value or "robot",
                                                       message.destination or f"tray_{message.object_id}")
            if message.kind in {"help_reply", "reassignment"} and message.object_id:
                if message.value == "decline":
                    self.assignments[message.object_id] = ("robot", message.destination or f"tray_{message.object_id}")
                elif message.value == "accept":
                    self.assignments[message.object_id] = ("human", message.destination or f"tray_{message.object_id}")
        self.seen_messages = len(observation.messages)
        candidates = []
        for object_id, (assignment, destination) in self.assignments.items():
            if assignment != "robot" or object_id in self.requested:
                continue
            if destination in observation.regions and object_id in observation.objects:
                if math.dist(observation.objects[object_id], observation.regions[destination]) > 0.065:
                    candidates.append((math.dist(observation.robot_ee, observation.objects[object_id]),
                                       object_id, destination))
        if candidates:
            _, object_id, destination = min(candidates)
            self.requested.add(object_id)
            return Action("request_help", object_id, destination,
                          text="我无法稳定完成这个贡献，可以请你接手吗？")
        if observation.active_robot_action == "idle":
            return Action("wait", duration_steps=2)
        return Action("wait", duration_steps=2)


class ContinuousBackend(Protocol):
    """真实或参考后端都必须提供的逐 tick 接口。"""

    def reset(self, seed: int) -> None: ...
    def observe(self) -> Observation: ...
    def say(self, message: Message) -> None: ...
    def record_event(self, kind: str, **data: Any) -> None: ...
    def apply_human_command(self, command: HumanCommand) -> None: ...
    def start_action(self, action: Action) -> None: ...
    def tick(self) -> None: ...
    def finished_robot(self) -> bool: ...
    def finished_human(self) -> bool: ...
    def finished_activity(self) -> bool: ...


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
    try:
        binder = getattr(world, "bind_output", None)
        if binder is not None:
            binder(output)
        return _run_continuous_episode(scenario, policy, partner, world=world, seed=seed,
                                       output=output, decision_interval=decision_interval,
                                       partner_mode=partner_mode)
    finally:
        closer = getattr(world, "close", None)
        if closer is not None:
            closer()


def _run_continuous_episode(scenario, policy, partner, *, world, seed, output,
                            decision_interval, partner_mode):
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
        wrist_artifact = getattr(world, "last_wrist_observation_path", None)
        if wrist_artifact is not None:
            record["wrist_rgb_artifact"] = str(wrist_artifact)
        return record

    for tick_index in range(scenario.max_steps):
        observation = world.observe()
        partner_output = partner.step(observation)
        for update in partner_output.state_updates:
            recorder = getattr(world, "record_event", None)
            if recorder is not None:
                recorder("human_state_update", **update)
                if update.get("field") == "intention":
                    recorder("human_intention_update", **update)
        for message in partner_output.messages:
            world.say(message)
        world.apply_human_command(partner_output.command)
        public_observation = world.observe()
        new_public_messages = public_observation.messages[policy_seen_messages:]
        public_reaction = any(message.kind in {"help_reply", "temporarily_away", "returned",
                                              "correction", "reassignment",
                                              "action_failed", "action_blocked"}
                              for message in new_public_messages)
        can_decide = (public_observation.active_robot_action == "idle" or public_reaction
                      or (getattr(policy, "continuous_control", False)
                          and tick_index % max(1, decision_interval) == 0))
        if can_decide:
            try:
                action = policy.act(public_observation)
            except Exception:
                audit_record = getattr(policy, "audit_record", None)
                failed_record = {"step": public_observation.time_s,
                                 "observation": observation_record(public_observation),
                                 "adapter": audit_record() if audit_record is not None else None}
                policy_io.append(failed_record)
                raise
            policy_seen_messages = len(public_observation.messages)
            policy_record = {"step": public_observation.time_s,
                             "observation": observation_record(public_observation),
                             "action": serialize(action)}
            audit_record = getattr(policy, "audit_record", None)
            if audit_record is not None:
                policy_record["adapter"] = audit_record()
            policy_io.append(policy_record)
            world.start_action(action)
            if action.kind == "finish":
                break
        public_observations.append(observation_record(public_observation))
        trace.append({"step": len(trace), "time_s": public_observation.time_s,
                      "objects": public_observation.objects,
                      "human_position": public_observation.human_position,
                      "robot_position": public_observation.robot_ee,
                      "active_robot_action": public_observation.active_robot_action,
                      "human_action": public_observation.visible_human_action,
                      "human_velocity_mps": getattr(world, "human_velocity", None).tolist()
                      if getattr(world, "human_velocity", None) is not None else None,
                      "human_heading_rad": getattr(world, "human_heading", None),
                      "human_gaze_target": getattr(world, "human_gaze_target", None),
                      "human_object": partner_output.command.object_id,
                      "human_destination": partner_output.command.destination})
        world.tick()
        if world.finished_activity():
            break
    terminal = world.observe()
    if trace and trace[-1]["time_s"] == terminal.time_s:
        trace.pop()
    trace.append({"step": len(trace), "time_s": terminal.time_s,
                  "objects": terminal.objects, "human_position": terminal.human_position,
                  "robot_position": terminal.robot_ee,
                  "active_robot_action": terminal.active_robot_action,
                  "human_action": terminal.visible_human_action,
                  "human_velocity_mps": getattr(world, "human_velocity", None).tolist()
                  if getattr(world, "human_velocity", None) is not None else None,
                  "human_heading_rad": getattr(world, "human_heading", None),
                  "human_gaze_target": getattr(world, "human_gaze_target", None),
                  "human_object": None, "human_destination": None,
                  "terminal": True})
    finalizer = getattr(world, "finish_episode", None)
    if finalizer is not None:
        finalizer()
    robot_success = world.finished_robot()
    human_success = world.finished_human()
    activity_success = bool(world.finished_activity())
    events = list(getattr(world, "events", ()))
    completed_skills = list(getattr(world, "completed_skills", ()))
    mode = partner_mode or {
        "FixedReplayPartner": "fixed_replay",
        "ReactivePartner": "reactive",
        "AdaptivePartner": "adaptive",
        "DynamicHumanPolicy": "dynamic",
    }.get(type(partner).__name__, type(partner).__name__)
    partner_audit = (partner.audit_state() if hasattr(partner, "audit_state") else {})
    # Private partner traces are evaluator artifacts. They are written as separate
    # JSONL streams so model inputs remain limited to public observations.
    audit_event_specs = (
        ("memory", "human_memory_write"),
        ("memory_retrievals", "human_memory_retrieval"),
        ("reflections", "human_reflection"),
        ("intention_history", "human_intention_update"),
    )
    for audit_key, event_kind in audit_event_specs:
        for record in partner_audit.get(audit_key, ()) or ():
            events.append({"step": record.get("time_s", 0.0), "kind": event_kind, **record})
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
    state_updates = [event for event in events if event.get("kind") == "human_state_update"]
    state_by_field: dict[str, list[dict[str, Any]]] = {}
    for update in state_updates:
        state_by_field.setdefault(str(update.get("field")), []).append(update)
    def state_delta(field_name: str) -> float | None:
        updates = state_by_field.get(field_name, [])
        if not updates:
            return None
        first = updates[0].get("before", {}).get(field_name)
        last = updates[-1].get("after", {}).get(field_name)
        if first is None or last is None:
            return None
        return round(float(last) - float(first), 6)

    failure_steps = [int(event["step"]) for event in events
                     if event.get("kind") in {"robot_action_failed", "robot_action_delayed"}]
    reassignment_steps = [int(event["step"]) for event in events
                          if event.get("kind") == "public_message"
                          and event.get("message_kind") == "reassignment"]
    recovery_steps = [step - failure_steps[0] for step in reassignment_steps
                      if failure_steps and step >= failure_steps[0]]
    public_replans = sum(event.get("kind") == "public_message" and
                         event.get("message_kind") in {"reassignment", "correction", "returned"}
                         for event in events)
    adaptation_events = sum(event.get("kind") in {
        "robot_action_preempted", "proximity_warning", "robot_action_delayed",
        "robot_action_failed"} for event in events)
    robot_expected = len(scenario.robot_targets)
    human_expected = len(scenario.human_targets)
    robot_completion = (sum(f"robot:{object_id}:{destination}" in completed_skills
                            for object_id, destination in scenario.robot_targets.items())
                        / robot_expected if robot_expected else 1.0)
    human_completion = (sum(f"human:{object_id}:{destination}" in completed_skills
                            for object_id, destination in scenario.human_targets.items())
                        / human_expected if human_expected else 1.0)
    contribution_complementarity = (min(robot_completion, human_completion)
                                    if robot_expected and human_expected
                                    else max(robot_completion, human_completion))
    failure_count = int(getattr(world, "robot_failures", 0))
    if failure_count == 0:
        recovery_status = "no_failure"
        recovery_success = None
        recovery_component = 1.0
    elif activity_success:
        recovery_status = "recovered_after_failure"
        recovery_success = 1.0
        recovery_component = 1.0
    else:
        recovery_status = "failed_to_recover"
        recovery_success = 0.0
        recovery_component = 0.0
    coordination_efficiency = 1.0 / (1.0 + (
        len(policy_io) + 2 * len(response_latencies) + 3 * result_preemptions(events)
    ) / max(1, len(trace)))
    cobalance_score = (0.35 * float(activity_success)
                       + 0.25 * contribution_complementarity
                       + 0.20 * recovery_component
                       + 0.20 * coordination_efficiency)
    result = {
        "scenario": scenario.name, "seed": seed, "robot_success": robot_success,
        "human_success": human_success, "task_success": activity_success,
        "condition": scenario.condition, "structure_family": scenario.structure.family,
        "structure_split": scenario.structure.split, "partner_mode": mode,
        "human_policy": partner_audit.get("policy", type(partner).__name__),
        "human_profile": partner_audit.get("profile"),
        "human_intention_switches": partner_audit.get("intention_switches"),
        "human_memory_size": partner_audit.get("memory_size"),
        "human_memory_writes": len(partner_audit.get("memory", ()) or ()),
        "human_memory_retrievals": len(partner_audit.get("memory_retrievals", ()) or ()),
        "human_reflections": len(partner_audit.get("reflections", ()) or ()),
        "human_intention": partner_audit.get("intention"),
        "task_family": scenario.task_family,
        "backend": type(world).__name__,
        "steps": tick_index + 1, "robot_actions": int(getattr(world, "robot_action_count", len(policy_io))),
        "preemptions": int(getattr(world, "interruptions", 0)),
        "robot_failures": int(getattr(world, "robot_failures", 0)),
        "robot_delay_steps": int(getattr(world, "robot_delay_steps", 0)),
        "proximity_warnings": int(getattr(world, "near_misses", 0)),
        "public_messages": len(getattr(world, "messages", ())),
        "action_chunks": len(policy_io),
        "completion_time_s": trace[-1]["time_s"] if trace else 0.0,
        "completed_skills": completed_skills, "events": len(events),
        "robot_role_success": all(
            f"robot:{object_id}:{destination}" in completed_skills
            for object_id, destination in scenario.robot_targets.items()
        ),
        "human_role_success": all(
            f"human:{object_id}:{destination}" in completed_skills
            for object_id, destination in scenario.human_targets.items()
        ),
        "response_latency_steps": (sum(response_latencies) / len(response_latencies)
                                    if response_latencies else None),
        "human_corrections": sum(event.get("message_kind") == "correction" for event in events),
        "human_reassignments": sum(event.get("message_kind") == "reassignment" for event in events),
        "human_state_updates": len(state_updates),
        "human_trust_delta": state_delta("trust"),
        "human_reliability_delta": state_delta("reliability_belief"),
        "human_workload_delta": state_delta("workload"),
        "human_dependency_delta": state_delta("robot_dependency"),
        "human_available_min": (min(update.get("after", {}).get("available", 1.0)
                                  for update in state_updates)
                                if state_updates else 1.0),
        "public_replans": int(public_replans),
        "recovery_time_steps": (min(recovery_steps) if recovery_steps else None),
        "handoff_success": bool(any("human:" in skill for skill in completed_skills)
                                and activity_success),
        "conflict_rate": (float(sum(event.get("kind") == "proximity_warning" for event in events))
                          / max(1, len(trace))),
        "human_yield_steps": human_actions.count("yield"),
        "human_idle_ratio": (human_actions.count("observe") / len(human_actions)
                              if human_actions else 0.0),
        "human_action_trace": [
            {"intent": row.get("human_action"), "object_id": row.get("human_object"),
             "destination": row.get("human_destination")}
            for row in trace
        ],
        "geometry_trace": [row.get("objects", {}) for row in trace],
        "adaptation_events": adaptation_events,
        "coordination_cost": float(len(policy_io) + 2 * len(response_latencies)
                                    + 3 * result_preemptions(events)),
        "activity_success": activity_success,
        "finish_declared": any(row.get("action", {}).get("kind") == "finish"
                                for row in policy_io),
        "public_observation_count": len(public_observations),
        "blocked_transfers": sum(event.get("kind") in {"robot_transfer_blocked", "robot_blocked_by_human"}
                                 for event in events),
        "robot_contribution_completion": round(float(robot_completion), 6),
        "human_contribution_completion": round(float(human_completion), 6),
        "contribution_complementarity": round(float(contribution_complementarity), 6),
        "recovery_success": (round(float(recovery_success), 6)
                             if recovery_success is not None else None),
        "recovery_status": recovery_status,
        "coordination_efficiency": round(float(coordination_efficiency), 6),
        "cobalance_score": round(float(cobalance_score), 6),
        "failure_count_for_recovery": failure_count,
    }
    if output is not None:
        output.mkdir(parents=True, exist_ok=True)
        (output / "scenario.json").write_text(
            json.dumps(scenario_to_dict(scenario),
                       ensure_ascii=False, indent=2))
        public_scenario = {
            "name": scenario.name,
            "description": scenario.description,
            "task_family": scenario.task_family,
            "objects": [spec.__dict__ for spec in scenario.objects],
            "regions": scenario.regions,
            "tick_hz": scenario.tick_hz,
            "max_steps": scenario.max_steps,
        }
        (output / "public_scenario.json").write_text(
            json.dumps(public_scenario, ensure_ascii=False, indent=2))
        (output / "trace.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in trace) + "\n")
        (output / "public_observations.jsonl").write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in public_observations) + "\n")
        (output / "policy_io.jsonl").write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in policy_io) + "\n")
        (output / "events.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n")
        for filename, key in (("human_memory.jsonl", "memory"),
                              ("human_reflections.jsonl", "reflections"),
                              ("human_intentions.jsonl", "intention_history"),
                              ("human_memory_retrievals.jsonl", "memory_retrievals")):
            records = partner_audit.get(key, ()) or ()
            (output / filename).write_text(
                "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
                + ("\n" if records else ""))
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


def run_paired_benchmark(*, policy_spec: str = "greedy_public", seed: int = 0,
                         output: Path | None = None,
                         scenarios: list[ContinuousScenario] | None = None,
                         backend_factory=ContinuousWorld,
                         partner_modes: tuple[str, ...] = ("fixed_replay", "reactive", "adaptive")) -> list[dict[str, Any]]:
    """在同一批场景和 seed 上运行伙伴条件配对实验。

    输出目录按 ``<partner_mode>/<scenario_name>`` 组织，配对关系由稳定的
    场景名、seed 和 scenario.json 表达，不需要额外 manifest。
    """
    invalid = set(partner_modes) - {"fixed_replay", "reactive", "adaptive", "dynamic"}
    if invalid:
        raise ValueError(f"未知伙伴模式: {sorted(invalid)}")
    scenario_list = scenarios or list(CONTINUOUS_SCENARIOS.values())
    results: list[dict[str, Any]] = []
    for mode in partner_modes:
        mode_output = output / mode if output else None
        results.extend(run_catalog(policy_spec=policy_spec, seed=seed, output=mode_output,
                                   scenarios=scenario_list, backend_factory=backend_factory,
                                   partner_mode=mode))
    if output:
        output.mkdir(parents=True, exist_ok=True)
        (output / "paired_summary.json").write_text(
            json.dumps({"episodes": results, "partner_modes": list(partner_modes),
                        "scenario_count": len(scenario_list), "seed": seed},
                       ensure_ascii=False, indent=2))
    return results


def run_counterfactual_benchmark(*, policy_specs: tuple[str, ...], seed: int = 0,
                                 output: Path | None = None,
                                 scenarios: list[ContinuousScenario] | None = None,
                                 backend_factory=ContinuousWorld,
                                 partner_mode: str = "adaptive") -> list[dict[str, Any]]:
    """在完全相同的场景和伙伴初始状态下比较多个机器人策略。

    每个策略都使用相同的 ``scenario``、seed 和伙伴模式；只有机器人输出
    会改变后续公开消息、动作结果和伙伴状态更新。这是识别“机器人行为
    是否改变人类后续协作”的反事实配对单元，而不是把伙伴当成固定脚本。
    结果按 ``<policy_name>/<scenario_name>`` 保存，配对关系由目录和
    ``counterfactual_group`` 字段表达，不依赖 manifest。
    """
    if not policy_specs:
        raise ValueError("policy_specs 至少需要一个策略")
    if len(set(policy_specs)) != len(policy_specs):
        raise ValueError("policy_specs 不能包含重复策略")
    if partner_mode not in {"fixed_replay", "reactive", "adaptive", "dynamic"}:
        raise ValueError(f"未知伙伴模式: {partner_mode}")
    scenario_list = scenarios or list(CONTINUOUS_SCENARIOS.values())
    results: list[dict[str, Any]] = []
    for policy_spec in policy_specs:
        policy_name = policy_spec.replace(":", "_").replace("/", "_")
        policy_output = output / policy_name if output else None
        for scenario in scenario_list:
            episode_output = policy_output / scenario.name if policy_output else None
            result = run_continuous_episode(
                scenario, load_continuous_policy(policy_spec),
                make_partner(scenario, partner_mode), seed=seed,
                output=episode_output, backend_factory=backend_factory,
                partner_mode=partner_mode,
            )
            result["policy_spec"] = policy_spec
            result["policy_name"] = policy_name
            result["counterfactual_group"] = f"{scenario.name}:seed={seed}:partner={partner_mode}"
            if episode_output is not None:
                (episode_output / "metrics.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2))
            results.append(result)
    if output:
        output.mkdir(parents=True, exist_ok=True)
        (output / "counterfactual_summary.json").write_text(
            json.dumps({"episodes": results, "policy_specs": list(policy_specs),
                        "partner_mode": partner_mode, "scenario_count": len(scenario_list),
                        "seed": seed}, ensure_ascii=False, indent=2))
    return results


def run_history_counterfactual(*, policy_specs: tuple[str, ...] = ("greedy_public", "request_help_public"),
                               seed: int = 0, output: Path | None = None,
                               scenarios: list[ContinuousScenario] | None = None,
                               backend_factory=ContinuousWorld,
                               partner_mode: str = "adaptive") -> list[dict[str, Any]]:
    """运行同一场景的历史反事实，并计算伙伴后续行为的历史依赖。

    两个策略共享实例、seed、伙伴初始状态和公开任务；差异只来自机器人
    在前期选择的公开动作。评测器寻找几何状态仍相同但伙伴动作已分化的
    时间点，从而区分“内部状态被更新”与“更新改变了可观察协作”。
    """
    results = run_counterfactual_benchmark(
        policy_specs=policy_specs, seed=seed, output=output, scenarios=scenarios,
        backend_factory=backend_factory, partner_mode=partner_mode)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        grouped.setdefault(str(result["counterfactual_group"]), []).append(result)
    for group_results in grouped.values():
        if len(group_results) < 2:
            continue
        baseline = group_results[0]
        base_geometry = baseline.get("geometry_trace", [])
        base_actions = baseline.get("human_action_trace", [])
        for result in group_results:
            geometry = result.get("geometry_trace", [])
            actions = result.get("human_action_trace", [])
            comparable = min(len(base_geometry), len(geometry), len(base_actions), len(actions))
            same_geometry_steps = 0
            divergent_steps = 0
            first_divergence = None
            for index in range(comparable):
                left = base_geometry[index]
                right = geometry[index]
                same_geometry = left.keys() == right.keys() and all(
                    np.linalg.norm(np.asarray(left[name]) - np.asarray(right[name])) <= 1e-6
                    for name in left
                )
                if not same_geometry:
                    continue
                same_geometry_steps += 1
                if base_actions[index] != actions[index]:
                    divergent_steps += 1
                    if first_divergence is None:
                        first_divergence = index
            result["same_geometry_steps"] = same_geometry_steps
            result["history_conditioned_action_divergence"] = (
                divergent_steps / same_geometry_steps if same_geometry_steps else 0.0
            )
            result["history_conditioned_first_divergence_step"] = first_divergence
            result["history_counterfactual_baseline"] = baseline["policy_name"]
            if output is not None:
                episode_output = output / result["policy_name"] / result["scenario"]
                episode_output.mkdir(parents=True, exist_ok=True)
                (episode_output / "metrics.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2))
    if output:
        (output / "history_counterfactual_summary.json").write_text(
            json.dumps({"episodes": results, "policy_specs": list(policy_specs),
                        "partner_mode": partner_mode, "scenario_count": len(scenarios or CONTINUOUS_SCENARIOS)},
                       ensure_ascii=False, indent=2))
    return results
