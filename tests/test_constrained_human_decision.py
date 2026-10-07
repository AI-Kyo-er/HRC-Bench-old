import json

import pytest

from hrc_pilot.constrained_human_decision import PREFIX,decision_json_schema,parse_constrained_decision,ConstrainedHumanDecisionPolicy
from hrc_pilot.joint_activity import ACTIVITIES


def scene():
    return {'time_s':0.,'objects_xyz':{'wine':[]},'regions_xyz':{'wine_home':[],'staging':[],'wine_on_cabinet':[]},
        'own_execution':{'held_object':None,'phase':'idle'},'measured_world':{},
        'public_dialogue':[],'private_context':[],'action_interface':{}}


def accepts(schema,value):
    parser=pytest.importorskip('lmformatenforcer').JsonSchemaParser(schema)
    for char in json.dumps(value):
        if char not in parser.get_allowed_characters():return False
        parser=parser.add_character(char)
    return parser.can_end()


def call(motion,speech=None):return {'name':'choose_human_contribution','arguments':{'contribution':motion,'communication':speech}}


def test_type_constraints_keep_all_strategy_choices_but_exclude_misplaced_finish_and_unknown_targets():
    schema=decision_json_schema(scene())
    for motion in [None,{'kind':'pause_current'},{'kind':'wait'},{'kind':'step_aside'},{'kind':'return_to_work'},
                   {'kind':'hold_object','object_id':'wine'},{'kind':'indicate_object','object_id':'wine'},
                   {'kind':'place_object','object_id':'wine','destination':'staging'},
                   {'kind':'place_object','object_id':'wine','destination':'wine_on_cabinet'}]:
        assert accepts(schema,call(motion,{'kind':'finish','text':'My part is finished.'}))
    assert not accepts(schema,call({'kind':'finish'}))
    assert not accepts(schema,call({'kind':'place_object','object_id':'wine','destination':'wine_home'}))
    assert not accepts(schema,call({'kind':'place_object','destination':'staging'}))


def test_explicit_pause_preserves_selected_words_and_does_not_declare_shared_task_done():
    raw=PREFIX+json.dumps(call({'kind':'pause_current'},{'kind':'proposal','text':'I will stop my movement; can you take over after I release it?'}))+'\n</tool_call>'
    choice,normalization,original=parse_constrained_decision(raw,scene())
    assert choice['action']=='pause_current' and choice['message']==original['arguments']['communication']['text']
    assert normalization['contribution_kind']=='pause_current' and 'task_success' not in choice


def test_actual_model_payload_offers_one_consistent_target_menu_and_records_decoder_boundary():
    inputs=[]
    def generate(value):inputs.append(json.loads(value));return PREFIX+json.dumps(call(None,{'kind':'reject','text':'I need to keep it.'}))+'\n</tool_call>'
    human=ConstrainedHumanDecisionPolicy(ACTIVITIES['drink_storage'],model_path='/unused',generator=generate)
    row=human.decide(scene())
    assert row['parse_error'] is None and row['choice_schema_version']==9
    assert row['private_input']==json.loads(inputs[0]['messages'][-1]['content'])
    assert 'wine_home' not in row['private_input']['scene']['named_destinations']
    assert row['generation_thinking'] is False and row['caller_prefix']==PREFIX
