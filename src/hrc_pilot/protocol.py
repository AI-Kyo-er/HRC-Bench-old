"""Simulator-independent public policy interface. No evaluator/private partner state."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Message:
    speaker: str
    kind: str
    text: str
    object_id: str | None = None
    value: str | None = None
    destination: str | None = None


@dataclass(frozen=True)
class Observation:
    # Pilot semantic geometry is simulator-derived; this is NOT a vision baseline.
    objects: dict[str, tuple[float, float, float]]
    regions: dict[str, tuple[float, float, float]]
    messages: tuple[Message, ...]
    robot_ee: tuple[float, float, float]
    human_position: tuple[float, float, float]
    held_by_human: tuple[str, ...]
    completed_skills: tuple[str, ...]
    robot_qpos: tuple[float, ...] = ()
    # Pass pixels, not an artifact path that could reveal the experimental condition.
    rgb: Any = None
    wrist_rgb: Any = None
    # Continuous benchmark fields. They expose execution timing and public action
    # status, while keeping scenario goals and partner latent state private.
    time_s: float = 0.0
    active_robot_action: str = ""
    action_phase: str = "idle"
    visible_human_action: str = ""
    # Public task semantics supplied by the scenario, never private goals or
    # evaluator state.  These fields let a VLA/WLA distinguish task families
    # without reverse-engineering a hard-coded benchmark name.
    task_family: str = "object_transport"
    task_description: str = ""
    scene_id: str = ""


@dataclass(frozen=True)
class Action:
    kind: str
    object_id: str | None = None
    destination: str | None = None
    text: str = ""
    joints: tuple[float, ...] = ()
    # A model may hold a control target for several simulator ticks. The runtime
    # can preempt it when a new public observation changes the decision.
    duration_steps: int = 1
    control_mode: str = "semantic"


class Policy(Protocol):
    def reset(self) -> None: ...
    def act(self, observation: Observation) -> Action: ...


@dataclass
class EventLog:
    events: list[dict[str, Any]] = field(default_factory=list)

    def add(self, step: int, kind: str, **data: Any) -> None:
        self.events.append({"step": step, "kind": kind, **data})


def serialize(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        result = asdict(value)
        if isinstance(value, Observation):
            for name in ("rgb", "wrist_rgb"):
                pixels = getattr(value, name)
                if pixels is not None:
                    result[name] = {"shape": list(pixels.shape), "dtype": str(pixels.dtype)}
        return result
    raise TypeError(type(value).__name__)
