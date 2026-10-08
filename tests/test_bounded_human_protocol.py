import json

import pytest
from lmformatenforcer import JsonSchemaParser

from hrc_pilot.bounded_human_protocol import bounded_output_schema,failed_turn_history_content


def test_only_free_text_is_bounded_and_original_schema_is_preserved():
    schema={'type':'object','properties':{'object_id':{'type':'string','enum':['a'*600]},
        'reason':{'type':'string'},'memory':{'type':['string','null'],'maxLength':12}},
        'required':['object_id','reason']}
    bounded=bounded_output_schema(schema)
    assert bounded['properties']['object_id']==schema['properties']['object_id']
    assert bounded['properties']['reason']['maxLength']==512
    assert bounded['properties']['memory']['maxLength']==12
    assert 'maxLength' not in schema['properties']['reason']
    assert bounded['required']==schema['required']


def test_actual_incremental_parser_requires_quote_at_communication_limit():
    schema={'type':'object','properties':{'communication':{'anyOf':[{'type':'null'},
        {'type':'object','properties':{'text':{'type':'string'}}}]}}}
    parser=JsonSchemaParser(bounded_output_schema(schema))
    for char in '{"communication":{"text":"'+'a'*512:
        assert char in parser.get_allowed_characters();parser=parser.add_character(char)
    assert parser.get_allowed_characters()=='"'
    assert not parser.can_end()


def test_failed_history_describes_actual_fallback_and_does_not_republish_raw_text():
    row={'decision_id':4,'time_s':36.,'parse_error':'unterminated string',
         'selected_tool_call':None,'actual_generated_json':'private repeated draft'*1000,
         'choice':{'action':'wait','message':''}}
    content=failed_turn_history_content(row);value=json.loads(content)
    assert value['recorded_backend_fallback']=='wait' and not value['public_message_sent']
    assert 'private repeated draft' not in content
    row['parse_error']=None
    with pytest.raises(ValueError,match='生成失败'):failed_turn_history_content(row)
