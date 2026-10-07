"""只有人明确选择暂停才停止自己的运动；不自动给机器人让权。"""
from .contribution_human_executor import ContributionHumanExecutor


class PausableHumanExecutor(ContributionHumanExecutor):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.cancelled_requests=[]

    def accept_choice(self,choice,request_id):
        if choice['action']!='pause_current':return super().accept_choice(choice,request_id)
        if request_id==self.last_request:return
        previous=self.active_request if self.phase!='idle' else None
        self.last_request=request_id
        self.receipts.append({'physics_time_s':float(self.env.sim.data.time),'request_id':request_id,
            'choice':choice,'accepted':True,'error':None,'cancelled_motion_request_id':previous,
            'effect':'explicit_pause_retains_owned_item'})
        if previous is not None:self.cancelled_requests.append(previous)
        self.target=self.position().copy();self.body_target=self.body_base.copy()
        self.transfer_destination=None;self.phase='idle';self.accepted_intent='pause_current'
        self.active_request=request_id;self.completed_requests.append(request_id)

    def public_feedback(self):
        result=super().public_feedback();result['cancelled_requests']=self.cancelled_requests[-6:]
        return result
