"""保留接触与短测量历史、允许模型选择真实手部空间动作的学习伙伴。"""
import json
import numpy as np

from .continuous import HumanCommand
from .learned_human import LearnedArticulatedHuman
from .native_action_validation import command_feedback


def hand_target(value):
    point=value.get('hand_target_xyz')
    if not isinstance(point,list) or len(point)!=3:raise ValueError('hand_target_xyz必须为3维位置')
    point=np.asarray(point,dtype=float)
    if not np.isfinite(point).all() or not np.all(point>=(-.7,-.4,.98)) or not np.all(point<=(.7,.85,1.45)):
        raise ValueError('手部目标超出公开工作空间')
    return tuple(float(x) for x in point)


class InteractiveArticulatedHuman(LearnedArticulatedHuman):
    def reset(self,seed):
        super().reset(seed);self.compact_measurement_history=[]

    def _system_prompt(self):
        return super()._system_prompt()+('还可选择move_hand并输出hand_target_xyz，在公开工作空间中真实受力移动手部。'
            '这个动作维持现有夹指压力，不能自动抓放或自动执行后续计划；你自己决定是否退开、抬高手或继续操作。'
            'hand_contact_summary是当前真实接触，recent_measured_world_history是过去测量，不是完成成绩。')

    def _prompt(self,observation):
        public=json.loads(super()._prompt(observation).split('\n',1)[1])
        measured=observation.human_execution
        report=measured.get('hand_contact_report',{})
        public['hand_contact_summary']={
            'source':'current_collision_geometry_no_goal_or_force_inference',
            'contact_with_other_agent':bool(report.get('contact_with_other_agent',False)),
            'contact_geoms':list(measured.get('hand_contact_geoms',[]))[:12]}
        for key in ['body_xy','body_target_xy','body_remaining_distance_m','fingertip_target_xyz']:
            if key in measured:public['your_measured_execution'][key]=measured[key]
        history={'time_s':observation.time_s,'fingertip_xyz':list(observation.human_hand_position) if observation.human_hand_position is not None else None,
            'fingertip_remaining_distance_m':measured.get('fingertip_remaining_distance_m'),
            'phase':observation.human_motor_phase,'object_measured_in_hand':measured.get('object_measured_in_hand'),
            'contact_with_other_agent':public['hand_contact_summary']['contact_with_other_agent']}
        public['recent_measured_world_history']=self.compact_measurement_history[-2:]
        self.compact_measurement_history.append(history)
        public['action_interface']['intents'].append('move_hand')
        public['action_interface']['hand_workspace_xyz_min']=[-.7,-.4,.98]
        public['action_interface']['hand_workspace_xyz_max']=[.7,.85,1.45]
        public['observation_projection']='compact_contact_history_v2'
        return '共同推理当前个人意图与下一动作：\n'+json.dumps(public,ensure_ascii=False,separators=(',',':'))

    def _validated_command(self,value,observation):
        if value.get('intent')!='move_hand':return super()._validated_command(value,observation)
        error=None
        try:command=HumanCommand('move_hand',target=hand_target(value),speed_mps=.2)
        except (ValueError,TypeError):command=HumanCommand('observe');error='invalid_hand_target_xyz'
        self.last_command_feedback=command_feedback(value,command,observation.objects,observation.regions,
            valid_intents=['push','grasp','place','release','observe','yield','away','return','move_hand'])
        if error:
            self.last_command_feedback['status']='rejected';self.last_command_feedback['errors'].append(error)
        return command

    def step(self,observation):
        count=len(self.policy_io);output=super().step(observation)
        if len(self.policy_io)>count:
            self.policy_io[-1]['observation_projection']='compact_contact_history_v2'
            self.policy_io[-1]['hand_target_xyz']=list(output.command.target) if output.command.intent=='move_hand' else None
        return output
