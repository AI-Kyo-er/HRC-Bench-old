"""只用于生成训练范例的几何教师，正式Benchmark不导入其决策。"""
import numpy as np


class ContactDemonstrationTeacher:
    def __init__(self,targets):
        self.targets=targets;self.dwell={t['object_id']:0. for t in targets};self.previous={}

    def observe(self,record,regions):
        for target in self.targets:
            obj=target['object_id'];p=np.asarray(record['objects'][obj]);goal=np.asarray(regions[target['destination']])
            previous=self.previous.get(obj);speed=np.linalg.norm(p-previous)/.05 if previous is not None else float('inf')
            support=touch=False
            for pair in record['contacts']:
                a,b=pair['geom1'] or '',pair['geom2'] or ''
                if b.startswith(obj+'_'):a,b=b,a
                if a.startswith(obj+'_'):
                    support|=b=='table_collision'
                    touch|=b.startswith(('human_left_finger','human_right_finger','human_palm','gripper'))
            good=np.linalg.norm(p[:2]-goal[:2])<.025 and abs(p[2]-goal[2])<.025 and speed<.08 and support and not touch
            self.dwell[obj]=self.dwell[obj]+.05 if good else 0.;self.previous[obj]=p.copy()

    def decision(self,observation):
        held=observation.human_execution.get('object_measured_in_hand')
        pending=[t for t in self.targets if self.dwell[t['object_id']]<.2-1e-9]
        if held:
            target=next(t for t in self.targets if t['object_id']==held)
            intent,obj,dest='place',held,target['destination']
            reason=f'真实在手传感器报告{held}；将它放到{dest}并释放。'
        elif observation.human_execution.get('motor_phase') in {'release','grasp_retreat'}:
            intent,obj,dest='release',None,None
            reason='已进入释放／退手阶段，保持张手，不把未握持的放置请求重新启动。'
        elif pending:
            target=pending[0];intent,obj,dest='grasp',target['object_id'],None
            reason=f'其他已经放稳的目标无需重新抓取；现在抓取尚未放稳的{obj}。'
        else:
            intent,obj,dest='observe',None,None
            reason='所选物品已经释放并由桌面稳定支撑，维持布置并观察。'
        return {'long_term_intention':'将偏好物品整理到各自个人区域并维持布置',
            'personal_targets':self.targets,'plan':[f'维持{t["object_id"]}在{t["destination"]}' for t in self.targets],
            'intent':intent,'object_id':obj,'destination':dest,'reason':reason,
            'memory_note':'仅以当前真实位置、支撑与握持判断进展。','current_goal':reason,
            'wait_condition':'','message':'','negotiation_proposal':None}
