"""最终开发世界：保留dev2动力学，日志增加接触距离和双方位置。"""
import pybullet as p

from experiments.structure_v5.world_v2 import ClearanceReworkWorld


class AuditedReworkWorld(ClearanceReworkWorld):
    def state(self):
        state = super().state()
        contacts = p.getContactPoints(physicsClientId=self.client)
        state['contacts'] = [{'body_a': c[1], 'body_b': c[2], 'link_a': c[3], 'link_b': c[4],
            'position_a': c[5], 'position_b': c[6], 'contact_distance': c[8],
            'normal_force': c[9]} for c in contacts]
        return state
