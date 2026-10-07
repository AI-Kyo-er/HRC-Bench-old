"""接受明确结构化的公开话语；不重选神经人的动作、物品或目标。"""
from copy import deepcopy
import json
import re

from .human_contribution_contract import parse_contribution
from .tool_joint_human import TOOL_NAME,ToolJointHumanPolicy


def structured_speech_payload(payload):
    actual=deepcopy(payload)
    properties=actual['tools'][0]['function']['parameters']['properties']
    properties['message']={'anyOf':[{'type':['string','null']},
        {'type':'object','properties':{'message':{'type':['string','null']},
            'message_kind':deepcopy(properties['message_kind'])},'required':['message'],'additionalProperties':False}]}
    return actual


def parse_structured_tool_choice(raw,objects,regions):
    calls=re.findall(r'<tool_call>\s*(.*?)\s*</tool_call>',raw.rsplit('</think>',1)[-1],re.S)
    if len(calls)!=1:raise ValueError('必须选择一个完整的当前贡献工具调用')
    call=json.loads(calls[0])
    if call.get('name')!=TOOL_NAME or not isinstance(call.get('arguments'),dict):raise ValueError('非法贡献工具调用')
    arguments=deepcopy(call['arguments']);speech=arguments.get('message');nested=isinstance(speech,dict)
    if nested:
        if 'message' not in speech or set(speech)-{'message','message_kind'}:
            raise ValueError('结构化公开话语包含未知字段')
        if not isinstance(speech['message'],(str,type(None))):raise ValueError('结构化公开话语须为文字或空')
        if 'message_kind' in speech:
            if arguments.get('message_kind') is not None and arguments['message_kind']!=speech['message_kind']:
                raise ValueError('内外公开话语类型冲突')
            arguments['message_kind']=speech['message_kind']
        arguments['message']=speech['message']
    choice,normalization=parse_contribution(json.dumps(arguments,ensure_ascii=False),objects,regions,schema_version=5)
    normalization['structured_public_speech']=nested
    return choice,normalization,call


class StructuredToolJointHumanPolicy(ToolJointHumanPolicy):
    def _system_prompt(self):
        return super()._system_prompt()+'message可为直接文字，也可为含message和message_kind的公开话语对象；不要混入私人记忆或原因。'

    def _generate_tool(self,payload):
        actual=structured_speech_payload(payload)
        payload['tools']=actual['tools']
        request=json.loads(payload['messages'][-1]['content'])
        request['human_measured_object_contacts']=deepcopy(self._current_source_scene['measured_world'].get('object_contacts',{}))
        payload['messages'][-1]['content']=json.dumps(request,ensure_ascii=False,separators=(',',':'))
        return super()._generate_tool(payload)

    def decide(self,scene):
        self._current_source_scene=scene
        row=super().decide(scene)
        row['private_input']=json.loads(row['native_tool_model_input']['messages'][-1]['content'])
        try:
            choice,normalization,call=parse_structured_tool_choice(row['raw_output'],scene['objects_xyz'],scene['regions_xyz'])
        except (ValueError,TypeError,KeyError) as error:
            row['parse_error']=str(error)
        else:
            row.update(choice=choice,parse_error=None,contribution_normalization=normalization,selected_tool_call=call)
        row['choice_schema_version']=7
        return row
