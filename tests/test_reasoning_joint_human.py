from hrc_pilot.reasoning_joint_human import ReasoningJointHumanPolicy
from hrc_pilot.human_contribution_contract import parse_contribution


def test_actual_post_thinking_choice_is_preserved_and_not_replaced_by_a_teacher():
    raw='<think>I need the measured drawer to be accessible; the claim alone is insufficient.</think>{"action":"message","message_kind":"request","message":"Please check the drawer; it is still closed."}'
    choice,_=parse_contribution(raw,{}, {})
    assert choice['action']=='message' and choice['message']=='Please check the drawer; it is still closed.'
    assert ReasoningJointHumanPolicy.enable_thinking and ReasoningJointHumanPolicy.generation_token_limit==4096
