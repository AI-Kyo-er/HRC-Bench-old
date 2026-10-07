"""背景／测量／公开交互驱动的在线人策略，不调用任务教师或操作成绩。"""
import json
import time

from .continuous import CONTINUOUS_SCENARIOS
from .llm_human import QwenHumanPolicy
from .joint_activity import PROFILES


INTENTS={'pick','place','point','move_hand','away','return','wait','message'}
MESSAGE_KINDS={'proposal','accept','reject','update','request','notice'}


def parse_choice(raw,objects,regions):
    text=raw.rsplit('</think>',1)[-1].strip()
    value=json.loads(text[text.index('{'):text.rindex('}')+1])
    if value.get('action') not in INTENTS:raise ValueError('非法人动作')
    if value['action'] in {'pick','point'} and value.get('object_id') not in objects:
        raise ValueError('所选物品不存在')
    if value['action']=='place' and value.get('destination') not in regions:
        raise ValueError('所选区域不存在')
    if value['action']=='move_hand':
        import numpy as np
        point=np.asarray(value.get('target_xyz'),dtype=float)
        if point.shape!=(3,) or not np.isfinite(point).all() or not np.all(point>=[-.7,-.4,.95]) or not np.all(point<=[.7,.9,1.5]):
            raise ValueError('手部目标超出工作空间')
    if value.get('message_kind','notice') not in MESSAGE_KINDS:raise ValueError('非法公开消息类型')
    # 记忆可为结构化记录；不能因辅助字段格式丢弃合法策略动作。
    if not isinstance(value.get('memory',''),str):
        value['memory']=json.dumps(value.get('memory'),ensure_ascii=False)
    for key in ['intention','participation','reason','message']:
        if not isinstance(value.get(key,''),str):raise ValueError(key+'须为文字')
    return value


class JointHumanPolicy(QwenHumanPolicy):
    enable_thinking=False
    generation_token_limit=1024

    def __init__(self,activity,*,model_path,profile='participating',seed=0,generator=None):
        self.activity=activity;self.profile=profile
        if profile not in PROFILES:raise ValueError('未知人物背景')
        super().__init__(CONTINUOUS_SCENARIOS['relay'],model_path=model_path,generator=generator,
                         persona_id='cooperative',memory_scope='episode')
        self.reset(seed);self.decisions=[];self.private_memory=[]

    def _system_prompt(self):
        return (
            '你是与机械臂共同进行日常活动的人，不是任务调度器。自己决定当前需要、参与和一个下一动作。'
            '根据自己的背景、当前测量、伙伴实际行为和公开对话考虑保留、修改、暂停、接手或结束活动。'
            '对方不知道你的私人需要，重要改变应通过简短英文message、指示或实际行为表达。'
            '共同活动的dependencies描述相互依赖，不是要求照着执行的动作队列。'
            '公开承诺只是表达，位置和机器人动作才是执行事实；不要把你以前的计划当成现在的事实。'
            '机器人可能不会说话，其实际运动也是反馈；可以询问、建议、拒绝或让出操作区。'
            '人执行由连续运动学动作完成，无需规划手指摩擦。pick接近并持有物品；place将当前持有物品放到区域；'
            'point指向物品但不移动它；move_hand指定位置；away/return移开或返回；wait等待并保留握持。'
            '一个动作未结束时可以选择wait让它继续，或明确选择另一个动作。程序不自动执行后续计划。'
            'scene.private_context是外部事实，不是要求你离开或变心的命令。你可以合理坚持当前安排。'
            '不要凭任务时间长或为满足测试而随机换目标。不读取评分，不编造伙伴隐藏目标。'
            '严格输出一个完整JSON对象，action只能是pick/place/point/move_hand/away/return/wait/message之一。'
            'move_hand仅使用公开workspace内的target_xyz；place仅选择regions_xyz中实际存在的名字。'
            '若仅询问、安排、拒绝或表达，可选action=message；它不会中止正在进行的身体动作。'
            '输出JSON：intention、participation、action、object_id、destination、target_xyz（仅move_hand需要）、'
            'message_kind（proposal/accept/reject/update/request/notice）、message（简短英文）、reason、memory。'
            '不输出动作清单。')

    def decide(self,scene):
        request={'agent_identity':{'self':'human','partner':'robot'},
                 'activity':self.activity.public(),'personal_background':self.activity.private_background,
                 'profile':PROFILES[self.profile],'scene':scene,
                 'own_previous_choices':[{k:d['choice'].get(k) for k in ['intention','participation','action','message']}
                                         for d in self.decisions[-4:]],
                 'own_memory':self.private_memory[-6:]}
        prompt=json.dumps(request,ensure_ascii=False,separators=(',',':'))
        started=time.perf_counter();raw=self._generate(prompt);error=None
        try:choice=parse_choice(raw,scene['objects_xyz'],scene['regions_xyz'])
        except (ValueError,TypeError,KeyError) as exc:
            error=str(exc);choice={'action':'wait','message':'','message_kind':'notice',
                'intention':'','participation':'','reason':'输出非法，保留现场并等待下一次人决策。','memory':''}
        row={'decision_id':len(self.decisions),'time_s':scene['time_s'],'system_prompt':self._system_prompt(),
             'private_input':request,'raw_output':raw,'choice':choice,'parse_error':error,
             'latency_s':time.perf_counter()-started,'action_source':'actual_qwen_joint_human'}
        self.decisions.append(row)
        if choice.get('memory'):self.private_memory.append({'time_s':scene['time_s'],'text':choice['memory']})
        return row
