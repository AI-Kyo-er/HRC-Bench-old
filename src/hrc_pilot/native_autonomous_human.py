"""有个人偏好、模型自选目标及公开协商提案的原生动态人策略。"""
import json

import numpy as np

from .continuous import PartnerOutput
from .native_contact_human import NativeQwenHuman
from .llm_human import PERSONAS
from .protocol import Message


CONTEXTS={
    'snack_host':{'label':'自己安排点心桌',
                  'preferences':'你在准备自己的点心休息，希望饼干在自己容易够到的位置，餐盘可供共同用餐。你喜欢先完成自己需要的整理，再决定是否帮助机械臂；可以根据实际进展改变物体安排、请求对方腾空间或暂时休息。没有必须执行的物体搬运清单。'},
    'snack_storage':{'label':'高台收纳自己的点心','preferences':'你准备把自己的饼干收纳在靠近自己的高台上，以腾出共用桌面的空间。你可以选择合适的真实抓取/搬运工具、改变安排或请求机械臂给你留出空间；根据实际反馈决定怎样推进，不假设命令已经完成。'},
    'shared_serving':{'label':'移动餐盘完成共同上桌','preferences':'你与机械臂准备把食物上桌。你希望接收盘最后在靠近自己的高台上，可先整理自己的食物，也可在机械臂放好碗之后移动盘子。你根据实际进展选择时机、工具和分工提案，不把机器人动作或自己的命令当作已经完成。'},
    'workspace_owner':{'label':'整理并维护自己的工作空间',
                       'preferences':'你与机械臂共用桌面，希望自己的食物和餐具容易取用、桌面不拥挤。你重视空间秩序，会根据对方的运动调整位置安排或提出协商；可以保留物品原位、重新整理或离开返回。没有预定的动作顺序和变化时刻。'}
}


def validate_targets(value,observation):
    """只校验可见参数，不检查分数或替模型选择个人目标。"""
    if not isinstance(value,list) or len(value)>3:return None,'personal_targets必须为最多3个对象/区域对'
    targets=[]
    for item in value:
        if not isinstance(item,dict):return None,'每个目标必须是对象'
        obj,destination=item.get('object_id'),item.get('destination')
        if obj not in observation.objects or destination not in observation.regions:
            return None,'目标对象/区域不在当前公开感知中'
        if any(t['object_id']==obj for t in targets):return None,'同一物体不能同时要求位于两个区域'
        targets.append({'object_id':obj,'destination':destination})
    return targets,None


