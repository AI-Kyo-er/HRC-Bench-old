"""来源侧冗余关节偏置，避免盘内抓取时前臂贴近伙伴顶部。"""
import numpy as np
import pybullet as p

from experiments.structure_v5.world import ReworkApproachWorld


class ClearanceReworkWorld(ReworkApproachWorld):
    def __init__(self, *args, **kwargs):
        self.rework_source_side = None
        self.object_partner_audit = {'ticks': 0, 'max_normal_force': 0, 'phases': {}}
        super().__init__(*args, **kwargs)

    def simulate(self, ticks):
        for _ in range(ticks):
            super().simulate(1)
            contacts = [c for body in self.objects.values()
                        for c in p.getContactPoints(body, self.partner, physicsClientId=self.client)]
            if contacts:
                self.object_partner_audit['ticks'] += 1
                self.object_partner_audit['max_normal_force'] = max(
                    self.object_partner_audit['max_normal_force'], max(c[9] for c in contacts))
                phases = self.object_partner_audit['phases']
                phases[self.phase] = phases.get(self.phase, 0) + 1

    def pick_place(self, item, destination, route='direct'):
        source = p.getBasePositionAndOrientation(self.objects[item], physicsClientId=self.client)[0]
        if route == 'careful' and self.direct_blocked() and source[0] > .54:
            self.rework_source_side = -1 if source[1] < 0 else 1
        try:
            result = super().pick_place(item, destination, route)
            result['object_partner_audit'] = dict(self.object_partner_audit)
            return result
        finally:
            self.rework_source_side = None

    def move(self, target, phase, ticks=160):
        if self.rework_source_side is None or not (phase.startswith('rework_') or
                                                  phase in ('approach', 'descend', 'lift')):
            return super().move(target, phase, ticks)
        self.phase = phase
        start = np.array(p.getLinkState(self.robot, 11, physicsClientId=self.client)[4])
        joints = list(range(7)) + [9, 10]
        info = [p.getJointInfo(self.robot, j, physicsClientId=self.client) for j in joints]
        lower, upper = [x[8] for x in info], [x[9] for x in info]
        rests = [p.getJointState(self.robot, j, physicsClientId=self.client)[0] for j in joints]
        # Panda第1/3关节提供冗余侧向姿态偏置，不改变末端抓取姿态或占位体。
        rests[0] = self.rework_source_side * .5
        rests[2] = self.rework_source_side * .5
        for t in range(1, ticks + 1):
            xyz = start + (np.asarray(target) - start) * t / ticks
            q = p.calculateInverseKinematics(self.robot, 11, xyz, self.orientation,
                lowerLimits=lower, upperLimits=upper,
                jointRanges=[hi - lo for lo, hi in zip(lower, upper)], restPoses=rests,
                maxNumIterations=80, residualThreshold=1e-5, physicsClientId=self.client)
            self.command_joints(q)
            self.simulate(1)
        self.simulate(80)
        return float(np.linalg.norm(np.array(p.getLinkState(self.robot, 11,
                                       physicsClientId=self.client)[4]) - target))
