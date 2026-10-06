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


def test_model_generated_memory_and_real_timestamps_enter_next_human_decision():
    scenario = CONTINUOUS_SCENARIOS["concurrent_overlay"]
    world = ContinuousWorld(scenario)
    world.reset(0)
    prompts = []
    policy = QwenHumanPolicy(scenario, model_path="/tmp/no-model", decision_interval_steps=1,
                             generator=lambda prompt: prompts.append(prompt) or
                             '{"intent":"observe","memory_note":"机器人尚未移动红物体。","reason":"先观察"}')
    policy.step(world.observe())
    world.tick()
    policy.step(world.observe())
    assert "机器人尚未移动红物体" in prompts[-1]
    assert '"time_s":0.0' in prompts[-1]
    assert len(policy.audit_state()["memory"]) == 2
    assert "trust" not in prompts[-1]


def test_public_assignment_survives_dialogue_window_and_reassignment_updates_it():
    scenario = CONTINUOUS_SCENARIOS["relay"]
    world = ContinuousWorld(scenario)
    for message in scenario.initial_messages():
        world.say(message)
    prompts = []
    policy = QwenHumanPolicy(scenario, model_path="/tmp/no-model", generator=lambda prompt: prompts.append(prompt) or
                             '{"intent":"observe","current_goal":"先完成公开承诺。"}')
    policy.step(world.observe())
    for index in range(20):
        world.say(Message("human", "policy_message", f"观察进度{index}"))
    policy.step(world.observe())
    value = json.loads(prompts[-1].split("\n", 1)[1])
    assert not any(row['kind'] == 'assignment' for row in value['public_dialogue'])
    board = {row['object_id']: row for row in value['persistent_public_task_board']}
    assert board['red']['assigned_role'] == 'human'
    assert board['blue']['assigned_role'] == 'robot'
    assert value['your_current_generated_goal'] == '先完成公开承诺。'
    world.say(Message("human", "reassignment", "我接管蓝块", "blue", "human", "tray_blue"))
    policy.step(world.observe())
    board = {row['object_id']: row for row in policy.audit_state()['public_task_board']}
    assert board['blue']['assigned_role'] == 'human'


def test_session_memory_is_separated_from_current_world_and_goal():
    scenario = CONTINUOUS_SCENARIOS["relay"]
    world = ContinuousWorld(scenario)
    prompts = []
    policy = QwenHumanPolicy(scenario, model_path="/tmp/no-model", memory_scope="session",
                             generator=lambda prompt: prompts.append(prompt) or
                             '{"intent":"observe","memory_note":"上次蓝块未完成","current_goal":"完成现在的公开任务"}')
    policy.step(world.observe())
    previous_id = policy.audit_state()['memory'][0]['memory_id']
    previous_persona = policy.persona_id
    policy.reset(2)
    assert policy.persona_id == previous_persona
    policy.step(world.observe())
    value = json.loads(prompts[-1].split("\n", 1)[1])
    assert value['your_personal_experience_memory'] == []
    assert value['your_current_generated_goal'] == ''
    assert value['your_previous_activity_experiences'][0]['memory_id'] == previous_id
    assert policy.audit_state()['memory_retrievals'][0]['previous_activity_memory_ids'] == [previous_id]
