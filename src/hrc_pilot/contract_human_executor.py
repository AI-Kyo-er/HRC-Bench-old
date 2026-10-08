"""声明的动作能力与执行一致；不让固定物件或超出手部工作区的物品被假搬运。"""
import numpy as np

from .relation_human_executor import RelationHumanExecutor


class ContractHumanExecutor(RelationHumanExecutor):
    def accept_choice(self,choice,request_id):
        if request_id==self.last_request:return
        error=None;obj=choice.get('object_id')
        if choice['action'] in {'pick','relocate'}:
            if obj not in self.object_q:error='object_not_movable_by_human'
            elif self.held!=obj:
                approach=self.object_position(obj)+[0,0,.06]
                if not (np.all(approach>=[-.7,-.4,.95]) and np.all(approach<=[.7,.9,1.5])):
                    error='object_outside_declared_pickup_workspace'
        if error:
            self.last_request=request_id
            self.receipts.append({'physics_time_s':float(self.env.sim.data.time),'request_id':request_id,
                                  'choice':choice,'accepted':False,'error':error})
            return
        return super().accept_choice(choice,request_id)
