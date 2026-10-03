"""Transparent hand-written controls, not claims about trained model performance."""
from __future__ import annotations

import math
from .protocol import Action, Observation


class CoordinationPolicy:
    def __init__(self, mode: str = "memory"):
        if mode not in {"memory", "static", "reactive"}:
            raise ValueError(mode)
        self.mode = mode
        self.reset()

    def reset(self) -> None:
        self.red_intent = "pack"
        self.blue_owner = "robot"
        self.initialized = False
        self.requested = False
        self.seen = 0
        self.corrected = False

    def act(self, observation: Observation) -> Action:
        fresh = observation.messages[self.seen:]
        self.seen = len(observation.messages)
        for message in fresh:
            if message.kind == "instruction":
                self.red_intent = message.value or "pack"
            elif message.kind == "assignment":
                self.blue_owner = message.value or "robot"
            elif message.kind == "correction" and self.mode != "static":
                self.red_intent = message.value or self.red_intent
                self.corrected = True
                return Action("acknowledge", "red", text="明白，红杯留用；我更新后续安排。")
            elif message.kind == "moved" and self.mode == "reactive":
                # Local geometric recovery without preserving the prior agreement.
                self.red_intent = "pack"
            elif message.kind == "help_reply" and message.value == "decline" and self.mode != "static":
                self.blue_owner = "robot"
                return Action("acknowledge", "blue", text="明白，你现在不可用；蓝杯由我收纳。")

        def packed(name: str) -> bool:
            target = observation.regions[f"tray_{name}"]
            return math.dist(observation.objects[name][:2], target[:2]) < 0.07

        if self.blue_owner == "human" and not packed("blue"):
            if not self.requested:
                self.requested = True
                return Action("request_help", "blue", "tray_blue", "你现在能把蓝杯放进收纳区吗？")
            return Action("wait", text="等待伙伴贡献。")
        if self.red_intent == "pack" and not packed("red"):
            return Action("transfer", "red", "tray_red")
        if not packed("blue"):
            return Action("transfer", "blue", "tray_blue")
        return Action("finish")


def load_policy(spec: str):
    """Built-ins or module:factory. Custom policies get only Observation."""
    if spec in {"memory", "static", "reactive"}:
        return CoordinationPolicy(spec)
    import importlib
    module, factory = spec.split(":", 1)
    return getattr(importlib.import_module(module), factory)()
