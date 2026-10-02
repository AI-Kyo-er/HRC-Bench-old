"""统一保守策略：不读取占位约定或yield反馈，只缓存初始目标。"""


class BlindYieldThenDetour:
    def __init__(self):
        self.initial_goals = None
        self.yielded_once = False

    def choose(self, observation):
        if self.initial_goals is None:
            # 唯一历史读取：已接受的初始物品目标。之后不读取任何history。
            self.initial_goals = dict(next(event['goals'] for event in observation['history']
                                          if event['kind'] == 'accepted_outer'))
        if not self.yielded_once:
            self.yielded_once = True
            return 'yield'
        for item in ('blue', 'green', 'red'):
            target = self.initial_goals[item]
            if target not in observation['physical_placements'][item]:
                return f'careful_{item}_{target}'
        raise ValueError('初始公开目标均已满足。')
