"""Partner decisions depend on visible execution and public requests, not robot plans."""
from __future__ import annotations

from .protocol import Message
from .scenarios import Scenario


class ResponsivePartner:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self.intervened = False
        self.help_answered = False
        self.understanding = scenario.initial_red

    def initial_messages(self) -> list[Message]:
        red_text = "红杯留给我使用，蓝杯收纳。" if self.understanding == "keep" else "红杯和蓝杯都要收纳。"
        return [
            Message("human", "instruction", red_text, "red", self.understanding),
            Message("human", "assignment", f"蓝杯初始由{'人' if self.scenario.blue_owner == 'human' else '机器人'}收纳。",
                    "blue", self.scenario.blue_owner),
        ]

    def on_visible_approach(self, object_id: str, distance: float) -> str | None:
        if self.intervened or object_id != "red" or distance > 0.32:
            return None
        if self.scenario.intervention == "none":
            return None
        self.intervened = True
        if self.scenario.intervention == "information":
            # Private incoming information changes understanding BEFORE any physical action.
            self.understanding = "keep"
        return self.scenario.intervention

    def movement_message(self) -> Message:
        # Identical intervention evidence across the history pair.
        return Message("human", "moved", "我先把红杯移到旁边。", "red")

    def correction_message(self) -> Message:
        return Message("human", "correction", "我刚得知红杯还要在这里使用，请留给我。", "red", "keep")

    def on_public_request(self, object_id: str, held_objects: tuple[str, ...]) -> tuple[Message, bool]:
        self.help_answered = True
        accepted = self.scenario.human_available and not held_objects
        text = "可以，我来放蓝杯。" if accepted else "我现在要处理自己的事项，不能接手蓝杯，请你完成。"
        return Message("human", "help_reply", text, object_id, "accept" if accepted else "decline"), accepted
