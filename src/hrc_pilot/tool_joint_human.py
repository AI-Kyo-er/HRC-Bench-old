"""原生工具调用的人策略：历史选择与随后测得的执行结果分开。"""
from copy import deepcopy
from hashlib import sha256
import json
import re
import time

from .human_contribution_contract import contribution_interface,parse_contribution
from .intent_observation import intent_observation
from .joint_activity import PROFILES
from .reasoning_joint_human import ReasoningJointHumanPolicy


TOOL_NAME='choose_human_contribution'


def retained_private_notes(history):
    return [{'decision_id':d['decision_id'],'time_s':d['time_s'],'note':d['choice']['memory']}
            for d in history if d['choice'].get('memory')][-6:]


def contribution_tool(scene):
    return {'type':'function','function':{'name':TOOL_NAME,
        'description':'Select one current human contribution and optional public speech. Selection and acceptance are not motion completion. Actual execution observations are returned at the next decision.',
        'parameters':{'type':'object','properties':{
            'action':{'type':'string','enum':['pick','place','relocate','point','move_hand','away','return','wait','message']},
            'object_id':{'enum':[None,*scene['objects_xyz']]},
            'destination':{'enum':[None,*scene['regions_xyz']]},
            'target_xyz':{'type':['array','null'],'items':{'type':'number'},'minItems':3,'maxItems':3},
            'presence_choice':{'type':'string','enum':['keep','step_aside','return_to_work']},
            **{k:{'type':'string'} for k in ['intention','participation','reason']},
            'message':{'type':['string','null']},
            'message_kind':{'enum':[None,'proposal','accept','reject','update','request','notice']},
            'memory':{'type':['string','null'],'description':'Optional private note; a recollection or intention is not a measured execution fact.'},
        },'required':['action'],'additionalProperties':False}}}


def parse_tool_choice(raw,objects,regions):
    final=raw.rsplit('</think>',1)[-1]
    calls=re.findall(r'<tool_call>\s*(.*?)\s*</tool_call>',final,re.S)
    if len(calls)!=1:raise ValueError('必须选择一个完整的当前贡献工具调用')
    value=json.loads(calls[0])
    if value.get('name')!=TOOL_NAME:raise ValueError('所选工具不存在')
    arguments=value.get('arguments')
    if not isinstance(arguments,dict):raise ValueError('贡献工具参数必须为对象')
    choice,normalization=parse_contribution(json.dumps(arguments,ensure_ascii=False),objects,regions,schema_version=5)
    return choice,normalization,value


def execution_tool_result(decision_id,scene):
    execution=scene['own_execution'];receipt=execution.get('last_receipt') or {}
    result={'policy_decision_id':decision_id,'observed_at_s':scene['time_s'],
        'acceptance':receipt.get('accepted') if receipt.get('request_id')==decision_id else None,
        'completed_request_ids':list(execution.get('completed_requests',[])),
        'active_motion_request_id':execution.get('active_request_id'),
        'held_object':execution['held_object'],'phase':execution['phase'],
        'last_execution_error':receipt.get('error'),
        'measured_current_facts':list(scene['measured_world'].get('current_measured_fact_sentences',[])),
        'interpretation':'Actual observations after a policy selection. Acceptance is not completion; no task score, future cue, or prescribed next action.'}
    if 'cancelled_requests' in execution:result['cancelled_request_ids']=list(execution['cancelled_requests'])
    return result


def tool_model_input(system,request,history,scene):
    messages=[{'role':'system','content':system}]
    for index in range(max(0,len(history)-4),len(history)):
        turn=history[index]
        messages.append({'role':'user','content':json.dumps(turn['private_input'],ensure_ascii=False,separators=(',',':'))})
        call=turn['selected_tool_call']
        if call is None:messages.append({'role':'assistant','content':turn['raw_output']})
        else:
            messages.append({'role':'assistant','content':'','tool_calls':[{'type':'function',
                'function':{'name':TOOL_NAME,'arguments':call['arguments']}}]})
            next_scene=history[index+1]['observation_source_scene'] if index+1<len(history) else scene
            messages.append({'role':'tool','content':json.dumps(execution_tool_result(turn['decision_id'],next_scene),
                                                              ensure_ascii=False,separators=(',',':'))})
    messages.append({'role':'user','content':json.dumps(request,ensure_ascii=False,separators=(',',':'))})
    return {'messages':messages,'tools':[contribution_tool(scene)]}


