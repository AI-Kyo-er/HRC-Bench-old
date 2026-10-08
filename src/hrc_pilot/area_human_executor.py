"""区域内放置兑现模型选择；无空位时拒绝，不替模型移动其他物品。"""
from copy import deepcopy

import numpy as np

from .placement_areas import area_placement, PlacementAreaFull
from .activity_workspace import body_target_on_surface
from .surface_human_executor import SurfaceDestinations, SurfaceHumanExecutor


class AreaDestinations(SurfaceDestinations):
    def __getitem__(self, name):
        if name not in self.actor.placement_areas:
            return super().__getitem__(name)
        choice = self.actor._table_input_choice
        obj = (choice.get('object_id') or self.actor.held) if choice else self.actor.object_id
        if obj is None:
            return self.public_regions[name]
        target = self.actor.area_targets[(obj, name)]['body_target_xyz']
        return body_target_on_surface(self.actor.env.sim.model, self.actor.env.sim.data, obj,
                                      [*target[:2], self.actor.placement_areas[name]['surface_z_m']])


class AreaHumanExecutor(SurfaceHumanExecutor):
    def __init__(self, env, regions, **kwargs):
        super().__init__(env, regions, **kwargs)
        self.placement_areas = env.env._hrc_placement_areas
        self.area_targets = {}
        self.regions = AreaDestinations(self, regions, self.regions.surface_names)

    def _payload_names(self, obj):
        if self.held == obj:
            return [name for name in self.carried_offsets if name != obj]
        states = getattr(self.env.env, 'object_states_dict', getattr(self.env.env, 'object_states', {}))
        names = []
        if obj in states:
            for name in self.object_q:
                if name == obj or name not in states or not states[obj].check_ontop(states[name]):
                    continue
                robot_touch = False
                for i in range(self.env.sim.data.ncon):
                    c = self.env.sim.data.contact[i]
                    pair = [self.env.sim.model.geom_id2name(g) or '' for g in [c.geom1, c.geom2]]
                    robot_touch |= any(g.startswith(name + '_') for g in pair) and any(g.startswith('gripper') for g in pair)
                if not robot_touch:
                    names.append(name)
        return names

    def accept_choice(self, choice, request_id):
        if request_id == self.last_request:
            return
        obj = choice.get('object_id') or (self.held if choice['action'] == 'place' else None)
        dest = choice.get('destination')
        area_choice = choice['action'] in {'place', 'relocate'} and dest in self.placement_areas and obj in self.object_q
        if area_choice:
            continued = self.phase != 'idle' and self.object_id == obj and self.transfer_destination == dest
            if not continued or (obj, dest) not in self.area_targets:
                area = self.placement_areas[dest]
                current = self.object_position(obj)[:2]
                within = np.all(current >= area['center_xy_min']) and np.all(current <= area['center_xy_max'])
                preferred = current if within else self.regions.public_regions[dest][:2]
                try:
                    target = area_placement(self.env.sim.model, self.env.sim.data, obj, area,
                                            list(self.env.env.obj_body_id), payload_names=self._payload_names(obj),
                                            preferred_xy=preferred)
                    target['planning_physics_time_s'] = float(self.env.sim.data.time)
                    target['preferred_xy'] = list(preferred)
                except PlacementAreaFull:
                    self.last_request = request_id
                    self.receipts.append({'physics_time_s': float(self.env.sim.data.time),
                        'request_id': request_id, 'choice': choice, 'accepted': False,
                        'error': 'destination_area_has_no_free_placement'})
                    return
                self.area_targets[(obj, dest)] = target
        super().accept_choice(choice, request_id)
        if area_choice and self.receipts[-1]['accepted']:
            target = deepcopy(self.area_targets[(obj, dest)])
            self.receipts[-1]['area_placement'] = target
            self.receipts[-1]['table_surface_placement']['resolved_object_body_xyz'] = self.regions[dest]

    def physics_step(self):
        dest = self.transfer_destination
        if dest in self.placement_areas and self.phase in {'transfer_lower', 'area_target_unavailable'}:
            target = self.area_targets[(self.object_id, dest)]
            try:
                area_placement(self.env.sim.model, self.env.sim.data, self.object_id,
                               self.placement_areas[dest], list(self.env.env.obj_body_id),
                               payload_names=self._payload_names(self.object_id), fixed_xy=target['body_target_xyz'][:2])
            except PlacementAreaFull:
                self.phase = 'area_target_unavailable'; self.target = self.position().copy()
            else:
                if self.phase == 'area_target_unavailable':
                    self.phase = 'transfer_lower'
        super().physics_step()

    def public_feedback(self):
        result = super().public_feedback()
        result['selected_area_placement'] = deepcopy(self.area_targets.get((self.object_id, self.transfer_destination)))
        if self.phase == 'area_target_unavailable':
            result['execution_blocked_reason'] = 'selected_area_point_occupied'
        return result
