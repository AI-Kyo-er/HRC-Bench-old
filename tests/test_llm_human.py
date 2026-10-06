import json

from hrc_pilot.continuous import CONTINUOUS_SCENARIOS, ContinuousWorld
from hrc_pilot.llm_human import QwenHumanPolicy
from hrc_pilot.protocol import Action, Message


def test_qwen_partner_uses_public_prompt_and_validates_decision():
    scenario = CONTINUOUS_SCENARIOS["concurrent_overlay"]
    world = ContinuousWorld(scenario)
    world.reset(0)
    for message in scenario.initial_messages():
        world.say(message)
    prompts = []

    def generate(prompt):
        prompts.append(prompt)
        return json.dumps({"intent": "carry", "object_id": "missing",
                           "destination": "tray_blue", "speed_mps": 9})

    policy = QwenHumanPolicy(scenario, model_path="/tmp/no-model",
                             decision_interval_steps=10, generator=generate)
    output = policy.step(world.observe())

    assert output.command.intent == "observe"
    assert output.command.speed_mps == 0.65
    assert prompts and "human_targets" not in prompts[0]
    assert "robot_targets" not in prompts[0]
    assert "private" not in prompts[0]
    assert policy.audit_state()["inference_count"] == 1


def test_qwen_partner_reuses_decision_until_public_context_changes():
    scenario = CONTINUOUS_SCENARIOS["concurrent_overlay"]
    world = ContinuousWorld(scenario)
    world.reset(0)
    for message in scenario.initial_messages():
        world.say(message)
    calls = []

    def generate(prompt):
        calls.append(prompt)
        return '{"intent":"observe","message":""}'

    policy = QwenHumanPolicy(scenario, model_path="/tmp/no-model",
                             decision_interval_steps=10, generator=generate)
    first = world.observe()
    policy.step(first)
    policy.step(first)
    assert len(calls) == 1

    world.start_action(Action("transfer", "blue", "tray_blue"))
    policy.step(world.observe())
    assert len(calls) == 2


def test_qwen_partner_records_parse_errors_without_private_fallback():
    scenario = CONTINUOUS_SCENARIOS["relay"]
    world = ContinuousWorld(scenario)
    world.reset(0)
    policy = QwenHumanPolicy(scenario, model_path="/tmp/no-model",
                             generator=lambda _: "not json")
    output = policy.step(world.observe())
    assert output.command.intent == "observe"
    record = policy.audit_state()["policy_io"][0]
    assert record["parse_error"]
    assert record["parsed_decision"]["intent"] == "observe"


def test_qwen_own_message_does_not_trigger_self_conversation_loop():
    scenario = CONTINUOUS_SCENARIOS["concurrent_overlay"]
    world = ContinuousWorld(scenario)
    world.reset(0)
    calls = []
    policy = QwenHumanPolicy(scenario, model_path="/tmp/no-model", persona_id="independent",
                             generator=lambda prompt: calls.append(prompt) or
                             '{"intent":"observe","message":"我在观察"}')
    first = policy.step(world.observe())
    for message in first.messages:
        world.say(message)
    policy.step(world.observe())
    assert len(calls) == 1
    world.say(Message("robot", "request_help", "请帮忙", "blue"))
    policy.step(world.observe())
    assert len(calls) == 2
    assert policy.persona_id == "independent"
