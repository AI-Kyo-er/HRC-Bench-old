"""可靠兑现当前被选中的贡献；取放高度随真实目标更新，不选择下一贡献。"""
import numpy as np

from .settled_placement_human import SettledPlacementHuman


class ContributionHumanExecutor(SettledPlacementHuman):
    def accept_choice(self,choice,request_id):
        if request_id!=self.last_request and choice['action']=='pick' and self.held==choice.get('object_id'):
            self.last_request=request_id
            self.receipts.append({'physics_time_s':float(self.env.sim.data.time),'request_id':request_id,
                'choice':choice,'accepted':True,'error':None,'effect':'already_holding_requested_object'})
            # “自己持有”是明确的新贡献，停止旧放置；wait才继续旧运动。
            self.accepted_intent='pick';self.active_request=request_id;self.object_id=self.held
            self.transfer_destination=None;self.target=self.position().copy();self.phase='idle'
            self.completed_requests.append(request_id)
            return
        super().accept_choice(choice,request_id)

    def physics_step(self):
        if self.phase=='transfer_raise' and self.transfer_destination is not None:
            self.target[2]=max(1.35,float(self.regions[self.transfer_destination][2]-self.offset[2]+.08))
        super().physics_step()

    def _complete(self):
        if self.phase in {'return','away'} and np.linalg.norm(self.body_base-self.body_target)>.004:return
        super()._complete()
