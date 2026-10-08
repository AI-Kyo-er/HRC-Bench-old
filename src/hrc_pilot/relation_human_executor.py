"""只兑现所选关系贡献；目标不可用时报告受阻，保留持物与已完成进度。"""
import numpy as np

from .pausable_human_executor import PausableHumanExecutor


class RelationHumanExecutor(PausableHumanExecutor):
    def accept_choice(self,choice,request_id):
        previous=self.active_request if self.phase!='idle' else None
        super().accept_choice(choice,request_id)
        if self.receipts and self.receipts[-1]['request_id']==request_id and self.receipts[-1]['accepted']:
            if previous is not None and self.active_request==previous:
                self.receipts[-1]['continues_motion_request_id']=previous
            elif previous is not None and request_id!=previous:
                if previous not in self.cancelled_requests:self.cancelled_requests.append(previous)
                self.receipts[-1]['superseded_motion_request_id']=previous

    def physics_step(self):
        destination=self.transfer_destination
        if destination and '__' in destination:
            available=getattr(self.env.env,'_hrc_region_accessibility',{}).get(destination,False)
            if not available and self.phase.startswith('transfer_') and self.phase!='transfer_retreat':
                self.blocked_phase=self.phase
                self.phase='relation_target_unavailable'
                self.target=self.position().copy()
            elif available and self.phase=='relation_target_unavailable':
                self.phase=self.blocked_phase
                self.target=np.asarray(self.regions[destination])-self.offset
                if self.phase=='transfer_raise':self.target[2]=max(1.35,self.target[2]+.08)
                elif self.phase=='transfer_translate':self.target[2]=max(1.35,float(self.target[2]+.08))
        super().physics_step()

    def public_feedback(self):
        value=super().public_feedback()
        value['selected_relation_target']=getattr(self.env.env,'_hrc_relation_targets',{}).get(self.transfer_destination)
        value['execution_blocked_reason']='reference_support_unavailable' if self.phase=='relation_target_unavailable' else None
        return value
