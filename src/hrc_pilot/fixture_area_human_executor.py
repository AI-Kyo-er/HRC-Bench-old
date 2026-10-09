"""家具面执行适配：只解算当前选定贡献，不按生活情境选择动作。"""
from contextlib import contextmanager
from copy import deepcopy
from itertools import product

import numpy as np

from .area_human_executor import AreaHumanExecutor
from .surface_human_executor import SurfaceHumanExecutor
from .human_relation_targets import central_support_surface
from .fixture_surface_placement import horizontal_fixture_surface, fixture_surface_placement
from .placement_areas import PlacementAreaFull


CONTRACT = 'selected_fixture_surface_with_occupancy_v1'


def fixture_placement_areas(model, data, object_names, regions):
    fixture = 'wooden_cabinet_1'
    if fixture not in object_names:
        return {}
    support = central_support_surface(model, data, fixture)
    if support is None:
        return {}
    surface = horizontal_fixture_surface(model, data, fixture, support['collision_geom'])
    axes = np.asarray(surface['local_xy_axes_in_world'])
    half = np.asarray(surface['local_half_extents_xy'])
    center = np.asarray(surface['surface_center_xyz'])
    corners = np.asarray([center[:2] + axes @ p for p in product(*zip(-half, half))])
    area = {'center_xy_min': corners.min(axis=0).tolist(),
        'center_xy_max': corners.max(axis=0).tolist(), 'surface_z_m': float(center[2]),
        'support_geom': surface['support_geom'], 'fixture_surface': surface,
        'scope': '所选家具表面，中心范围只是外包围盒；整个物品必须通过实际面边界与占位验证。'}
    return {name: deepcopy(area) for name in regions
            if name.endswith('_on_cabinet') and name.removesuffix('_on_cabinet') in object_names}


class FixtureAreaHumanExecutor(AreaHumanExecutor):
    registered_areas = None

    def __init__(self, env, regions, **kwargs):
        if not any(name.endswith('_on_cabinet') for name in regions):
            from .human_support_targets import update_human_support_targets
            update_human_support_targets(env, regions)
        extra = fixture_placement_areas(env.sim.model, env.sim.data, list(env.env.obj_body_id), regions)
        env.env._hrc_placement_areas.update(extra)
        super().__init__(env, regions, **kwargs)
        self.fixture_areas = extra
        type(self).registered_areas = deepcopy(self.placement_areas)

    def accept_choice(self, choice, request_id):
        dest = choice.get('destination')
        obj = choice.get('object_id') or (self.held if choice['action'] == 'place' else None)
        if not (choice['action'] in {'place', 'relocate'} and dest in self.fixture_areas and obj in self.object_q):
            return super().accept_choice(choice, request_id)
        if request_id == self.last_request:
            return
        continued = self.phase != 'idle' and self.object_id == obj and self.transfer_destination == dest
        if not continued or (obj, dest) not in self.area_targets:
            surface = self.fixture_areas[dest]['fixture_surface']
            preferred = self.object_position(obj)[:2]
            payloads = self._payload_names(obj)
            try:
                target = fixture_surface_placement(self.env.sim.model, self.env.sim.data, obj, surface,
                    list(self.env.env.obj_body_id), payload_names=payloads, preferred_xy=preferred)
            except PlacementAreaFull:
                self.last_request = request_id
                self.receipts.append({'physics_time_s': float(self.env.sim.data.time), 'request_id': request_id,
                    'choice': deepcopy(choice), 'accepted': False, 'error': 'destination_area_has_no_free_placement',
                    'fixture_surface_rejection': {'destination': dest, 'fixture_id': surface['fixture_id'],
                        'payload_names': payloads, 'preferred_xy': preferred.tolist(),
                        'scope': '保守支撑边界与当前占位下没有安全候选；不移动物品、不选择替代目标。'}})
                return
            target.update(planning_physics_time_s=float(self.env.sim.data.time), preferred_xy=preferred.tolist())
            self.area_targets[(obj, dest)] = target
        # 家具面不冒充原table_surface_positions；原区域／目标锚点不改写。
        SurfaceHumanExecutor.accept_choice(self, choice, request_id)
        if self.receipts[-1]['accepted']:
            self.receipts[-1]['fixture_surface_placement'] = deepcopy(self.area_targets[(obj, dest)])

    def physics_step(self):
        dest = self.transfer_destination
        if dest not in self.fixture_areas:
            return super().physics_step()
        if self.phase in {'transfer_lower', 'area_target_unavailable'}:
            target = self.area_targets[(self.object_id, dest)]
            try:
                fixture_surface_placement(self.env.sim.model, self.env.sim.data, self.object_id,
                    self.fixture_areas[dest]['fixture_surface'], list(self.env.env.obj_body_id),
                    payload_names=self._payload_names(self.object_id), fixed_xy=target['body_target_xyz'][:2])
            except PlacementAreaFull:
                self.phase = 'area_target_unavailable'
                self.target = self.position().copy()
            else:
                if self.phase == 'area_target_unavailable':
                    self.phase = 'transfer_lower'
        SurfaceHumanExecutor.physics_step(self)


@contextmanager
def fixture_executor_override():
    import hrc_pilot.area_human_executor as module
    original = module.AreaHumanExecutor
    FixtureAreaHumanExecutor.registered_areas = None
    module.AreaHumanExecutor = FixtureAreaHumanExecutor
    try:
        yield
    finally:
        module.AreaHumanExecutor = original
