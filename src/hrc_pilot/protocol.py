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


@dataclass(frozen=True)
class Action:
    kind: str
    object_id: str | None = None
    destination: str | None = None
    text: str = ""
    joints: tuple[float, ...] = ()


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
        if isinstance(value, Observation) and value.rgb is not None:
            result["rgb"] = {"shape": list(value.rgb.shape), "dtype": str(value.rgb.dtype)}
        return result
    raise TypeError(type(value).__name__)
