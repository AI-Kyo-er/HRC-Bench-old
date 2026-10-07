"""真实接触示范适配的神经伙伴；只投影测量，不路由策略或执行计划。"""
import json
from pathlib import Path

from .native_deliberative_human import DeliberativeArticulatedHuman


EXECUTION_KEYS=('accepted_intent','motor_phase','status','command_elapsed_s','fingertip_xyz',
    'fingertip_remaining_distance_m','object_id','destination','object_xyz','destination_xyz',
    'object_remaining_xy_distance_m','object_center_inside_visible_destination',
    'object_measured_in_hand','motor_failure','measured_finger_target_contacts')


class LearnedArticulatedHuman(DeliberativeArticulatedHuman):
    def __init__(self,*args,adapter_path=None,**kwargs):
        self.adapter_path=Path(adapter_path) if adapter_path else None
        self._adapter_loaded=False
        super().__init__(*args,**kwargs)

    def _load_model(self):
        super()._load_model()
        if self.adapter_path and not self._adapter_loaded:
            from peft import PeftModel
            self._model=PeftModel.from_pretrained(self._model,str(self.adapter_path),is_trainable=False)
            self._model.eval();self._adapter_loaded=True

    def _prompt(self,observation):
        full=json.loads(super()._prompt(observation).split('\n',1)[1])
        keys=('time_s','objects_xyz','regions_xyz','human_position_xyz','robot_ee_xyz',
            'your_hand_position_xyz','robot_current_assignments','your_current_assignments',
            'personal_context','preferred_personal_object_ids','your_previous_personal_targets',
            'your_long_term_intention','your_last_command_validation','task_source',
            'human_input_contract','agent_identity')
        public={k:full[k] for k in keys if k in full}
        measured=full['your_measured_execution']
        public['your_measured_execution']={k:measured[k] for k in EXECUTION_KEYS if k in measured}
        public['action_interface']=full['action_interface']
        public['robot_measured_motion']={k:v for k,v in full['robot_measured_motion'].items()
            if k in {'eef_speed_m_s','perceived_object_contacts'}}
        public['public_dialogue']=full['public_dialogue'][-4:]
        public['previous_model_choices']={'source':'own_past_model_choices_not_current_world_facts',
            'decisions':[{k:d[k] for k in ('time_s','intent','object_id','destination')} for d in self.public_decision_history[-3:]]}
        public['observation_projection']='compact_measured_world_v1'
        return '共同推理当前个人意图与下一动作：\n'+json.dumps(public,ensure_ascii=False,separators=(',',':'))

    def step(self,observation):
        count=len(self.policy_io);output=super().step(observation)
        if len(self.policy_io)>count:
            self.policy_io[-1].update(observation_projection='compact_measured_world_v1',
                adapter_path=str(self.adapter_path) if self.adapter_path else None)
        return output
