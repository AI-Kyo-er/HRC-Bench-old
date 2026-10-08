"""生成式私人需要／共同活动理解与当前贡献分开推理；不按状态选动作。"""
from copy import deepcopy
from hashlib import sha256
import json
import time

from .constrained_human_decision import constrained_interface
from .intent_observation import intent_observation
from .joint_activity import PROFILES
from .reasoning_constrained_human import ReasoningConstrainedHumanPolicy
from .tool_joint_human import execution_tool_result


AGENDA_FIELDS=['current_need','current_intention','participation_preference',
               'understood_shared_arrangement','unresolved_needs','update_reason','private_memory']
AGENDA_SCHEMA={'type':'object','properties':{
    **{name:{'type':'string'} for name in AGENDA_FIELDS if name not in {'unresolved_needs','private_memory'}},
    'unresolved_needs':{'type':'array','items':{'type':'string'},'maxItems':5},
    'private_memory':{'type':'array','items':{'type':'string'},'maxItems':5}},
    'required':AGENDA_FIELDS,'additionalProperties':False}
AGENDA_SYSTEM=(
    '你是正在与机械臂共同活动的人。先更新自己的持续需要、当前意图、参与意愿和对公开约定的理解。'
    '根据个人背景、实际观察、自己的执行结果、伙伴公开回应和新的私人情境考虑保留或改变。'
    '前一意图与私人记忆是自己的解释，不是测量；伙伴说已完成也不等于已经完成。'
    '未解决的需要可以保留、暂缓或取消，变化应说明依据，不为了实验随机切换。'
    '这里不选择身体动作、动作队列或固定工作阶段。当前贡献稍后由独立推理选择。'
    '只输出JSON，包括current_need、current_intention、participation_preference、'
    'understood_shared_arrangement、unresolved_needs、update_reason、private_memory。'
    '理解不确定时明确说明不确定，不能编造私人事件或已经达成的约定。')


def compact_execution_feedback(feedback):
    """历史保留完整对象坐标／接触／持物；相对距离可由坐标恢复，不重复整张关系矩阵。"""
    result=deepcopy(feedback)
    measurement=result.get('measured_scene_geometry_and_contact')
    if measurement is not None:
        result['measured_scene_geometry_and_contact']={
            key:deepcopy(measurement[key]) for key in ['source','contact_measurement_available','objects','scope']}
    return result


def compact_action_history(payload):
    """本刻保留完整感知；历史用户上下文与随后真实执行反馈分开保留，不重复旧全场景。"""
    value=deepcopy(payload)
    for index,message in enumerate(value['messages']):
        if message['role']=='user' and index!=len(value['messages'])-1:
            old=json.loads(message['content'])
            context={'agent_identity':old['agent_identity'],'historical_time_s':old['scene']['time_s'],
                'private_context_at_that_time':old['scene']['private_context'],
                'public_partner_statements_at_that_time':old['scene']['public_partner_statements_not_execution_facts'],
                'self_generated_private_agenda':old.get('self_generated_private_agenda'),
                'scope':'历史需要／话语与自生成理解；随后的tool给实际反馈，本刻world不是这个历史快照。'}
            message['content']=json.dumps(context,ensure_ascii=False,separators=(',',':'))
        elif message['role']=='tool':
            message['content']=json.dumps(compact_execution_feedback(json.loads(message['content'])),
                                          ensure_ascii=False,separators=(',',':'))
    return value


def agenda_request(scene,activity,profile,previous,history):
    observed=intent_observation(scene)
    observed['public_partner_statements_not_execution_facts']=[m for m in scene['public_dialogue']
                                                               if m['speaker'] in {'human','robot'}]
    experiences=[]
    for i in range(max(0,len(history)-4),len(history)):
        row=history[i]
        next_scene=history[i+1]['observation_source_scene'] if i+1<len(history) else scene
        experiences.append({'decision_id':row['decision_id'],'time_s':row['time_s'],
            'chosen_contribution':deepcopy(row['choice']),
            'subsequent_measured_execution':compact_execution_feedback(execution_tool_result(row['decision_id'],next_scene))})
    return {'agent_identity':{'self':'human','partner':'robot'},'activity':activity.public(),
        'personal_background':activity.private_background,'profile':PROFILES[profile],
        'current_observation':observed,'previous_self_generated_private_agenda':deepcopy(previous),
        'recent_choices_and_actual_feedback':experiences,'available_human_contributions':constrained_interface(scene),
        'scope':'私人意图推理，不转发给机器人；不读取评分，不提供正确下一动作。'}


