"""明确已实现贡献与参数域的人意图策略；不将意图文本路由为预设任务。"""
import json

from .human_contribution_contract import contribution_interface,parse_contribution
from .semantic_joint_human import SemanticJointHumanPolicy


class ContributionJointHumanPolicy(SemanticJointHumanPolicy):
    contribution_schema_version=4
    def _system_prompt(self):
        return super()._system_prompt().replace('regions_xyz','named_destinations')+(
            'human_contribution_interface明确你的当前执行能力与目标参数，不是动作队列。'
            'destination必须使用destination_choices中的destination_id；目标物体名不是区域名。'
            '若需要的操作不在你自己的接口中，可协商伙伴、保留／修改意图或说明限制，不能编造已执行。'
            'message为null代表不公开说话，不必每次重复同一句。')

    def _generate(self,prompt):
        request=json.loads(prompt)
        request['human_contribution_interface']=contribution_interface(request['scene'])
        return super()._generate(json.dumps(request,ensure_ascii=False,separators=(',',':')))

    def decide(self,scene):
        row=super().decide(scene);previous_error=row['parse_error']
        try:choice,normalization=parse_contribution(row['raw_output'],scene['objects_xyz'],scene['regions_xyz'],
                                                  schema_version=self.contribution_schema_version)
        except (ValueError,TypeError,KeyError):pass
        else:
            row['choice']=choice;row['parse_error']=None;row['contribution_normalization']=normalization
            if previous_error:
                row['original_contribution_parse_error']=previous_error
                if choice.get('memory'):self.private_memory.append({'time_s':scene['time_s'],'text':choice['memory']})
        row['choice_schema_version']=self.contribution_schema_version
        row['human_contribution_contract']='explicit_parameter_domains_v1'
        return row
