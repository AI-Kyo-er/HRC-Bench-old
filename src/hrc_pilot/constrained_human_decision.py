"""只约束合法接口结构；不按任务进展选择策略、目标或同意内容。"""
from copy import deepcopy
import json

from .human_decision_interface import decision_tool,decision_interface,available_destinations,parse_decision,destinations_for_object,movable_objects
from .human_decision_policy import HumanDecisionPolicy


PREFIX='<tool_call>\n'


def constrained_tool(scene):
    tool=decision_tool(scene)
    variants=[{'type':'null'}]
    for obj in movable_objects(scene):
        destinations=destinations_for_object(scene,obj)
        variants.append({'type':'object','properties':{
            'kind':{'type':'string','enum':['place_object']},'object_id':{'type':'string','enum':[obj]},
            'destination':{'type':'string','enum':destinations}},
            'required':['kind','object_id','destination'],'additionalProperties':False})
    # 新契约分开实际取放能力与指示固定实体；旧schema保持原形式供历史重建。
    if 'movable_object_ids' in scene:
        for kind,objects in [('hold_object',movable_objects(scene)),('indicate_object',list(scene['objects_xyz']))]:
            variants.append({'type':'object','properties':{'kind':{'type':'string','enum':[kind]},
                'object_id':{'type':'string','enum':objects}},'required':['kind','object_id'],'additionalProperties':False})
    else:
        variants.append({'type':'object','properties':{
            'kind':{'type':'string','enum':['hold_object','indicate_object']},
            'object_id':{'type':'string','enum':list(scene['objects_xyz'])}},
            'required':['kind','object_id'],'additionalProperties':False})
    variants.append({'type':'object','properties':{'kind':{'type':'string',
        'enum':['step_aside','return_to_work','wait','pause_current']}},'required':['kind'],'additionalProperties':False})
    tool['function']['parameters']['properties']['contribution']={'anyOf':variants}
    return tool


def constrained_interface(scene):
    result=decision_interface(scene)
    result['contributions']['pause_current']='Stop your current motion where it is, retain any held item, and cancel the previous motion request. Does not release or give the item to the robot.'
    return result


def decision_json_schema(scene):
    return {'type':'object','properties':{'name':{'type':'string','enum':['choose_human_contribution']},
        'arguments':constrained_tool(scene)['function']['parameters']},'required':['name','arguments'],'additionalProperties':False}


def parse_constrained_decision(raw,scene):
    text=raw[len(PREFIX):].removesuffix('\n</tool_call>').strip()
    call=json.loads(text);motion=call.get('arguments',{}).get('contribution')
    pause=isinstance(motion,dict) and motion.get('kind')=='pause_current'
    parsed=deepcopy(call)
    if pause:
        if set(motion)-{'kind'}:raise ValueError('暂停当前运动不选择新物品或目标')
        parsed['arguments']['contribution']=None
    choice,normalization,_=parse_decision(PREFIX+json.dumps(parsed,ensure_ascii=False)+'\n</tool_call>',scene)
    if pause:
        choice['action']='pause_current';normalization['contribution_kind']='pause_current'
    return choice,normalization,call


class ConstrainedHumanDecisionPolicy(HumanDecisionPolicy):
    enable_thinking=False
    generation_token_limit=1024

    def _system_prompt(self):
        return super()._system_prompt()+(
            'pause_current明确停止自己的当前搬运并保留持物，wait继续原运动；让权不能只说话。'
            '接下来按工具定义输出JSON调用，格式由解码器约束；意图、贡献、目标和话语仍由你自己选。')

    def _generate_tool(self,payload):
        source=self._current_source_scene
        request=json.loads(payload['messages'][-1]['content'])
        request.pop('human_contribution_interface',None)
        request['human_decision_interface']=constrained_interface(source)
        request['scene']['named_destinations']=list(available_destinations(source))
        request['human_measured_object_contacts']=deepcopy(source['measured_world'].get('object_contacts',{}))
        payload['messages'][-1]['content']=json.dumps(request,ensure_ascii=False,separators=(',',':'))
        payload['tools']=[constrained_tool(source)]
        self._current_schema=decision_json_schema(source)
        if self.generator is not None:return self.generator(json.dumps(payload,ensure_ascii=False))
        self._load_model()
        import torch
        from lmformatenforcer import JsonSchemaParser
        from lmformatenforcer.integrations.transformers import build_token_enforcer_tokenizer_data,build_transformers_prefix_allowed_tokens_fn
        if not hasattr(self,'_format_tokenizer_data'):
            self._format_tokenizer_data=build_token_enforcer_tokenizer_data(self._tokenizer)
        encoded=self._tokenizer.apply_chat_template(payload['messages'],tools=payload['tools'],
            tokenize=True,add_generation_prompt=True,enable_thinking=False,return_tensors='pt').to(self._model.device)
        ids=encoded['input_ids'] if hasattr(encoded,'keys') else encoded
        suffix=torch.tensor([self._tokenizer.encode(PREFIX,add_special_tokens=False)],device=ids.device)
        ids=torch.cat([ids,suffix],dim=1);self._current_token_ids=ids[0].tolist()
        prefix_fn=build_transformers_prefix_allowed_tokens_fn(self._format_tokenizer_data,JsonSchemaParser(self._current_schema))
        with torch.inference_mode():
            generated=self._model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),
                max_new_tokens=self.generation_token_limit,do_sample=True,temperature=.45,top_p=.85,
                pad_token_id=self._tokenizer.eos_token_id,prefix_allowed_tokens_fn=prefix_fn)
        self._generated_token_ids=generated[0,ids.shape[-1]:].tolist()
        self._generated_json=self._tokenizer.decode(generated[0,ids.shape[-1]:],skip_special_tokens=True).strip()
        return PREFIX+self._generated_json+'\n</tool_call>'

    def decide(self,scene):
        row=super().decide(scene)
        try:choice,normalization,call=parse_constrained_decision(row['raw_output'],scene)
        except (ValueError,TypeError,KeyError) as error:row['parse_error']=str(error)
        else:row.update(choice=choice,parse_error=None,contribution_normalization=normalization,selected_tool_call=call)
        row.update(choice_schema_version=9,human_policy_interface='schema_constrained_decision_with_explicit_pause_v1',
            human_observation_encoding='intent_semantic_available_targets_v2',
            output_json_schema=deepcopy(self._current_schema),generation_thinking=False,
            caller_prefix=PREFIX,caller_suffix='\n</tool_call>',
            decoder='lm-format-enforcer-0.11.3',actual_generated_json=getattr(self,'_generated_json',None))
        row['actual_generated_token_ids']=getattr(self,'_generated_token_ids',None)
        return row
