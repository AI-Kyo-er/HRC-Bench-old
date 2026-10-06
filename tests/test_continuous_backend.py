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
from hrc_pilot.backend import VCWorkspace
from hrc_pilot.protocol import Action, EventLog


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


def test_video_settling_does_not_add_contributions_to_terminal_score():
    scenario = replace(CONTINUOUS_SCENARIOS["relay"], max_steps=1)
    world = ContinuousWorld(scenario)

    def visual_tail():
        for object_id, destination in {**scenario.human_targets, **scenario.robot_targets}.items():
            world.objects[object_id] = np.array(scenario.regions[destination])
        world.completed_skills.extend(["human:red:tray_red", "robot:blue:tray_blue"])

    world.finish_episode = visual_tail
    result = run_continuous_episode(scenario, ModelPolicy(lambda _: {"kind": "wait"}), make_partner(scenario),
                                    backend_factory=lambda _: world)
    assert result["task_success"] is False
    assert result["completed_skills"] == []


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


def test_genesis_failure_budget_only_applies_to_started_transfers():
    # 直接检查生产后端的动作 / 反馈接口，不加载 GPU 或 Genesis。
    workspace = VCWorkspace.__new__(VCWorkspace)
    workspace.scenario = CONTINUOUS_SCENARIOS["relay"]
    workspace.remaining_failure_budget = 1
    workspace.continuous_rng = np.random.default_rng(7)
    workspace.continuous_execution = None
    workspace.step_count = 0
    workspace.log = EventLog()
    workspace.messages = []
    workspace.objects = {"blue": object()}
    workspace.regions = workspace.scenario.regions
    workspace.positions = lambda: {"blue": [0.35, -0.08, 0.82]}
    workspace.continuous_start_action(Action("wait"))
    assert workspace.remaining_failure_budget == 1
    workspace._continuous_robot_step()
    workspace.continuous_start_action(Action("transfer", "blue", "tray_blue"))
    workspace._continuous_robot_step()
    assert workspace.remaining_failure_budget == 0
    assert workspace.continuous_execution is None
    assert workspace.log.events[-1]["kind"] == "robot_action_failed"
    assert workspace.messages[-1].kind == "action_failed"
    assert workspace.messages[-1].object_id == "blue"
    assert GenesisContinuousAdapter(workspace).robot_failures == 1
    workspace.continuous_start_action(Action("transfer", "blue", "tray_blue"))
    assert not workspace.continuous_execution["failed"]
