"""独立neutral检查盘；沿用v5动力学控制，不改变旧世界。"""
from experiments.structure_v5.world_v3 import AuditedReworkWorld


class NeutralWorld(AuditedReworkWorld):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 环境初始化期间创建静态盘，运行期物品仍仅由电机/摩擦移动。
        self.neutral_tray = self.box([.06, .06, .005], [.65, 0, .005], 0, (.55, .65, .75, 1))
        for y in (-.06, .06):
            self.box([.06, .005, .009], [.65, y, .019], 0, (.45, .55, .65, 1))

    def goal(self, item, destination):
        if destination == 'neutral':
            if item != 'blue':
                raise ValueError('当前neutral检查能力只适用于blue。')
            return [.65, 0, .036]
        return super().goal(item, destination)
