from copy import deepcopy
import json
from pathlib import Path

import pytest

from hrc_pilot.joint_activity import ACTIVITIES
from hrc_pilot.tool_joint_human import ToolJointHumanPolicy,parse_tool_choice


def test_native_tools_keep_neural_choice_and_return_pending_motion_as_actual_feedback():
    inputs=[]
    outputs=iter([
        '<think>A tool example is not my final selection.</think><tool_call>{"name":"choose_human_contribution","arguments":{"action":"relocate","object_id":"wine","destination":"staging","message":"Placing the bottle."}}</tool_call>',
        '<tool_call>{"name":"choose_human_contribution","arguments":{"action":"message","message":"I need it for immediate use; please hold."}}</tool_call>'])
    def generate(payload):inputs.append(json.loads(payload));return next(outputs)
    human=ToolJointHumanPolicy(ACTIVITIES['drink_storage'],model_path='/unused',generator=generate)
    scene={'time_s':0.,'objects_xyz':{'wine':[0,0,1]},'regions_xyz':{'staging':[0,0,1]},
        'own_execution':{'held_object':'wine','phase':'idle','completed_requests':[]},
        'measured_world':{'current_measured_fact_sentences':['Human is holding wine.']},
        'public_dialogue':[],'private_context':[],'action_interface':{}}
    first=human.decide(scene)
    assert first['choice']['action']=='relocate' and first['choice_schema_version']==6
    later=deepcopy(scene);later['time_s']=4.
    later['own_execution'].update(phase='transfer_raise',active_request_id=0,
        last_receipt={'request_id':0,'accepted':True,'error':None})
    later['private_context']=[{'time_s':4.,'text':'The visitor needs the bottle now.'}]
    second=human.decide(later)
    reply=json.loads(next(m['content'] for m in inputs[1]['messages'] if m['role']=='tool'))
    assert reply['acceptance'] is True and reply['held_object']=='wine'
    assert reply['phase']=='transfer_raise' and reply['completed_request_ids']==[]
    assert reply['active_motion_request_id']==0 and 'next_action' not in reply
    assert json.loads(inputs[1]['messages'][-1]['content'])==second['private_input']
    assert inputs[1]==second['native_tool_model_input']
    assert second['choice']['message']=='I need it for immediate use; please hold.'
    assert scene['own_execution']['phase']=='idle'


def test_tool_parser_rejects_multiple_or_unsupported_calls_without_inventing_an_action():
    one='<tool_call>{"name":"choose_human_contribution","arguments":{"action":"wait"}}</tool_call>'
    assert parse_tool_choice('<think>'+one+'</think>'+one,{}, {})[0]['action']=='wait'
    for raw in [one+one,one.replace('choose_human_contribution','teacher'),one.replace('wait','finish_robot_task')]:
        with pytest.raises(ValueError):parse_tool_choice(raw,{}, {})
    with pytest.raises(ValueError):parse_tool_choice(one.replace('"wait"','"relocate","object_id":"hidden","destination":"staging"'),{}, {'staging':[]})


def test_self_selected_private_note_survives_the_short_tool_window_without_becoming_world_truth():
    outputs=iter(['<tool_call>{"name":"choose_human_contribution","arguments":{"action":"wait","memory":"Keep the bottle available for the visitor."}}</tool_call>']+
                 ['<tool_call>{"name":"choose_human_contribution","arguments":{"action":"wait"}}</tool_call>']*6)
    human=ToolJointHumanPolicy(ACTIVITIES['drink_storage'],model_path='/unused',generator=lambda _:next(outputs))
    scene={'time_s':0.,'objects_xyz':{},'regions_xyz':{},'own_execution':{'held_object':None,'phase':'idle'},
           'measured_world':{},'public_dialogue':[],'private_context':[],'action_interface':{}}
    for i in range(7):row=human.decide({**scene,'time_s':i*4.})
    notes=row['private_input']['own_retained_private_notes']
    assert notes==[{'decision_id':0,'time_s':0.,'note':'Keep the bottle available for the visitor.'}]
    assert row['private_input']['scene']['measured_current_facts']==[]
    assert min(json.loads(m['content'])['scene']['time_s'] for m in row['native_tool_model_input']['messages']
               if m['role']=='user')==8.


def test_local_qwen_native_template_encodes_the_actual_tool_exchange():
    model=Path('/data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B')
    if not (model/'tokenizer_config.json').is_file():pytest.skip('本地Qwen模板不可用')
    transformers=pytest.importorskip('transformers')
    tokenizer=transformers.AutoTokenizer.from_pretrained(model,local_files_only=True)
    messages=[{'role':'system','content':'Select your current contribution.'},
        {'role':'user','content':'Prepare the bottle.'},
        {'role':'assistant','content':'','tool_calls':[{'type':'function','function':{'name':'choose_human_contribution','arguments':{'action':'relocate'}}}]},
        {'role':'tool','content':'{"held_object":"wine","phase":"transfer_raise"}'},
        {'role':'user','content':'Current needs may change.'}]
    rendered=tokenizer.apply_chat_template(messages,tools=[{'type':'function','function':{'name':'choose_human_contribution','parameters':{'type':'object'}}}],
        tokenize=False,add_generation_prompt=True,enable_thinking=True)
    assert '<tool_response>\n{"held_object":"wine","phase":"transfer_raise"}' in rendered
    assert '<tool_call>' in rendered and rendered.endswith('<|im_start|>assistant\n')
    no_think=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
    assert no_think.endswith('<think>\n\n</think>\n\n')
