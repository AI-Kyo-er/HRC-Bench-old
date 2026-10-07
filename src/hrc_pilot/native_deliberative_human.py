"""一次神经推理联合产生私人意图和当前动作，不执行生成计划队列。"""
import json

from .llm_human import QwenHumanPolicy, PERSONAS
from .native_autonomous_human import CONTEXTS
from .native_grounded_human import FACT_KEYS
from .native_hand_policy import ArticulatedAutonomousHuman


class DeliberativeArticulatedHuman(ArticulatedAutonomousHuman):
    allow_relational_targets=True
    enable_thinking=True
    generation_token_limit=3072

    def _system_prompt(self):
        return (
            '你是共用厨房中活动的人。self=human、other=robot；每次完整推理同时决定自己的当前意图和一个下一动作。'
            f'个人背景：{CONTEXTS[self.autonomous_context]["preferences"]}；倾向：{PERSONAS[self.persona_id]}。'
            f'偏好物品：{self.preferred_personal_objects}，是背景，不是必须完成的任务清单。'
            '比较当前测量、自己的上次动作和意图，考虑个人需要、正在发生的物品操作、空间占用及公开消息。'
            '自己决定保留、改变或结束活动；不要为了目标变化而变化。robot的公开任务不是自动给你的任务。'
            'personal_targets含0到3个object_id/destination对象，destination是公开区域或合法on:关系；它是你现在想维持的关系，不是完成事实。'
            '整个推理的目标与下一动作在同一个JSON中输出，没有另一动作模型或自动计划执行器。'
            '可选择grasp/place/push/release/observe/yield/away/return，参数以action_interface为准。'
            'grasp连续接近、夹持和抬升，命令不等于在手；object_measured_in_hand才报告当次握持。'
            'place只适用于实际在手物品，运动到指定固定区域或当次接收支撑面并尝试释放；不保证容器包含或最终稳定。'
            '相同grasp/place请求可接续正在运行的动作；observe暂停并保留夹持，release张手。'
            '执行阶段完成不等于你的意图达成，须依据当前位置、真实接触与后续反馈判断。'
            '固定个人区域半径25mm；relative_placement_destinations的support_xyz是当前碰撞支撑面，不是接收物body原点。'
            'previous_model_choices是自己以前的想法，不能作为现在的物理事实。计划不会排队执行，每次只执行intent。'
            'negotiation_proposal可为null或kind/text，kind限request_space/request_help/offer_help/revise_arrangement；提案不等于对方同意。'
            '输出一个JSON：long_term_intention、personal_targets、plan、intent、object_id、destination、'
            'reason、memory_note、current_goal、wait_condition、message、negotiation_proposal。message和提案text简短英文，其余可中文。'
            '不输出评测成绩，不编造自己的操作完成或机器人的隐藏计划。')

    def _prompt(self,observation):
        full=json.loads(super()._prompt(observation).split('\n',1)[1])
        public={k:full[k] for k in FACT_KEYS if k in full and k!='your_target_geometry'}
        public.update(human_input_contract='joint_intention_action_v1',
            agent_identity={'self':'human','other':'robot'},
            recent_measured_world_history=self.motor_observation_history[-3:],
            previous_model_choices={'source':'own_past_model_choices_not_current_world_facts',
                'decisions':self.public_decision_history[-3:]})
        return '共同推理当前个人意图与下一动作：\n'+json.dumps(public,ensure_ascii=False,separators=(',',':'))

    def _generate(self,prompt):
        raw=QwenHumanPolicy._generate(self,prompt)
        self._last_full_generation=raw
        # 未结束的思考不能被解析成实际意图或动作。
        return raw.rsplit('</think>',1)[-1].strip() if '</think>' in raw else ''

    def step(self,observation):
        before=len(self.policy_io)
        output=super().step(observation)
        if len(self.policy_io)>before:
            self.policy_io[-1].update(raw_model_output=self._last_full_generation,
                thinking_enabled=True,generation_token_limit=self.generation_token_limit,
                human_policy_architecture='deliberative_joint_intention_action',
                neural_calls_for_this_decision=1)
        return output

    def audit_state(self):
        return {**super().audit_state(),'policy_architecture':'deliberative_joint_intention_action',
            'total_neural_inferences':len(self.policy_io)}
