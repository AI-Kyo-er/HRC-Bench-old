"""独立控制修复：保持v3.1冻结不变，只替换停车轨迹并审计全部物理步。"""
import pybullet as p

from experiments.physical.world import World


class SafeParkingWorld(World):
    def __init__(self, *args, **kwargs):
        self.contact_audit = {'robot_partner_ticks': 0, 'max_normal_force': 0,
                              'phases': {}, 'total_ticks': 0}
        self.parking_waypoint_errors = []
        super().__init__(*args, **kwargs)

    def simulate(self, ticks):
        for _ in range(ticks):
            super().simulate(1)
            self.contact_audit['total_ticks'] += 1
            contacts = p.getContactPoints(self.robot, self.partner, physicsClientId=self.client)
            if contacts:
                self.contact_audit['robot_partner_ticks'] += 1
                self.contact_audit['max_normal_force'] = max(
                    self.contact_audit['max_normal_force'], max(c[9] for c in contacts))
                phases = self.contact_audit['phases']
                phases[self.phase] = phases.get(self.phase, 0) + 1

    def command_joints(self, q):
        if self.phase == 'park':
            # 旧版本直达home的关节插值扫过占位块；先沿目标侧外移抬升，
            # 再在远离中央柱的位置收臂，最后电机回home。没有运行期reset。
            ee = p.getLinkState(self.robot, 11, physicsClientId=self.client)[4]
            side = -.40 if ee[1] < 0 else .40
            error1 = self.move([.52, side, .40], 'park_side_lift')
            error2 = self.move([.30, side, .45], 'park_retract')
            self.parking_waypoint_errors.append([error1, error2])
            self.phase = 'park_home'
            super().command_joints(q)
        else:
            super().command_joints(q)
