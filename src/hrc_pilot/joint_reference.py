"""可执行性参照的人／调度；禁止作为正式动态人条件使用。"""


class JointReference:
    def __init__(self,activity):
        self.activity=activity;self.stage='prepare';self.decisions=[]
        self.pending=None

    def decide(self,scene,robot_contribution):
        feedback=scene['own_execution'];done=feedback['completed_requests']
        choice={'action':'wait','object_id':None,'destination':None,'message':'','message_kind':'notice',
                'intention':'reference_fixed_activity','participation':'reference',
                'reason':'固定可执行性参照，不计神经人或动态策略效果。','memory':''}
        if self.pending is not None and self.pending in done:
            self.stage={'prepare':'robot','finish':'done'}[self.stage];self.pending=None
        if self.stage=='prepare' and self.pending is None:
            obj,dest={'snack_service':('akita_black_bowl_1','serving_ready'),
                      'drink_storage':('wine_bottle_1','drink_staging'),
                      'drawer_access':('plate_1','plate_1_personal')}[self.activity.key]
            choice.update(action='relocate',object_id=obj,destination=dest,message=f'I will prepare {obj} at {dest}.')
            self.pending=len(self.decisions)
        elif self.stage=='robot':
            choice['message']='Preparation is physically complete; please perform your contribution.'
            if robot_contribution:
                self.stage='finish'
                obj,dest={'snack_service':('akita_black_bowl_1','snack_delivery'),
                          'drink_storage':('cream_cheese_1','cream_cheese_1_personal'),
                          'drawer_access':('cream_cheese_1','drawer_storage')}[self.activity.key]
                choice.update(action='relocate',object_id=obj,destination=dest,
                              message=f'I will receive or finish the activity by moving {obj} to {dest}.')
                self.pending=len(self.decisions)
        row={'decision_id':len(self.decisions),'time_s':scene['time_s'],'private_input':{'scene':scene},
             'choice':choice,'raw_output':'','parse_error':None,'action_source':'fixed_feasibility_reference',
             'neural_inferences':0,'reference_stage':self.stage}
        self.decisions.append(row);return row

    @property
    def robot_permission(self):return self.stage=='robot'
