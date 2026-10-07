import json

import pytest

from hrc_pilot.human_decision_interface import parse_decision
from hrc_pilot.human_decision_policy import HumanDecisionPolicy
from hrc_pilot.joint_activity import ACTIVITIES


def call(arguments):return '<tool_call>'+json.dumps({'name':'choose_human_contribution','arguments':arguments})+'</tool_call>'


def scene():
    return {'time_s':0.,'objects_xyz':{'wine':[]},'regions_xyz':{'wine_home':[],'staging':[],'wine_on_cabinet':[]},
        'own_execution':{'held_object':None,'phase':'idle'},'measured_world':{},
        'public_dialogue':[],'private_context':[],'action_interface':{}}


def test_putting_a_free_object_is_one_selected_contribution_not_a_required_pick_place_sequence():
    args={'contribution':{'kind':'place_object','object_id':'wine','destination':'wine_on_cabinet'},'communication':None}
    choice,norm,raw=parse_decision(call(args),scene())
    assert choice['action']=='relocate' and choice['object_id']=='wine' and choice['destination']=='wine_on_cabinet'
    assert norm['contribution_kind']=='place_object' and raw['arguments']==args
    with pytest.raises(ValueError):parse_decision(call({**args,'contribution':{**args['contribution'],'destination':'wine_home'}}),scene())


def test_accept_and_finish_are_public_speech_without_physical_or_shared_success_labels():
    for kind in ['accept','finish']:
        choice,normalization,_=parse_decision(call({'contribution':None,'communication':{'kind':kind,'text':'I consider my part finished.'}}),scene())
        assert choice['action']=='wait' and choice['message']=='I consider my part finished.'
        assert normalization['communication_kind']==kind and 'task_success' not in choice
    with pytest.raises(ValueError):parse_decision(call({'contribution':None,'communication':{'kind':'accept','text':'yes','private_need':'secret'}}),scene())


def test_actual_neural_payload_uses_natural_targets_and_preserves_private_selected_intent():
    inputs=[]
    def generate(payload):
        inputs.append(json.loads(payload))
        return call({'contribution':None,'communication':{'kind':'reject','text':'I need to keep this bottle.'},'intention':'Keep my bottle available.'})
    human=HumanDecisionPolicy(ACTIVITIES['drink_storage'],model_path='/unused',generator=generate)
    row=human.decide(scene())
    assert row['parse_error'] is None and row['choice_schema_version']==8
    assert row['private_input']==json.loads(inputs[0]['messages'][-1]['content'])
    assert 'human_contribution_interface' not in row['private_input']
    ids=[d['destination_id'] for d in row['private_input']['human_decision_interface']['destination_choices']]
    assert 'wine_home' not in ids and 'wine_on_cabinet' in ids
    assert row['choice']['message_kind']=='reject' and row['choice']['intention']=='Keep my bottle available.'