class ToolJointHumanPolicy(ReasoningJointHumanPolicy):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if self.reflection:raise ValueError('原生工具人条件使用一次推理，不叠加旧反思条件')

    def _system_prompt(self):
        return (
            '你是与机械臂共同进行日常活动的人。依据自己的需要、参与意愿、当前实际场景和伙伴回应，'
            '自己决定一个当前贡献。你可以加入、暂离、返回、保留或修改用途、提出纠正、接管或拒绝请求。'
            '这些选择应有生活情境依据，不为了展示变化随机改目标。共同活动说明是可能贡献与依赖，不是动作队列。'
            '私人需要不会直接告诉机器人；必要时自己用简短英文message或实际行为表达、协商。'
            '只调用一次choose_human_contribution。参数中的意图、参与、对象、目标和话语由你选择。'
            'tool_response是真实执行反馈；自己的tool_call、旧消息、记忆和伙伴声明不是完成事实。'
            'own_retained_private_notes保留你此前自选的私人记忆，仍不是实测事实。'
            '动作可以持续多个决策周期；wait和message保留正在执行的运动，不能凭上一轮选择宣布已经完成。'
            '当前单手代理的point或move_hand会改变手的当前运动，持物不自动释放。'
            'relocate连续完成你已选的一次取放及退手，可在接口允许时先暂放原持物；不自动选择下一任务。'
            'return_to_work可配合relocate接近工作区；step_aside不能同时搬物。'
            'human_contribution_interface列出真实能力与目标含义，不支持的需求可以协商，不编造完成。'
            '无需每次说话，不必生成重复记忆。重要的是按当前实际状态和新的需要考虑是否继续、改变或结束安排。')

    def _generate_tool(self,payload):
        if self.generator is not None:return self.generator(json.dumps(payload,ensure_ascii=False))
        self._load_model()
        import torch
        encoded=self._tokenizer.apply_chat_template(payload['messages'],tools=payload['tools'],
            tokenize=True,add_generation_prompt=True,enable_thinking=True,return_tensors='pt')
        encoded=encoded.to(self._model.device)
        ids=encoded['input_ids'] if hasattr(encoded,'keys') else encoded
        self._current_token_ids=ids[0].tolist()
        with torch.inference_mode():
            options={'max_new_tokens':self.generation_token_limit,'do_sample':True,'temperature':.45,
                     'top_p':.85,'pad_token_id':self._tokenizer.eos_token_id}
            if hasattr(encoded,'keys'):generated=self._model.generate(**encoded,**options)
            else:generated=self._model.generate(encoded,attention_mask=torch.ones_like(encoded),**options)
        return self._tokenizer.decode(generated[0,ids.shape[-1]:],skip_special_tokens=True).strip()

    def decide(self,scene):
        request={'agent_identity':{'self':'human','partner':'robot'},'activity':self.activity.public(),
            'personal_background':self.activity.private_background,'profile':PROFILES[self.profile],
            'scene':intent_observation(scene),'human_contribution_interface':contribution_interface(scene),
            'own_retained_private_notes':retained_private_notes(self.decisions)}
        payload=tool_model_input(self._system_prompt(),request,self.decisions,scene)
        started=time.perf_counter();raw=self._generate_tool(payload);error=None;normalization=None;call=None
        try:choice,normalization,call=parse_tool_choice(raw,scene['objects_xyz'],scene['regions_xyz'])
        except (ValueError,TypeError,KeyError) as exc:
            error=str(exc);choice={'action':'wait','message':'','message_kind':'notice',
                'intention':'','participation':'','reason':'工具调用非法，保留现场等待下一次人决策。','memory':''}
        row={'decision_id':len(self.decisions),'time_s':scene['time_s'],'system_prompt':self._system_prompt(),
            'private_input':request,'observation_source_scene':deepcopy(scene),'raw_output':raw,'choice':choice,
            'parse_error':error,'latency_s':time.perf_counter()-started,'action_source':'actual_qwen_native_tool_human',
            'candidate_raw_output':raw,'reflection_enabled':False,'reflection_input':None,'neural_inferences':1,
            'choice_schema_version':6,'human_observation_encoding':'intent_semantic_facts_v1',
            'human_contribution_contract':'explicit_parameter_domains_v1','contribution_normalization':normalization,
            'native_tool_model_input':deepcopy(payload),'native_tool_input_token_ids':getattr(self,'_current_token_ids',None),
            'selected_tool_call':call}
        if self._tokenizer is not None:
            template=self._tokenizer.chat_template
            row['chat_template_sha256']=sha256(template.encode()).hexdigest()
        self.decisions.append(row)
        return row
