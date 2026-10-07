"""机器人活动与阻挡恢复的数据教师；不接入正式学习策略的动作选择。"""
import numpy as np

from .human_training_teacher import ContactDemonstrationTeacher


class InteractionContactTeacher(ContactDemonstrationTeacher):
    def __init__(self,targets):
        super().__init__(targets);self.waypoint=None;self.samples=[];self.recovery_count=0

    def observe(self,record,regions):
        super().observe(record,regions)
        measured=record['human_execution']
        self.samples.append((record['time_s'],measured.get('fingertip_remaining_distance_m',0.)))
        self.samples=self.samples[-81:]

    def decision(self,observation):
        result=super().decision(observation);measured=observation.human_execution
        remaining=float(measured.get('fingertip_remaining_distance_m',0.))
        if self.waypoint is not None:
            if np.linalg.norm(np.asarray(observation.human_hand_position)-self.waypoint)>.015:
                result.update(intent='move_hand',object_id=None,destination=None,hand_target_xyz=self.waypoint,
                    reason='继续真实手部退开／抬高，当前尚未到达自己选择的空间位置。')
                result['current_goal']=result['reason'];return result
            self.waypoint=None
        contact=measured.get('hand_contact_report',{}).get('contact_with_other_agent',False)
        stalled=(measured.get('motor_phase') in {'grasp_approach','grasp_descend','place_transfer'}
            and measured.get('command_elapsed_s',0.)>4 and remaining>.04
            and len(self.samples)>=40 and max(s[1] for s in self.samples[-40:])-min(s[1] for s in self.samples[-40:])<.008)
        if contact or stalled:
            hand=np.asarray(observation.human_hand_position)
            self.waypoint=[float(hand[0]),float(max(hand[1],.60)),1.30]
            self.recovery_count+=1
            result.update(intent='move_hand',object_id=None,destination=None,hand_target_xyz=self.waypoint,
                reason='当前真实接触或持续无进展，先把手退到靠自己一侧并抬高，保持夹指状态，再重新观察。')
            result['current_goal']=result['reason']
        return result
