"""以意图所需语义事实驱动同一本地人策略；原始测量单独保留供审计。"""
from copy import deepcopy
import json

from .intent_observation import intent_observation
from .joint_human_policy import JointHumanPolicy,MESSAGE_KINDS,parse_choice


def parse_semantic_choice(raw,objects,regions):
    text=raw.rsplit('</think>',1)[-1].strip()
    value=json.loads(text[text.index('{'):text.rindex('}')+1])
    declared=value.get('message_kind','notice')
    if not isinstance(declared,str) or declared not in MESSAGE_KINDS:
        # 这是辅助记录标签，不应让合法的已选贡献或公开话语丢失。
        value['declared_message_kind']=declared
        value['message_kind']='notice'
    return parse_choice(json.dumps(value,ensure_ascii=False),objects,regions,schema_version=2)


class SemanticJointHumanPolicy(JointHumanPolicy):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.semantic_inputs=[]

    def _system_prompt(self):
        return super()._system_prompt()+(
            '你的scene给出当前语义测量与自己的执行事实，不要求你处理机械臂关节或规划手指。'
            'measured_current_facts与own_execution来自当前测量；public_partner_statements_not_execution_facts只是伙伴说法。'
            '两者不一致时不能把伙伴说法当已经执行；自己判断是否等待、说明受阻、请求核实或调整安排。'
            'object_ids和named_destinations列出真实可选物品／区域，不包含下一步正确答案。')

    def _generate(self,prompt):
        actual=json.loads(prompt)
        actual['scene']=intent_observation(actual['scene'])
        self.semantic_inputs.append(deepcopy(actual))
        return super()._generate(json.dumps(actual,ensure_ascii=False,separators=(',',':')))

    def decide(self,scene):
        cursor=len(self.semantic_inputs)
        row=super().decide(scene)
        previous_error=row['parse_error']
        try:
            choice=parse_semantic_choice(row['raw_output'],scene['objects_xyz'],scene['regions_xyz'])
        except (ValueError,TypeError,KeyError):pass
        else:
            row['choice']=choice;row['parse_error']=None
            if previous_error:
                row['original_auxiliary_parse_error']=previous_error
                if choice.get('memory'):self.private_memory.append({'time_s':scene['time_s'],'text':choice['memory']})
        row['observation_source_scene']=deepcopy(scene)
        row['private_input']=self.semantic_inputs[cursor]
        if row['reflection_enabled']:row['reflection_input']=self.semantic_inputs[cursor+1]
        row['human_observation_encoding']='intent_semantic_facts_v1'
        row['choice_schema_version']=3
        return row
