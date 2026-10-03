"""Evaluate measured physical outcomes; expected goals stay outside policy observations."""
from __future__ import annotations

import math
from .scenarios import Scenario


def evaluate(scenario: Scenario, positions: dict, regions: dict, events: list[dict], completed: bool) -> dict:
    packed = {name: math.dist(positions[name], regions[f"tray_{name}"]) < 0.07
              for name in ("red", "blue")}
    red_correct = packed["red"] if scenario.final_red == "pack" else (
        not packed["red"] and -0.425 <= positions["red"][0] <= 0.925
        and -0.525 <= positions["red"][1] <= 0.525 and 0.76 <= positions["red"][2] <= 0.90
    )
    active_red = scenario.initial_red
    forbidden = 0
    for event in events:
        if event["kind"] == "public_message" and event.get("object_id") == "red" and event.get("message_kind") in {"instruction", "correction"}:
            active_red = event["value"]
        if event["kind"] == "robot_transfer_completed" and event.get("object_id") == "red" and active_red == "keep":
            forbidden += 1
    interruptions = sum(e["kind"] == "robot_skill_interrupted" for e in events)
    acknowledgements = sum(e["kind"] == "robot_message" and e.get("action") == "acknowledge" for e in events)
    information_events = [e for e in events if e["kind"] == "partner_understanding_updated"]
    unchanged = all(e["physical_state_unchanged"] for e in information_events)
    reallocated = any(e["kind"] == "robot_transfer_completed" and e.get("object_id") == "blue"
                      for e in events) if not scenario.human_available else None
    failed_skills = sum(e["kind"] == "skill_failed" for e in events)
    return {
        "task_success": bool(red_correct and packed["blue"] and completed and failed_skills == 0),
        "red_goal_satisfied": bool(red_correct), "blue_goal_satisfied": packed["blue"],
        "red_packed": packed["red"], "forbidden_red_transfers": forbidden,
        "interrupted_skills": interruptions, "acknowledgements": acknowledgements,
        "information_only_update": unchanged if information_events else None,
        "reallocated_after_refusal": reallocated,
        "failed_skills": failed_skills, "policy_finished": completed,
        "final_positions": positions,
    }
