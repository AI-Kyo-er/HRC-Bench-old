"""日常情境分布：只给人新的事实／需要，不指定高层动作或分工。"""
from dataclasses import asdict,dataclass

import numpy as np


@dataclass(frozen=True)
class PrivateCue:
    time_s: float
    text: str
    source: str = 'external_private_information_not_action_command'


@dataclass(frozen=True)
class JointSituation:
    key: str
    initial_background: str
    initial_presence: str
    cue_windows: tuple[tuple[float,float,str], ...]
    intended_diagnostic: str

    def sample(self,seed):
        rng=np.random.default_rng(seed)
        cues=[PrivateCue(round(float(rng.uniform(lo,hi)),1),text) for lo,hi,text in self.cue_windows]
        return {'situation':self.key,'private_initial_background':self.initial_background,
                'initial_presence':self.initial_presence,'private_cues':[asdict(c) for c in cues],
                'seed':seed,'intended_diagnostic':self.intended_diagnostic,
                'interpretation':'情境配置不算行为覆盖；人是否参与、改变、表达或拒绝由在线模型决定。'}


SITUATIONS={s.key:s for s in [
    JointSituation('join','你刚在旁边处理个人事务，知道桌边有共同活动，但尚未承诺参与。','aside',
        ((12.,20.,'你收到消息：个人事务已经不需要继续处理，现在有空考虑桌边正在进行的共同活动。'),),
        '实际加入、建立分工与提供贡献；不由通知自动return'),
    JointSituation('leave_return','你愿意参与共同活动，但也在等待一位同事的紧急联系。','workspace',
        ((22.,30.,'同事联系你，想简短讨论一个与你有关的紧急且私人的问题；你重视这类谈话的隐私，可以根据当前进度决定如何处理。'),
         (58.,66.,'同事发来消息：问题已经解决，不再需要你继续处理。')),
        '实际暂离／交接及返回后的进度衔接，保留同一世界'),
    JointSituation('change_use','你起初希望按共同活动的正常用途准备物品。','workspace',
        ((32.,40.,'家人临时提出新的用途：准备好的东西需要留作马上取用，而不是按原安排存放或留在原位置。'),),
        '意图／用途变化后是否公开表达并调整实际活动'),
    JointSituation('detour','你愿意推进共同活动，也有一些需要兼顾的日常事情。','workspace',
        ((24.,32.,'来客发消息说很快会到，希望桌边有可取用的饮品；你需要考虑与当前工作的先后安排。'),
         (64.,72.,'来客通知行程改变，暂时不需要饮品安排。')),
        '是否临时处理另一需要、继续或恢复共同活动；不强制移物'),
    JointSituation('correction','你对物品用途和摆放有明确偏好，会考虑指出误解或自己接手。','workspace',
        ((30.,38.,'家人澄清：有一件东西是要留给自己使用的，原先收纳／交付的安排可能需要重新讨论。'),),
        '根据实际进度纠正、接管、交还或保留原安排，不预设机器人犯错'),
    JointSituation('robot_request','你愿意帮助，但是否接受额外工作取决于当前负担和请求内容。','workspace',
        ((20.,28.,'你收到自己的日程提醒：之后还有事情要处理，需要考虑剩余参与时间。'),),
        '实际机器人请求后的接受／修改／拒绝；该情境不制造机器人消息'),
]}
