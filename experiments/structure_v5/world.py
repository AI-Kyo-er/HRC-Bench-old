"""修复来源在托盘内时的绕行取物接近；旧v3.2实现不改。"""
import pybullet as p

from experiments.physical_v3_2.world import SafeParkingWorld


class ReworkApproachWorld(SafeParkingWorld):
    def pick_place(self, item, destination, route='direct'):
        source = p.getBasePositionAndOrientation(self.objects[item], physicsClientId=self.client)[0]
        preapproach_errors = []
        # 公开几何条件：托盘一侧的物品且中央通道实际占位。
        # 从home直接IK插值到盘内来源会扫过伙伴；逆向使用停车侧轨迹。
        if route == 'careful' and self.direct_blocked() and source[0] > .54:
            side = -.40 if source[1] < 0 else .40
            self.set_grip(.04, 'rework_open')
            for target, phase in [([.30, side, .45], 'rework_side_retract'),
                                  ([.52, side, .40], 'rework_side_lift'),
                                  ([source[0], side, .26], 'rework_side_approach'),
                                  ([source[0], source[1], .26], 'rework_above_source')]:
                preapproach_errors.append(self.move(target, phase))
        result = super().pick_place(item, destination, route)
        result['preapproach_errors'] = preapproach_errors
        return result
