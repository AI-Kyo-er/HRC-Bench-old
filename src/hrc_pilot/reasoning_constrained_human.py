"""保留Qwen原生思考并约束最终调用；不依据分数选择或纠正策略。"""
from copy import deepcopy
import json

from .constrained_human_decision import ConstrainedHumanDecisionPolicy,PREFIX,constrained_tool,constrained_interface,decision_json_schema
from .human_decision_interface import available_destinations
from .thinking_schema_filter import ThinkingSchemaFilter


THINK_PREFIX='<think>\n'


def reasoning_request(source,request):
    actual=deepcopy(request);actual.pop('human_contribution_interface',None)
    actual['human_decision_interface']=constrained_interface(source)
    actual['scene']['named_destinations']=list(available_destinations(source))
    # 场景说明和能力目录是环境信息，不是队友已经提出的请求。
    actual['scene']['public_partner_statements_not_execution_facts']=[m for m in source['public_dialogue'] if m['speaker'] in {'human','robot'}]
    actual['human_measured_object_contacts']=deepcopy(source['measured_world'].get('object_contacts',{}))
    return actual


class ReasoningConstrainedHumanPolicy(ConstrainedHumanDecisionPolicy):
    enable_thinking=True
    generation_token_limit=4096

    def _system_prompt(self):
        # 只保留真正的接口规则，去掉非thinking模式的说明。
        from .human_decision_policy import HumanDecisionPolicy
        return HumanDecisionPolicy._system_prompt(self)+(
            'pause_current停止自己的当前运动并保留持物，wait继续原运动。'
            'activity是活动说明，public_robot_operation_inputs是能力，不是队友请求；'
            '队友请求只来自实际public_partner_statements。私人需要变更不能仅由能力目录推出。')

    def _generate_tool(self,payload):
        source=self._current_source_scene
        request=reasoning_request(source,json.loads(payload['messages'][-1]['content']))
        payload['messages'][-1]['content']=json.dumps(request,ensure_ascii=False,separators=(',',':'))
        payload['tools']=[constrained_tool(source)];self._current_schema=decision_json_schema(source)
        if self.generator is not None:return self.generator(json.dumps(payload,ensure_ascii=False))
        self._load_model()
        import torch
        from lmformatenforcer import JsonSchemaParser
        from lmformatenforcer.integrations.transformers import build_token_enforcer_tokenizer_data,build_transformers_prefix_allowed_tokens_fn
        if not hasattr(self,'_format_tokenizer_data'):self._format_tokenizer_data=build_token_enforcer_tokenizer_data(self._tokenizer)
        encoded=self._tokenizer.apply_chat_template(payload['messages'],tools=payload['tools'],
            tokenize=True,add_generation_prompt=True,enable_thinking=True,return_tensors='pt').to(self._model.device)
        ids=encoded['input_ids'] if hasattr(encoded,'keys') else encoded
        suffix=torch.tensor([self._tokenizer.encode(THINK_PREFIX,add_special_tokens=False)],device=ids.device)
        ids=torch.cat([ids,suffix],dim=1);self._current_token_ids=ids[0].tolist()
        close=self._tokenizer.encode('</think>',add_special_tokens=False)
        if len(close)!=1:raise ValueError('该模型没有单一原生思考结束token')
        prefix_fn=build_transformers_prefix_allowed_tokens_fn(self._format_tokenizer_data,JsonSchemaParser(self._current_schema))
        filter_fn=ThinkingSchemaFilter(prefix_fn,input_length=ids.shape[-1],close_think_id=close[0],
            tool_prefix_ids=self._tokenizer.encode(PREFIX,add_special_tokens=False),
            vocab_size=self._model.config.vocab_size,eos_id=self._tokenizer.eos_token_id)
        with torch.inference_mode():
            generated=self._model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),max_new_tokens=4096,
                do_sample=True,temperature=.45,top_p=.85,pad_token_id=self._tokenizer.eos_token_id,
                prefix_allowed_tokens_fn=filter_fn)
        output=generated[0,ids.shape[-1]:].tolist();self._whole_output_token_ids=output
        self._raw_generated_text=self._tokenizer.decode(output,skip_special_tokens=False)
        close_index=output.index(close[0]);start=close_index+1+len(filter_fn.tool_prefix_ids)
        self._generated_token_ids=output[start:]
        self._generated_json=self._tokenizer.decode(self._generated_token_ids,skip_special_tokens=True).strip()
        self._reasoning_token_ids=output[:close_index]
        self._reasoning_text=self._tokenizer.decode(self._reasoning_token_ids,skip_special_tokens=False)
        self._forced_close=filter_fn.forced_think_close
        return PREFIX+self._generated_json+'\n</tool_call>'

    def decide(self,scene):
        row=super().decide(scene)
        row.update(choice_schema_version=10,human_policy_interface='reasoning_then_schema_constrained_decision_v1',
            human_observation_encoding='intent_semantic_agent_dialogue_v3',generation_thinking=True,
            caller_input_prefix=THINK_PREFIX,reasoning_text=getattr(self,'_reasoning_text',None),
            reasoning_token_ids=getattr(self,'_reasoning_token_ids',None),whole_generated_token_ids=getattr(self,'_whole_output_token_ids',None),
            reasoning_close_forced=getattr(self,'_forced_close',None),reasoning_token_limit=1536)
        row['actual_raw_generated_text']=getattr(self,'_raw_generated_text',None)
        return row
