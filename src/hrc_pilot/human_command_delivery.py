"""保持神经请求身份，完成或失败后不把缓存动作重新当成新请求。"""
from dataclasses import asdict


class HumanCommandDelivery:
    def __init__(self):
        self.last_decision_id=None
        self.last_command=None

    def submit(self,actor,command,decision_id):
        if not isinstance(decision_id,int) or decision_id<0:
            raise ValueError('需要实际神经决定的非负序号')
        payload=asdict(command)
        same=decision_id==self.last_decision_id
        if same and payload!=self.last_command:
            raise ValueError('同一神经决定不能更改请求内容')
        if self.last_decision_id is not None and decision_id<self.last_decision_id:
            raise ValueError('不能递送更早的神经请求')
        if same and actor.phase in {'idle','holding','failed'}:
            return False
        self.last_decision_id=decision_id
        self.last_command=payload
        # 活动中的原语仍可跟踪移动物品；新NN请求允许显式重试。
        actor.accept(command)
        return True
