import json

import pytest

from hrc_pilot.joint_activity import ACTIVITIES
from hrc_pilot.structured_tool_joint_human import StructuredToolJointHumanPolicy,parse_structured_tool_choice
from hrc_pilot.tool_joint_human import parse_tool_choice


RAW='<tool_call>{"name":"choose_human_contribution","arguments":{"action":"place","destination":"staging","message":{"message":"I will place it here.","message_kind":"notice"}}}</tool_call>'


def test_observed_structured_speech_is_forwarded_without_reselecting_contribution_or_rewriting_history():
    with pytest.raises(ValueError):parse_tool_choice(RAW,{}, {'staging':[]})
    choice,normalization,call=parse_structured_tool_choice(RAW,{}, {'staging':[]})
    assert choice['action']=='place' and choice['destination']=='staging'
    assert choice['message']=='I will place it here.' and normalization['structured_public_speech']
    assert isinstance(call['arguments']['message'],dict)
    with pytest.raises(ValueError):parse_structured_tool_choice(RAW.replace('"message_kind":"notice"','"message_kind":"notice","memory":"private"'),{}, {'staging':[]})
    with pytest.raises(ValueError):parse_structured_tool_choice(RAW.replace('"action":"place"','"message_kind":"reject","action":"place"'),{}, {'staging':[]})


def test_repaired_choice_receives_real_tool_feedback_on_next_decision():
    payloads=[]
    def generate(payload):payloads.append(json.loads(payload));return RAW
    human=StructuredToolJointHumanPolicy(ACTIVITIES['drink_storage'],model_path='/unused',generator=generate)
    scene={'time_s':0.,'objects_xyz':{'wine':[]},'regions_xyz':{'staging':[]},
        'own_execution':{'held_object':'wine','phase':'idle'},'measured_world':{},
        'public_dialogue':[],'private_context':[],'action_interface':{}}
    first=human.decide(scene)
    assert first['parse_error'] is None and first['choice_schema_version']==7
    second=human.decide({**scene,'time_s':4.})
    assert second['native_tool_model_input']==payloads[1]
    assert json.loads(payloads[1]['messages'][-1]['content'])==second['private_input']
    assert second['private_input']['human_measured_object_contacts']=={}
    assert any(m['role']=='tool' for m in payloads[1]['messages'])
    assert 'anyOf' in payloads[1]['tools'][0]['function']['parameters']['properties']['message']