def parse_agenda(raw):
    value=json.loads(raw)
    from jsonschema import validate,ValidationError
    try:validate(value,AGENDA_SCHEMA)
    except ValidationError as error:raise ValueError(error.message) from error
    return value


class PrivateAgendaHumanPolicy(ReasoningConstrainedHumanPolicy):
    def __init__(self,*args,agenda_generator=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.agenda_generator=agenda_generator;self.private_agenda=None;self.agenda_inferences=[]

    def _system_prompt(self):
        return super()._system_prompt()+(
            'self_generated_private_agenda是自己刚生成的需要及活动理解，不是实际完成或伙伴认可的事实。'
            '依据当前测量核对这些理解，自己选择本刻应执行的贡献和公开表达。'
            '未来准备做的贡献不等于此刻应开始搬运；可以询问、暂停、继续或修正自己的理解。')

    def _generate_agenda(self,request):
        payload={'messages':[{'role':'system','content':AGENDA_SYSTEM},
            {'role':'user','content':json.dumps(request,ensure_ascii=False,separators=(',',':'))}]}
        if self.agenda_generator:
            raw=self.agenda_generator(deepcopy(payload))
            return {'model_input':payload,'raw_output':raw,'input_token_ids':None,'generated_token_ids':None,
                    'decoder':'injected_test_generator','generation_thinking':False}
        self._load_model()
        import torch
        from lmformatenforcer import JsonSchemaParser
        from lmformatenforcer.integrations.transformers import build_token_enforcer_tokenizer_data,build_transformers_prefix_allowed_tokens_fn
        ids=self._tokenizer.apply_chat_template(payload['messages'],tokenize=True,add_generation_prompt=True,
            enable_thinking=False,return_tensors='pt').to(self._model.device)
        if not hasattr(self,'_agenda_tokenizer_data'):
            self._agenda_tokenizer_data=build_token_enforcer_tokenizer_data(self._tokenizer)
        prefix=build_transformers_prefix_allowed_tokens_fn(self._agenda_tokenizer_data,JsonSchemaParser(AGENDA_SCHEMA))
        with torch.inference_mode():
            output=self._model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),max_new_tokens=1024,
                do_sample=True,temperature=.45,top_p=.85,pad_token_id=self._tokenizer.eos_token_id,
                prefix_allowed_tokens_fn=prefix)
        generated=output[0,ids.shape[-1]:].tolist()
        return {'model_input':payload,'raw_output':self._tokenizer.decode(generated,skip_special_tokens=True).strip(),
            'input_token_ids':ids[0].tolist(),'generated_token_ids':generated,
            'decoder':'lm-format-enforcer-0.11.3','generation_thinking':False,
            'chat_template_sha256':sha256(self._tokenizer.chat_template.encode()).hexdigest()}

    def _generate_tool(self,payload):
        compact=compact_action_history(payload)
        payload['messages']=compact['messages']
        request=json.loads(payload['messages'][-1]['content'])
        request['self_generated_private_agenda']=deepcopy(self.private_agenda)
        request['private_agenda_status']=('generated_interpretation_not_world_fact' if self._agenda_error is None
                                        else 'agenda_generation_invalid_previous_interpretation_retained')
        payload['messages'][-1]['content']=json.dumps(request,ensure_ascii=False,separators=(',',':'))
        return super()._generate_tool(payload)

    def decide(self,scene):
        before=deepcopy(self.private_agenda)
        request=agenda_request(scene,self.activity,self.profile,before,self.decisions)
        started=time.perf_counter();inference=self._generate_agenda(request);error=None
        try:proposal=parse_agenda(inference['raw_output'])
        except (ValueError,TypeError) as exc:error=str(exc);proposal=None
        # 类型检查只保留或拒绝NN输出；不替它选择需要、下一贡献或正确约定。
        if proposal is not None:self.private_agenda=deepcopy(proposal)
        self._agenda_error=error
        inference.update(request=request,agenda_before=before,agenda_after=deepcopy(self.private_agenda),
            parse_error=error,latency_s=time.perf_counter()-started,output_schema=deepcopy(AGENDA_SCHEMA))
        self.agenda_inferences.append(inference)
        row=super().decide(scene)
        row.update(private_agenda_inference=deepcopy(inference),neural_inferences=2,
            human_policy_interface='private_agenda_then_current_contribution_v1',
            human_history_encoding='current_full_scene_and_compact_factual_experience_v1')
        row['latency_s']+=inference['latency_s']
        return row
