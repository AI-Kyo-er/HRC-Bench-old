from copy import deepcopy
import json

import pytest

from hrc_pilot.constrained_human_decision import PREFIX,parse_constrained_decision
from hrc_pilot.human_output_verification import INVALID_TOOL_FALLBACK,verify_recorded_constrained_output


def failed_record():
    text='{"name":"choose_human_contribution","arguments":{"communication":{"text":"unfinished'
    raw=PREFIX+text+'\n</tool_call>'
    try:parse_constrained_decision(raw,{})
    except ValueError as error:message=str(error)
    return {'caller_prefix':PREFIX,'caller_suffix':'\n</tool_call>','raw_output':raw,
        'actual_generated_json':text,'parse_error':message,'choice':deepcopy(INVALID_TOOL_FALLBACK),
        'selected_tool_call':None,'contribution_normalization':None,'output_json_schema':{'type':'object'}}


def test_truncated_actual_generation_is_a_verified_failure_not_an_audit_crash():
    row=failed_record();before=deepcopy(row)
    result=verify_recorded_constrained_output(row,{})
    assert result['recorded_generation_failure'] and not result['policy_choice_valid']
    assert row==before


def test_wrong_failure_tag_or_emitted_message_is_rejected():
    row=failed_record();row['parse_error']='different error'
    with pytest.raises(ValueError,match='解析错误'):verify_recorded_constrained_output(row,{})
    row=failed_record();row['choice']['message']='Correction that was never sent.'
    with pytest.raises(ValueError,match='回退'):verify_recorded_constrained_output(row,{})


def test_invalid_json_cannot_be_recorded_as_success():
    row=failed_record();row['parse_error']=None
    with pytest.raises(json.JSONDecodeError):verify_recorded_constrained_output(row,{})