class AutonomousNativeHuman(NativeQwenHuman):
    generation_token_limit=640

    def __init__(self,*args,autonomous_context,**kwargs):
        self.autonomous_context=autonomous_context
        if autonomous_context not in CONTEXTS:raise ValueError('未知个人活动背景')
        super().__init__(*args,**kwargs)

    def reset(self,seed):
        super().reset(seed)
        self.personal_targets=[];self.long_term_intention='';self.target_revision=0
        self.intention_records=[];self.target_validation_feedback=None

    def _system_prompt(self):
        return (
            '你是在共用餐桌上活动的人，不是完成预设搬运脚本的执行器。'
            f'个人背景与偏好：{CONTEXTS[self.autonomous_context]["preferences"]}'
            f'稳定行为倾向：{PERSONAS[self.persona_id]}'
            '没有给你分配固定物体任务；根据个人偏好、可见世界、自身执行经历及机械臂活动，'
            '自己决定long_term_intention、personal_targets、当前计划和一个下一动作。'
            '机械臂自己的公开任务属于它，你可以合作、提出新安排、拒绝等待或保留个人事项。'
            '目标可以持续、替换或放弃，变化时机由你选择；不必为了变化而改变，也不必为了重复旧记录而坚持。'
            'personal_targets是你现在希望维持的0到3个物体/区域关系，每项含object_id和destination。'
            '它们是你自己的意图，不是完成事实。实际位置优先；目标已经满足时无需重复推向精确中心。'
            '位置未变化或执行失败时，你可以继续、换安排、询问或暂缓，由你决定。'
            '只支持push、observe、yield、away、return；push通过指尖实际受力推物，不支持抓持。'
            'objects_xyz、regions_xyz和your_measured_execution是感知；公开圆形区域半径25mm，按物体中心判断区域。'
            '推物中observe会暂停；返回/让行通过连续身体运动执行。'
            'plan是你写的计划，不会自动执行；每次只执行你选择的intent。'
            '可用negotiation_proposal向机器人请求空间、请求帮助、提供帮助或提出重新安排。'
            '其kind只可为request_space、request_help、offer_help、revise_arrangement，text用简短英文；'
            '没有提案时为null。提出请求不等于机器人同意，不能编造已达成分工。'
            '机器人可能没有语言回复，请根据后续实际运动和物体位置重新判断，而非假定理解。'
            'your_previous_personal_targets、your_generated_intention_history和记忆是你的旧意图；可以自己修订。'
            '只输出JSON：intent、object_id、destination、message、speed_mps、reason、memory_note、current_goal、plan、wait_condition、'
            'long_term_intention、personal_targets、negotiation_proposal。'
            'message用简短英文公开交流，其余解释可中文；不要输出评测器结果或把命令当成完成。')

    def _prompt(self,observation):
        visible=json.loads(super()._prompt(observation).split('\n',1)[1])
        geometry=[]
        for target in self.personal_targets:
            obj,destination=target['object_id'],target['destination']
            if obj in observation.objects and destination in observation.regions:
                distance=float(np.linalg.norm(np.asarray(observation.objects[obj])[:2]-np.asarray(observation.regions[destination])[:2]))
                geometry.append({**target,'measured_xy_distance_m':distance,'visible_radius_m':.025})
        visible.update(personal_context=CONTEXTS[self.autonomous_context],
                       your_previous_personal_targets=self.personal_targets,
                       your_long_term_intention=self.long_term_intention,
                       your_generated_intention_history=self.intention_records[-5:],
                       your_target_geometry=geometry,your_last_target_validation=self.target_validation_feedback,
                       task_source='no_human_assignment_or_timed_goal_schedule',
                       public_scene_description='Shared table with food and tableware; choose your own activity while the robot performs its publicly assigned task.')
        return '根据个人偏好、当前感知与经历，自己选择目标和下一动作；可提出公开协商：\n'+json.dumps(visible,ensure_ascii=False,separators=(',',':'))

    def step(self,observation):
        before=len(self.policy_io);output=super().step(observation)
        if len(self.policy_io)==before:return output
        row=self.policy_io[-1];extra=()
        if row['parse_error'] is None:
            value=self._parse(row['raw_output'])
            if 'personal_targets' in value:
                targets,error=validate_targets(value['personal_targets'],observation)
                self.target_validation_feedback=error
                if error is None:
                    if sorted(targets,key=lambda t:t['object_id'])!=sorted(self.personal_targets,key=lambda t:t['object_id']):self.target_revision+=1
                    self.personal_targets=targets
            else:self.target_validation_feedback='没有提供personal_targets，保留你先前的意图'
            intention=value.get('long_term_intention')
            if isinstance(intention,str) and intention.strip():self.long_term_intention=intention.strip()[:500]
            proposal=value.get('negotiation_proposal')
            if isinstance(proposal,dict) and proposal.get('kind') in {'request_space','request_help','offer_help','revise_arrangement'} and isinstance(proposal.get('text'),str):
                text=proposal['text'].strip()[:180]
                if text:extra=(Message('human','negotiation_proposal',f'{proposal["kind"]}: {text}'),)
            row['personal_goal_state']={'revision':self.target_revision,'personal_targets':[dict(t) for t in self.personal_targets],
                                        'long_term_intention':self.long_term_intention,'target_validation_error':self.target_validation_feedback}
            row['negotiation_proposal_messages']=[m.__dict__ for m in extra]
            self.intention_records.append({'time_s':observation.time_s,**row['personal_goal_state'],
                                           'reason':row['parsed_decision']['reason']})
        else:
            row['personal_goal_state']={'revision':self.target_revision,'personal_targets':[dict(t) for t in self.personal_targets],
                                        'long_term_intention':self.long_term_intention,'target_validation_error':'输出解析失败，保留此前个人意图'}
            row['negotiation_proposal_messages']=[]
        self.last_message_count+=len(extra)
        return PartnerOutput(output.command,output.messages+extra)

    def audit_state(self):
        return {**super().audit_state(),'intention_records':self.intention_records,
                'autonomous_context':self.autonomous_context,'personal_targets':self.personal_targets}
