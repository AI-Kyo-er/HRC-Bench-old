"""将可信测量与生成假设分开的人策略，反思采用本地推理模式。"""
import json
import numpy as np

from .llm_human import QwenHumanPolicy
from .native_reflective_human import ReflectiveArticulatedHuman


FACT_KEYS=('time_s','objects_xyz','regions_xyz','public_goal_surfaces','human_position_xyz',
    'robot_ee_xyz','your_hand_position_xyz','your_visible_motor_phase','robot_action','robot_action_phase',
    'public_dialogue','persistent_public_task_board','your_measured_execution','robot_measured_motion',
    'your_current_assignments','robot_current_assignments','action_interface','personal_context',
    'preferred_personal_object_ids','your_previous_personal_targets','your_long_term_intention',
    'your_last_target_validation','your_last_command_validation','task_source','public_scene_description',
    'your_target_geometry')


class GroundedReflectiveHuman(ReflectiveArticulatedHuman):
    allow_relational_targets=True

    def _system_prompt(self):
        text=super()._system_prompt()
        if self._inference_stage=='intention':
            text=text.replace('固定区域destination对','destination对；目的地为公开区域或action_interface中合法on:接收物体关系')
        return text

    def reset(self,seed):
        super().reset(seed);self.stage_model_outputs={}

    def _prompt(self,observation):
        full=json.loads(super()._prompt(observation).split('\n',1)[1])
        facts={key:full[key] for key in FACT_KEYS if key in full}
        facts['recent_measured_world_history']=self.motor_observation_history[-3:]
        facts['information_sources']={
            'measurements':'current simulator perception and own execution sensors',
            'roles':'public task board; robot assignments belong to robot',
            'intentions':'own model-generated private goals; not observed completion',
            'past_generated_explanations':'excluded from action evidence; no repetition-based factual credit'}
        return '根据可信测量、公开分工和自己的意图自主行动：\n'+json.dumps(facts,ensure_ascii=False,separators=(',',':'))

    def _call_stage(self,stage,prompt):
        import time
        self._inference_stage=stage;self.enable_thinking=stage=='intention'
        self.generation_token_limit=2048 if self.enable_thinking else 512
        started=time.perf_counter();raw=QwenHumanPolicy._generate(self,prompt);latency=time.perf_counter()-started
        self.stage_model_outputs[stage]={'raw_model_output':raw,'thinking_enabled':self.enable_thinking,
                                        'generation_token_limit':self.generation_token_limit}
        if self.enable_thinking:
            answer=raw.rsplit('</think>',1)[-1].strip() if '</think>' in raw else ''
        else:answer=raw
        return answer,latency

    def _motor_context(self,public):
        """在意图推理之后投影当前目标，不把过去的模型观察判断当动作事实。"""
        public=dict(public)
        planner=self.planning_io[-1]
        public['human_input_contract']='current_intentions_and_measured_geometry_v2'
        public['agent_identity']={'self':'human','other':'robot'}
        public['your_current_personal_targets']=[dict(t) for t in self.personal_targets]
        public.pop('your_previous_personal_targets',None)
        public.pop('your_previous_generated_plan',None)
        public['active_intention_plan']={k:self.active_plan.get(k) for k in
            ['decision_kind','long_term_intention','personal_targets','plan']}
        public['active_intention_plan'].update(source='own_model_generated_intentions_not_world_measurements',
            generated_at_sim_time_s=planner['time_s'])
        geometry=[]
        for target in self.personal_targets:
            obj,destination=target['object_id'],target['destination']
            relative=public['action_interface'].get('relative_placement_destinations',{})
            if destination in public['regions_xyz']:
                point=public['regions_xyz'][destination];radius=.025
            elif destination in relative:
                receiver=relative[destination]['receiver_object_id']
                point=public['objects_xyz'][receiver];radius=.03
            else:continue
            geometry.append({**target,'destination_xyz':point,
                'measured_xy_distance_m':float(np.linalg.norm(np.asarray(public['objects_xyz'][obj])[:2]-np.asarray(point)[:2])),
                'visible_radius_m':radius,'measurement_time_s':public['time_s']})
        public['your_target_geometry']=geometry
        return public

    def step(self,observation):
        previous_plans=len(self.planning_io);previous_motors=len(self.policy_io)
        output=super().step(observation)
        if len(self.planning_io)>previous_plans:self.planning_io[-1].update(self.stage_model_outputs['intention'])
        if len(self.policy_io)>previous_motors:
            self.policy_io[-1].update(self.stage_model_outputs['motor'])
            self.policy_io[-1]['human_policy_architecture']='grounded_reflective_intent_then_motor'
        return output

    def audit_state(self):
        return {**super().audit_state(),'policy_architecture':'grounded_reflective_intent_then_motor'}
