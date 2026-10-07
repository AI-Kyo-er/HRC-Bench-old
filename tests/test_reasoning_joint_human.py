from hrc_pilot.reasoning_joint_human import ReasoningJointHumanPolicy
from hrc_pilot.human_contribution_contract import parse_contribution
from hrc_pilot.joint_activity import ACTIVITIES


def test_actual_post_thinking_choice_is_preserved_and_not_replaced_by_a_teacher():
    raw='<think>I need the measured drawer to be accessible; the claim alone is insufficient.</think>{"action":"message","message_kind":"request","message":"Please check the drawer; it is still closed."}'
    choice,_=parse_contribution(raw,{}, {})
    assert choice['action']=='message' and choice['message']=='Please check the drawer; it is still closed.'
    assert ReasoningJointHumanPolicy.enable_thinking and ReasoningJointHumanPolicy.generation_token_limit==4096


def test_actual_reasoning_output_return_and_relocation_is_retained_in_versioned_record():
    raw='<think>Return to contribute.</think>{"presence_choice":"return_to_work","action":"relocate","object_id":"cream","destination":"drawer","message":null}'
    human=ReasoningJointHumanPolicy(ACTIVITIES['drawer_access'],model_path='/unused',generator=lambda _:raw)
    scene={'time_s':40.,'objects_xyz':{'cream':[0,0,1]},'regions_xyz':{'drawer':[0,0,1]},
        'own_execution':{'held_object':None,'phase':'idle'},'measured_world':{},
        'public_dialogue':[],'private_context':[],'action_interface':{}}
    row=human.decide(scene)
    assert row['parse_error'] is None and row['choice_schema_version']==5
    assert row['choice']['action']=='relocate' and row['choice']['destination']=='drawer'
    assert parse_contribution(raw,scene['objects_xyz'],scene['regions_xyz'],schema_version=5)[0]==row['choice']
