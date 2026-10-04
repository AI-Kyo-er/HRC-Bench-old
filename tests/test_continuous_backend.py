import json
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pytest

from hrc_pilot.benchmark import ExternalPolicyAdapter, ModelPolicy, decode_action
from hrc_pilot.continuous import (CONTINUOUS_SCENARIOS, ContinuousWorld,
                                 GreedyPublicPolicy, make_partner, run_continuous_episode)
from hrc_pilot.continuous_genesis import GenesisContinuousAdapter
from hrc_pilot.protocol import EventLog


def test_model_receives_pixels_without_evaluator_state():
    world = ContinuousWorld(CONTINUOUS_SCENARIOS["relay"])
    world.reset(0)
    pixels = np.full((8, 9, 3), 137, dtype=np.uint8)
    received = []
    policy = ModelPolicy(lambda value: received.append(value) or {"kind": "wait"})
    policy.act(world.observe(rgb=pixels))
    np.testing.assert_array_equal(received[0]["rgb"], pixels)
    received[0]["rgb"][0, 0, 0] = 0
    assert pixels[0, 0, 0] == 137
    assert "robot_targets" not in received[0]


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_invalid_joint_targets_rejected(value):
    with pytest.raises(ValueError):
        decode_action({"kind": "joint_position", "joints": [value] * 9})


def test_adapter_tick_and_events_use_benchmark_clock():
    class Workspace:
        scenario = CONTINUOUS_SCENARIOS["relay"]
        step_count = 0
        log = EventLog()

        def tick(self, steps):
            self.step_count += steps

    workspace = Workspace()
    adapter = GenesisContinuousAdapter(workspace)
    adapter.tick()
    adapter.record_event("human_state_update", step=1, field="trust")
    assert workspace.step_count == 6
    assert adapter.events[0]["step"] == 1
    assert adapter.events[0]["physics_step"] == 6


def test_runner_closes_backend_after_policy_error():
    scenario = CONTINUOUS_SCENARIOS["relay"]
    world = ContinuousWorld(scenario)
    closed = []
    world.close = lambda: closed.append(True)

    def fail(_):
        raise RuntimeError("policy inference failed")

    with pytest.raises(RuntimeError, match="inference failed"):
        run_continuous_episode(scenario, ModelPolicy(fail), make_partner(scenario),
                               backend_factory=lambda _: world)
    assert closed == [True]


def test_runner_binds_episode_output_and_records_terminal_state():
    scenario = replace(CONTINUOUS_SCENARIOS["relay"], max_steps=2)
    world = ContinuousWorld(scenario)
    bound, finished = [], []
    world.bind_output = lambda output: bound.append(output)
    world.finish_episode = lambda: finished.append(world.step_count)
    with TemporaryDirectory() as directory:
        output = Path(directory) / "adaptive" / "relay"
        result = run_continuous_episode(scenario, GreedyPublicPolicy(), make_partner(scenario),
                                        output=output, backend_factory=lambda _: world)
        trace = [json.loads(line) for line in (output / "trace.jsonl").read_text().splitlines()]
    assert bound == [output]
    assert finished == [2]
    assert trace[-1]["terminal"] is True
    assert result["completion_time_s"] == 0.2


def test_continuous_model_is_invoked_during_action_chunk():
    scenario = replace(CONTINUOUS_SCENARIOS["relay"], max_steps=7)
    policy = ModelPolicy(lambda _: {"kind": "wait", "duration_steps": 20},
                         continuous_control=True)
    run_continuous_episode(scenario, policy, make_partner(scenario), decision_interval=2)
    assert policy.calls == 4


def test_external_adapter_records_public_call_audit():
    world = ContinuousWorld(CONTINUOUS_SCENARIOS["relay"])
    world.reset(0)
    policy = ExternalPolicyAdapter(lambda value: {"kind": "wait", "duration_steps": 2},
                                   adapter_name="fake-vla")
    action = policy.act(world.observe())
    assert action.kind == "wait"
    assert policy.audit_record()["adapter"] == "fake-vla"
    assert policy.audit_record()["status"] == "ok"
    assert policy.audit_record()["action"]["kind"] == "wait"


def test_external_adapter_records_inference_error():
    world = ContinuousWorld(CONTINUOUS_SCENARIOS["relay"])
    world.reset(0)

    def fail(_):
        raise RuntimeError("model unavailable")

    policy = ExternalPolicyAdapter(fail)
    with pytest.raises(RuntimeError, match="model unavailable"):
        policy.act(world.observe())
    assert policy.audit_record()["status"] == "error"
    assert policy.audit_record()["error_type"] == "RuntimeError"
