from copy import deepcopy
import json

import pytest

from hrc_pilot.bounded_human_protocol import TEXT_LIMITS
from hrc_pilot.bounded_human_runtime import (
    PROTOCOL,HISTORY_ENCODING,protocol_enabled,failure_aware_tool_payload,
    failure_aware_agenda_request,bounded_runtime_overrides)


def failed():
    return {'decision_id':2,'time_s':36.,'raw_output':'malformed private draft'*100,
        'parse_error':'Unterminated string','selected_tool_call':None,
        'choice':{'action':'wait','message':''}}


def test_only_failed_assistant_history_changes_and_public_channel_remains_exact():
    row=failed();payload={'messages':[{'role':'user','content':'actual private observation'},
        {'role':'assistant','content':row['raw_output']},{'role':'tool','content':'actual receipt'},
        {'role':'user','content':'current actual world'}],'tools':[{'unchanged':True}]}
    before=deepcopy(payload);result=failure_aware_tool_payload(payload,[row])
    assert payload==before and result['tools']==payload['tools']
    assert result['messages'][0]==payload['messages'][0] and result['messages'][2:]==payload['messages'][2:]
    assert not json.loads(result['messages'][1]['content'])['public_message_sent']
    with pytest.raises(ValueError,match='不对应'):
        failure_aware_tool_payload({'messages':[{'role':'assistant','content':'different'}]},[row])


def test_agenda_knows_wait_was_backend_fallback_without_changing_measured_feedback():
    row=failed();request={'recent_choices_and_actual_feedback':[{'decision_id':2,
        'chosen_contribution':row['choice'],'subsequent_measured_execution':{'held_object':'wine'}}]}
    before=deepcopy(request);result=failure_aware_agenda_request(request,[row])
    assert request==before
    assert result['recent_choices_and_actual_feedback'][0]['chosen_contribution']==row['choice']
    assert result['recent_choices_and_actual_feedback'][0]['contribution_generation_status']=='invalid_generation_backend_wait'
    assert result['recent_choices_and_actual_feedback'][0]['subsequent_measured_execution']=={'held_object':'wine'}


def test_protocol_marker_must_be_complete_and_legacy_has_no_changes():
    assert not protocol_enabled({})
    assert protocol_enabled({'human_output_protocol':PROTOCOL,'human_failed_history_encoding':HISTORY_ENCODING,
        'human_text_limits':TEXT_LIMITS})
    with pytest.raises(ValueError,match='不完整'):protocol_enabled({'human_output_protocol':PROTOCOL})


def test_local_overrides_restore_original_functions_after_error():
    import hrc_pilot.reasoning_constrained_human as reasoning
    import hrc_pilot.tool_joint_human as tools
    import hrc_pilot.private_agenda_human as agenda
    originals=(reasoning.constrained_tool,reasoning.decision_json_schema,tools.tool_model_input,agenda.agenda_request)
    with pytest.raises(RuntimeError):
        with bounded_runtime_overrides():
            assert reasoning.constrained_tool is not originals[0]
            raise RuntimeError('stop this independent run')
    assert (reasoning.constrained_tool,reasoning.decision_json_schema,tools.tool_model_input,agenda.agenda_request)==originals


def test_two_stage_policy_receives_failure_fact_and_retains_its_actual_next_choice():
    from hrc_pilot.private_agenda_human import PrivateAgendaHumanPolicy
    from hrc_pilot.constrained_human_decision import PREFIX
    from hrc_pilot.joint_activity import ACTIVITIES
    from test_constrained_human_decision import scene
    from test_private_agenda_human import agenda
    inputs=[];agenda_inputs=[]
    outputs=iter([PREFIX+'{"name":"choose_human_contribution","arguments":{"communication":{"text":"unfinished\n</tool_call>',
        PREFIX+json.dumps({'name':'choose_human_contribution','arguments':{'contribution':None,
            'communication':{'kind':'reject','text':'Keep the bottle here for immediate use.'}}})+'\n</tool_call>'])
    def act(payload):inputs.append(json.loads(payload));return next(outputs)
    def intent(payload):agenda_inputs.append(payload);return json.dumps(agenda('Keep the bottle available.'))
    policy=PrivateAgendaHumanPolicy(ACTIVITIES['drink_storage'],model_path='/unused',
        generator=act,agenda_generator=intent)
    with bounded_runtime_overrides():
        first=policy.decide(scene());current=scene();current['time_s']=4;second=policy.decide(current)
    assert first['parse_error'] is not None and first['choice']['message']==''
    history=json.loads(agenda_inputs[-1]['messages'][-1]['content'])['recent_choices_and_actual_feedback'][0]
    assert history['contribution_generation_status']=='invalid_generation_backend_wait'
    assistant=next(m for m in inputs[-1]['messages'] if m['role']=='assistant')
    assert json.loads(assistant['content'])['public_message_sent'] is False
    assert second['choice']['message_kind']=='reject' and second['choice']['message']=='Keep the bottle here for immediate use.'
    assert inputs[-1]['tools'][0]['function']['parameters']['properties']['reason']['maxLength']==512


def test_runtime_rejects_valid_json_that_violates_declared_text_limit():
    from hrc_pilot.private_agenda_human import PrivateAgendaHumanPolicy
    from hrc_pilot.constrained_human_decision import PREFIX
    from hrc_pilot.joint_activity import ACTIVITIES
    from hrc_pilot.human_output_verification import verify_recorded_constrained_output
    from test_constrained_human_decision import scene
    from test_private_agenda_human import agenda
    raw=PREFIX+json.dumps({'name':'choose_human_contribution','arguments':{'contribution':None,
        'communication':{'kind':'notice','text':'a'*513}}})+'\n</tool_call>'
    policy=PrivateAgendaHumanPolicy(ACTIVITIES['drink_storage'],model_path='/unused',
        generator=lambda payload:raw,agenda_generator=lambda payload:json.dumps(agenda('Keep bottle.')))
    with bounded_runtime_overrides():row=policy.decide(scene())
    assert row['parse_error'] is not None and row['choice']['message']==''
    # 注入测试生成器不产生token/JSON证据，这里只为验证独立错误重放补实际生成文本。
    row['actual_generated_json']=raw[len(PREFIX):-len('\n</tool_call>')]
    assert verify_recorded_constrained_output(row,scene())['recorded_generation_failure']
