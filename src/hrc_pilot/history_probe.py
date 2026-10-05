"""用真实运行的公开历史构造匹配当前输入的伙伴适应诊断。"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

from .continuous import (AdaptivePartner, CONTINUOUS_SCENARIOS, InteractionStructure,
                         GreedyPublicPolicy)
from .protocol import Action, Message, Observation, serialize


def make_history_prefix(name: str, *, failures: int):
    base = CONTINUOUS_SCENARIOS["concurrent_overlay"]
    return replace(base, name=name, description="机器人承担三个杯子的收纳，伙伴根据公开结果更新判断。",
                   human_targets={}, robot_targets={name: f"tray_{name}" for name in ("red", "blue", "green")},
                   activity=None, max_steps=120,
                   structure=InteractionStructure("isolated", ("joint_execution",)),
                   dynamics=replace(base.dynamics, robot_failure_budget=failures))


def make_history_probe():
    base = CONTINUOUS_SCENARIOS["relay"]
    return replace(base, name="matched_history_probe",
                   description="机器人先公开请求蓝杯的帮助，伙伴回应后完成收纳。",
                   human_targets={}, robot_targets={"blue": "tray_blue"}, activity=None,
                   max_steps=100, structure=InteractionStructure("isolated", ("joint_execution",)))


def recorded_observation(row: dict) -> Observation:
    values = {key: value for key, value in row.items()
              if key in Observation.__dataclass_fields__ and key not in {"rgb", "wrist_rgb"}}
    values["messages"] = tuple(Message(**message) for message in values["messages"])
    values["completed_skills"] = tuple(values["completed_skills"])
    values["held_by_human"] = tuple(values["held_by_human"])
    return Observation(**values)


class HistoryCarryoverPartner(AdaptivePartner):
    """从公开记录重放学习，只将 trust / reliability 带入匹配的当前任务。

    这是实验室匹配状态诊断，显式重建世界和协议上下文，不是同一自然活动的
    无重置长程评测。此前的分工、工作负载和剩余目标在探针中保持一致。
    不读取源运行的 metrics、私有潜变量或 evaluator 标签。
    """

    def __init__(self, scenario, *, history_scenario, history_records: list[dict], frozen: bool = False):
        self.history_scenario = history_scenario
        self.history_records = history_records
        self.frozen = frozen
        super().__init__(scenario, update_adaptation=not frozen)

    def reset(self, seed: int) -> None:
        super().reset(seed)
        learner = AdaptivePartner(self.history_scenario, update_adaptation=not self.frozen)
        learner.reset(seed)
        for row in self.history_records:
            learner.step(recorded_observation(row))
        self.source_state = learner.state.snapshot()
        self.history_updates = list(learner.state_updates)
        self.state = replace(self.state, trust=learner.state.trust,
                             reliability_belief=learner.state.reliability_belief)
        self.probe_initial_state = self.state.snapshot()
        self.probe_inputs: list[dict] = []

    def step(self, observation: Observation):
        encoded = serialize(observation)
        self.probe_inputs.append({
            "observation": encoded,
            "public_input_sha256": sha256(json.dumps(encoded, sort_keys=True).encode()).hexdigest(),
            "rgb_pixels_sha256": sha256(observation.rgb.tobytes()).hexdigest() if observation.rgb is not None else None,
        })
        return super().step(observation)


class HelpThenExecutePolicy(GreedyPublicPolicy):
    """相同首次请求；拒绝后承担贡献，接受后等待伙伴。"""

    def reset(self) -> None:
        super().reset()
        self.help_sent = False

    def act(self, observation: Observation) -> Action:
        action = super().act(observation)
        if not self.help_sent and action.kind == "transfer":
            self.help_sent = True
            return Action("request_help", action.object_id, action.destination,
                          text="你可以帮我把蓝杯放到收纳区吗？")
        return action


def read_public_history(directory: Path) -> list[dict]:
    return [json.loads(line) for line in (directory / "public_observations.jsonl").read_text().splitlines()
            if line.strip()]
