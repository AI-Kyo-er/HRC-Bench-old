"""人的自然贡献与交流决策；使用真实原生工具反馈，不调度下一任务。"""
from copy import deepcopy
import json

from .human_decision_interface import decision_tool,decision_interface,parse_decision
from .tool_joint_human import ToolJointHumanPolicy


class HumanDecisionPolicy(ToolJointHumanPolicy):
    def _system_prompt(self):
        return (
            '你是与机械臂共同活动的人，有自己的需要、参与意愿和生活安排。'
            '根据个人背景、新的私人情境、当前实际场景及伙伴的公开请求和行为，决定保留、改变、暂停或结束自己的贡献。'
            '可能贡献与依赖不是强制动作队列，不为展示变化而随机换目标。对方不知道你未公开的需要。'
            '只调用一次choose_human_contribution：contribution选择一个当前身体贡献或null；'
            'communication选择公开交流kind和英文text或null。接受、拒绝、求助、结束是交流，不是抓放动作。'
            'place_object包含取、搬、放和退手，选择实际存在的目标，不必安排手指或先pick后place。'
            'hold_object表示取来自己持有；indicate_object只指示；wait让当前运动继续。'
            'tool_response是随后实际测得的执行进展，接受不等于完成。'
            '自己的旧承诺、私人记忆和伙伴声明可能有误，不替代当前持物、接触和完成记录。'
            'finish表达你认为该部分结束，不改变环境评分或替对方同意。'
            'human_decision_interface列出可兑现贡献和自然目标，不编造未发生的放置。'
            '自己的背景和历史可以解释意图；重要变化应由你选择公开表达或实际动作，让伙伴能响应。'
            '无需每次说话或重复记忆；可以坚持自己的需要、拒绝请求、提出替代或等待。')

    def _generate_tool(self,payload):
        source=self._current_source_scene
        request=json.loads(payload['messages'][-1]['content'])
        request.pop('human_contribution_interface',None)
        request['human_decision_interface']=decision_interface(source)
        request['human_measured_object_contacts']=deepcopy(source['measured_world'].get('object_contacts',{}))
        payload['messages'][-1]['content']=json.dumps(request,ensure_ascii=False,separators=(',',':'))
        payload['tools']=[decision_tool(source)]
        return super()._generate_tool(payload)

    def decide(self,scene):
        self._current_source_scene=scene
        row=super().decide(scene)
        row['private_input']=json.loads(row['native_tool_model_input']['messages'][-1]['content'])
        row.pop('human_contribution_contract',None)
        try:choice,normalization,call=parse_decision(row['raw_output'],scene)
        except (ValueError,TypeError,KeyError) as error:row['parse_error']=str(error)
        else:row.update(choice=choice,parse_error=None,contribution_normalization=normalization,selected_tool_call=call)
        row['choice_schema_version']=8
        row['human_policy_interface']='separate_contribution_and_communication_v1'
        return row
