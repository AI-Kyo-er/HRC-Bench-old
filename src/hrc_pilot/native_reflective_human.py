"""独立的生成式意图反思和动作推理；计划与评分均不路由执行器。"""
import json
import time
from types import SimpleNamespace

import numpy as np

from .continuous import PartnerOutput
from .llm_human import QwenHumanPolicy, PERSONAS
from .native_autonomous_human import CONTEXTS, validate_targets
from .native_hand_policy import ArticulatedAutonomousHuman
from .protocol import Message


class ReflectiveArticulatedHuman(ArticulatedAutonomousHuman):
    def __init__(self,*args,reflection_interval_s=6.,**kwargs):
        if reflection_interval_s<=0:raise ValueError('反思推理间隔须为正')
        self.reflection_interval_s=float(reflection_interval_s)
        super().__init__(*args,**kwargs)

    def reset(self,seed):
        super().reset(seed)
        self.planning_io=[];self.next_reflection_s=0.;self.active_plan={}
        self.last_reflection_objects={};self._pending_proposals=();self._inference_stage='motor'
        self._actual_motor_input=''

    def _system_prompt(self):
        if self._inference_stage=='intention':
            return (
                '你是在共用工作台活动的人，现在只进行较长期意图反思，不输出动作intent。'
                f'个人生活背景：{CONTEXTS[self.autonomous_context]["preferences"]}'
                f'行为倾向：{PERSONAS[self.persona_id]}；个人偏好物品：{self.preferred_personal_objects}。'
                '这些是背景，不是必须执行的清单或强制变化时刻。'
                '比较最新实际位置、接触、自己的执行历史和机器人公开任务，与自己先前的假设。'
                'assigned_role=robot的任务属于机器人；你可以帮助、维护个人活动、等待、改安排或放弃，但不要自动把它当自己的任务。'
                '先前memory_note和reason是自己的解释，可能错误；位置、接触与现在的运动优先。'
                '如果自己的抓取没有发生，而机器人已移动了物品，不必重复声称自己仍在完成原步骤；可以改变计划或协商。'
                '只依据感知判断，不编造完成成绩或对方已接受请求。'
                '只输出JSON：decision_kind（continue/revise/suspend/finish_activity），long_term_intention，'
                'personal_targets（0到3个现有object_id和固定区域destination对），plan（最多5条自己的计划文本），'
                'observed_changes（当前观察支持的简短说明），assumption_corrections（纠正自己的旧解释），'
                'negotiation_proposal（kind为request_space/request_help/offer_help/revise_arrangement，text为简短英文，或null）。'
                '目标可以保留、调整或清空，但不要为了变化而变化。计划不会自动执行。')
        return (
            '你是该人的当前动作决策模型，依据最新感知和意图反思选择一个动作。'
            'active_intention_plan是自己较长期意图，不是执行器队列；只执行这次intent，不自动转到计划下一步。'
            '最新实际位置、接触和握持优先于旧计划或解释；机器人任务不自动成为你的任务。'
            '按action_interface选择push/grasp/place/release/observe/yield/away/return。'
            'grasp尚在执行时可以继续，也可依据无进展、空间争用或对方活动暂停、换物品或让行。'
            '只有object_measured_in_hand为该物品才可place；release张手，observe暂停并保留夹持。'
            'place支持固定区域或公开on:物体的当前支撑放置；后者不保证完整容器包含。'
            '不会因为你说握住、放下或合作而发生物理成功。协商不自动被机器人接受。'
            '只输出JSON：intent、object_id、destination、message（最多16个英文单词）、speed_mps、reason、'
            'memory_note、current_goal、wait_condition。不在此层修改personal_targets或长期意图。')

    def _call_stage(self,stage,prompt):
        self._inference_stage=stage
        self.generation_token_limit=512 if stage=='intention' else 384
        started=time.perf_counter()
        raw=QwenHumanPolicy._generate(self,prompt)
        return raw,time.perf_counter()-started

    def _generate(self,prompt):
        public=json.loads(prompt.split('\n',1)[1]);now=float(public['time_s'])
        if now>=self.next_reflection_s-1e-9:
            changes={name:float(np.linalg.norm(np.asarray(point)-self.last_reflection_objects[name]))
                     for name,point in public['objects_xyz'].items() if name in self.last_reflection_objects}
            planning_input='阶段：意图反思\n'+json.dumps({**public,'previous_active_intention_plan':self.active_plan,
                'measured_object_displacements_since_last_reflection_m':changes,
                'inference_schedule_only':'periodic cognition, no externally assigned goal changes'},ensure_ascii=False,separators=(',',':'))
            raw,latency=self._call_stage('intention',planning_input)
            error=None;proposal_messages=()
            try:
                value=self._parse(raw)
                targets,error=validate_targets(value.get('personal_targets'),SimpleNamespace(objects=public['objects_xyz'],regions=public['regions_xyz']),allow_pair_arrays=True)
                if error:raise ValueError(error)
                if value.get('decision_kind') not in {'continue','revise','suspend','finish_activity'}:raise ValueError('未知反思类型')
                intention=value.get('long_term_intention')
                if not isinstance(intention,str) or not intention.strip():raise ValueError('缺少长期意图说明')
                plan=value.get('plan',[])
                if not isinstance(plan,list) or any(not isinstance(item,str) for item in plan):raise ValueError('计划必须为文本列表')
                if sorted(targets,key=lambda t:t['object_id'])!=sorted(self.personal_targets,key=lambda t:t['object_id']):self.target_revision+=1
                self.personal_targets=targets;self.long_term_intention=intention[:500]
                self.generated_plan=[p[:180] for p in plan[:5]]
                self.active_plan={key:value.get(key) for key in ['decision_kind','observed_changes','assumption_corrections']}
                self.active_plan.update(long_term_intention=self.long_term_intention,personal_targets=self.personal_targets,plan=self.generated_plan)
                proposal=value.get('negotiation_proposal')
                if isinstance(proposal,dict) and proposal.get('kind') in {'request_space','request_help','offer_help','revise_arrangement'} and isinstance(proposal.get('text'),str):
                    text=proposal['text'].strip()[:180]
                    if text:proposal_messages=(Message('human','negotiation_proposal',f'{proposal["kind"]}: {text}'),)
            except (ValueError,TypeError,json.JSONDecodeError) as exc:error=str(exc)
            self.target_validation_feedback=error
            state=self._personal_state()
            self.planning_io.append({'planner_decision_id':len(self.planning_io),'time_s':now,
                'target_decoder':'dict_or_pair_v1',
                'system_prompt':self._system_prompt(),'public_input':planning_input,'raw_output':raw,
                'validation_error':error,'retained_or_accepted_personal_goal_state':state,
                'active_intention_plan':dict(self.active_plan),'public_proposal_messages':[m.__dict__ for m in proposal_messages],
                'latency_s':latency})
            self.intention_records.append({'time_s':now,**state,'reason':str(self.active_plan.get('observed_changes',''))})
            self.last_reflection_objects=public['objects_xyz'];self.next_reflection_s=now+self.reflection_interval_s
            self._pending_proposals=proposal_messages
        public.update(active_intention_plan=self.active_plan,planner_decision_id=self.planning_io[-1]['planner_decision_id'],
                      your_previous_personal_targets=self.personal_targets,your_long_term_intention=self.long_term_intention,
                      your_previous_generated_plan=self.generated_plan,your_last_target_validation=self.target_validation_feedback)
        self._actual_motor_input='阶段：当前动作\n'+json.dumps(public,ensure_ascii=False,separators=(',',':'))
        raw,_=self._call_stage('motor',self._actual_motor_input)
        return raw

    def _personal_state(self):
        return {'revision':self.target_revision,'personal_targets':[dict(t) for t in self.personal_targets],
                'long_term_intention':self.long_term_intention,'target_validation_error':self.target_validation_feedback}

    def step(self,observation):
        count=len(self.policy_io)
        # Preserve the base observation/message/memory and cadence machinery, but
        # never let motor JSON overwrite the independently generated intention.
        output=QwenHumanPolicy.step(self,observation)
        if count==len(self.policy_io):return output
        row=self.policy_io[-1];row['public_input']=self._actual_motor_input
        row.update(human_policy_architecture='reflective_intent_then_motor',system_prompt=self._system_prompt(),
                   planner_decision_id=self.planning_io[-1]['planner_decision_id'],personal_goal_state=self._personal_state(),
                   generated_plan=self.generated_plan.copy(),command_validation=self.last_command_feedback,
                   negotiation_proposal_messages=[m.__dict__ for m in self._pending_proposals])
        if row['parse_error'] is None:self.wait_condition=str(self._parse(row['raw_output']).get('wait_condition',''))[:300]
        row['wait_condition']=self.wait_condition
        outgoing=output.messages+self._pending_proposals
        self.last_message_count+=len(self._pending_proposals);self._pending_proposals=()
        return PartnerOutput(output.command,outgoing)

    def audit_state(self):
        return {**super().audit_state(),'human_planner_io':self.planning_io,
                'policy_architecture':'reflective_intent_then_motor',
                'total_neural_inferences':len(self.planning_io)+len(self.policy_io)}
