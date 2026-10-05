"""检验冻结不破坏协议，以及匹配当前输入时历史是否改变伙伴回应。"""
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from hrc_pilot.continuous import AdaptivePartner, ContinuousWorld, GreedyPublicPolicy, run_continuous_episode
from hrc_pilot.history_probe import (HelpThenExecutePolicy, HistoryCarryoverPartner,
                                    make_history_prefix, make_history_probe, read_public_history)
from hrc_pilot.protocol import Message


def test_failure_updates_belief_even_when_handoff_is_declined():
    base = make_history_prefix("failure_without_handoff", failures=0)
    scenario = replace(base, dynamics=replace(base.dynamics, handoff_on_failure_probability=0.0))
    world = ContinuousWorld(scenario)
    world.say(Message("robot", "action_failed", "未完成", "blue", destination="tray_blue"))
    partner = AdaptivePartner(scenario)
    before = partner.state.snapshot()
    output = partner.step(world.observe())
    assert partner.state.trust < before["trust"]
    assert partner.state.reliability_belief < before["reliability_belief"]
    assert not any(message.kind == "reassignment" for message in output.messages)


def test_freezing_adaptation_keeps_protocol_response_and_state():
    scenario = make_history_prefix("frozen", failures=0)
    world = ContinuousWorld(scenario)
    partner = AdaptivePartner(scenario, update_adaptation=False)
    before = partner.state.snapshot()
    world.say(Message("robot", "action_failed", "未完成", "blue", destination="tray_blue"))
    output = partner.step(world.observe())
    partner.trust = 0.0
    partner.workload = 1.0
    assert partner.state.snapshot() == before
    assert output.state_updates == ()
    assert any(message.kind == "reassignment" for message in output.messages)


def test_success_evidence_is_not_recounted_on_every_tick():
    scenario = make_history_prefix("successful", failures=0)
    observation = ContinuousWorld(scenario).observe()
    observation = replace(observation, completed_skills=("robot:blue:tray_blue",))
    partner = AdaptivePartner(scenario)
    partner.step(observation)
    learned = partner.state.trust
    partner.step(observation)
    assert learned > 0.7
    assert partner.state.trust == learned


def test_public_history_changes_identical_request_only_with_adaptation():
    probe = make_history_probe()
    with TemporaryDirectory() as directory:
        root = Path(directory)
        sources = {}
        for history, failures in (("reliable", 0), ("failures", 3)):
            scenario = make_history_prefix(f"prefix_{history}", failures=failures)
            source = root / history
            result = run_continuous_episode(scenario, GreedyPublicPolicy(), AdaptivePartner(scenario), output=source)
            assert result["task_success"]
            sources[history] = scenario, read_public_history(source)
        initial_inputs, initial_actions, request_inputs, replies = [], [], [], {}
        for frozen in (False, True):
            for history, (source_scenario, records) in sources.items():
                partner = HistoryCarryoverPartner(probe, history_scenario=source_scenario,
                                                 history_records=records, frozen=frozen)
                target = root / "probe" / f"{history}_{frozen}"
                result = run_continuous_episode(probe, HelpThenExecutePolicy(), partner, output=target)
                assert result["task_success"]
                calls = [json.loads(line) for line in (target / "policy_io.jsonl").read_text().splitlines()]
                initial_inputs.append(calls[0]["observation"])
                initial_actions.append(calls[0]["action"])
                assert "trust" not in calls[0]["observation"]
                events = [json.loads(line) for line in (target / "events.jsonl").read_text().splitlines()]
                reply = next(event for event in events if event.get("message_kind") == "help_reply")
                replies[history, frozen] = reply["value"]
                request_input = next(row for row in partner.probe_inputs if any(
                    message["speaker"] == "robot" and message["kind"] == "request_help"
                    for message in row["observation"]["messages"]))
                request_inputs.append(request_input["public_input_sha256"])
        assert all(value == initial_inputs[0] for value in initial_inputs)
        assert all(value == initial_actions[0] for value in initial_actions)
        assert len(set(request_inputs)) == 1
        assert replies["reliable", False] == "accept"
        assert replies["failures", False] == "decline"
        assert replies["reliable", True] == replies["failures", True] == "accept"
