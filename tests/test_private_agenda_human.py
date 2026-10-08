import json

import pytest

from hrc_pilot.private_agenda_human import PrivateAgendaHumanPolicy,parse_agenda
from hrc_pilot.constrained_human_decision import PREFIX
from hrc_pilot.joint_activity import ACTIVITIES
from test_constrained_human_decision import scene


def agenda(need):
    return {'current_need':need,'current_intention':'Keep the shared activity usable.',
            'participation_preference':'Decide based on partner availability.',
            'understood_shared_arrangement':'Not yet mutually confirmed.',
            'unresolved_needs':[need],'update_reason':'Based on current observation.',
            'private_memory':['Partner claims are not completion facts.']}


def test_private_agenda_persists_and_actual_current_contribution_remains_neural_choice():
    agenda_inputs=[];action_inputs=[];needs=iter(['Keep bottle for visitor.','Return to snack after visitor cancellation.'])
    def propose(payload):agenda_inputs.append(payload);return json.dumps(agenda(next(needs)))
    def act(payload):
        action_inputs.append(json.loads(payload))
        return PREFIX+json.dumps({'name':'choose_human_contribution','arguments':{
            'contribution':{'kind':'wait'},'communication':{'kind':'reject','text':'I need to keep this bottle.'}}})+'\n</tool_call>'
    human=PrivateAgendaHumanPolicy(ACTIVITIES['drink_storage'],model_path='/unused',generator=act,agenda_generator=propose)
    first=human.decide(scene());second_scene=scene();second_scene['time_s']=4;second=human.decide(second_scene)
    last=json.loads(action_inputs[-1]['messages'][-1]['content'])
    assert last['self_generated_private_agenda']==agenda('Return to snack after visitor cancellation.')
    assert json.loads(agenda_inputs[-1]['messages'][-1]['content'])['previous_self_generated_private_agenda']==agenda('Keep bottle for visitor.')
    assert second['choice']['action']=='wait' and second['choice']['message_kind']=='reject'
    assert first['neural_inferences']==second['neural_inferences']==2
    assert second['private_agenda_inference']['request']['recent_choices_and_actual_feedback'][0]['decision_id']==0
    assert second['private_agenda_inference']['request']['recent_choices_and_actual_feedback'][0]['subsequent_measured_execution']['observed_at_s']==4
    assert not {'next_action','task_success','score'}.intersection(last['self_generated_private_agenda'])


def test_invalid_agenda_cannot_silently_create_a_task_or_replace_previous_neural_intent():
    proposals=iter([json.dumps(agenda('Keep wine.')),'{}'])
    def act(payload):return PREFIX+json.dumps({'name':'choose_human_contribution','arguments':{
        'contribution':None,'communication':None}})+'\n</tool_call>'
    human=PrivateAgendaHumanPolicy(ACTIVITIES['drink_storage'],model_path='/unused',generator=act,
                                  agenda_generator=lambda payload:next(proposals))
    human.decide(scene());row=human.decide(scene())
    assert row['private_agenda_inference']['parse_error'] is not None
    assert row['private_agenda_inference']['agenda_after']==agenda('Keep wine.')
    assert row['private_input']['private_agenda_status']=='agenda_generation_invalid_previous_interpretation_retained'
    assert row['choice']['action']=='wait'


def test_agenda_schema_does_not_accept_a_background_action_queue():
    proposed=agenda('Finish snack.');proposed['next_action']='pick bowl'
    with pytest.raises(ValueError):parse_agenda(json.dumps(proposed))


def test_actual_decoder_accepts_the_private_intent_schema_without_adding_actions():
    from lmformatenforcer import JsonSchemaParser
    from hrc_pilot.private_agenda_human import AGENDA_SCHEMA
    parser=JsonSchemaParser(AGENDA_SCHEMA)
    for char in json.dumps(agenda('Respect the visitor request.'),ensure_ascii=False):
        assert char in parser.get_allowed_characters()
        parser=parser.add_character(char)
    assert parser.can_end()


def test_factual_history_keeps_coordinates_contacts_ownership_and_current_full_relations():
    from hrc_pilot.private_agenda_human import compact_action_history
    from hrc_pilot.public_scene_measurements import public_scene_measurements
    from test_public_scene_measurements import record
    measured=public_scene_measurements(record(),['cream','bowl'])
    old={'agent_identity':{'self':'human','partner':'robot'},'scene':{'time_s':0,
         'private_context':[],'public_partner_statements_not_execution_facts':[],
         'measured_scene_geometry_and_contact':measured},'self_generated_private_agenda':agenda('Prepare snack.')}
    payload={'messages':[{'role':'user','content':json.dumps(old)},
        {'role':'tool','content':json.dumps({'phase':'idle','held_object':'bowl',
            'measured_scene_geometry_and_contact':measured})},
        {'role':'user','content':json.dumps(old)}]}
    result=compact_action_history(payload)
    history=json.loads(result['messages'][0]['content'])
    feedback=json.loads(result['messages'][1]['content'])
    current=json.loads(result['messages'][2]['content'])
    assert history['historical_time_s']==0 and history['self_generated_private_agenda']==agenda('Prepare snack.')
    assert feedback['measured_scene_geometry_and_contact']['objects']==measured['objects']
    assert 'relative_object_measurements' not in feedback['measured_scene_geometry_and_contact']
    assert current['scene']['measured_scene_geometry_and_contact']==measured
    assert 'relative_object_measurements' in json.loads(payload['messages'][1]['content'])['measured_scene_geometry_and_contact']
