"""解算人已选家具支撑面上的空位；无空位拒绝，不移动其他对象或选策略。"""
from itertools import product

import numpy as np

from .activity_workspace import object_collision_bounds
from .human_relation_targets import collision_geoms
from .placement_areas import PlacementAreaFull


def horizontal_fixture_surface(model, data, fixture_id, geom_name):
    gid = model.geom_name2id(geom_name)
    if gid not in collision_geoms(model, fixture_id) or int(model.geom_type[gid]) != 6:
        raise ValueError('支撑须为所选家具的真实碰撞盒')
    rotation = np.asarray(data.geom_xmat[gid]).reshape(3, 3)
    vertical = int(np.argmax(np.abs(rotation[2])))
    if abs(abs(rotation[2, vertical]) - 1) > 1e-6:
        raise ValueError('仅支持当前水平的家具表面')
    lateral = [i for i in range(3) if i != vertical]
    center = np.asarray(data.geom_xpos[gid], dtype=float).copy()
    center[2] += float(model.geom_size[gid, vertical])
    return {'fixture_id': fixture_id, 'support_geom': geom_name,
        'surface_center_xyz': center.tolist(),
        'local_xy_axes_in_world': rotation[:2, lateral].tolist(),
        'local_half_extents_xy': model.geom_size[gid, lateral].tolist(),
        'scope': '原碰撞盒的水平上表面；不把家具整体包围盒当空置区域。'}


def fixture_surface_placement(model, data, object_id, surface, obstacle_names, *,
                              payload_names=(), preferred_xy=None, clearance_m=.005, fixed_xy=None):
    # 重新核对实际表面，避免沿用已移动家具的旧参数。
    actual = horizontal_fixture_surface(model, data, surface['fixture_id'], surface['support_geom'])
    for key in ['surface_center_xyz', 'local_xy_axes_in_world', 'local_half_extents_xy']:
        if not np.allclose(actual[key], surface[key], atol=1e-6, rtol=0):
            raise ValueError('家具表面位置已改变，需要重新观察')
    if not np.isfinite(clearance_m) or clearance_m < 0:
        raise ValueError('间距须为有限非负值')
    center = np.asarray(actual['surface_center_xyz'])
    axes = np.asarray(actual['local_xy_axes_in_world'])
    halves = np.asarray(actual['local_half_extents_xy'])
    origin = np.asarray(data.body_xpos[model.body_name2id(object_id + '_main')])
    group = list(dict.fromkeys([object_id, *payload_names]))
    bounds = [object_collision_bounds(model, data, name) for name in group]
    lower = np.min([b[0] for b in bounds], axis=0) - origin
    upper = np.max([b[1] for b in bounds], axis=0) - origin
    z = float(center[2] - lower[2] + .002)
    obstacles = []
    for name in dict.fromkeys(obstacle_names):
        if name in group:
            continue
        if name != surface['fixture_id']:
            obstacles.append(object_collision_bounds(model, data, name))
            continue
        # 只排除支撑盒，保留同一家具的其他真实碰撞件，避免误判为全空。
        for gid in collision_geoms(model, name):
            if model.geom_id2name(gid) == surface['support_geom']:
                continue
            if int(model.geom_type[gid]) != 6:
                raise ValueError('所选家具含未支持的非盒碰撞件，不能认证空位')
            half = np.abs(data.geom_xmat[gid].reshape(3, 3)) @ model.geom_size[gid]
            obstacles.append((data.geom_xpos[gid] - half, data.geom_xpos[gid] + half))
    preferred = center[:2] if preferred_xy is None else np.asarray(preferred_xy, dtype=float)
    if preferred.shape != (2,) or not np.isfinite(preferred).all():
        raise ValueError('优先点须为有限二维坐标')

    def feasible(xy):
        lo, hi = np.r_[xy, z] + lower, np.r_[xy, z] + upper
        for corner in product(*zip(lo[:2], hi[:2])):
            local = axes.T @ (np.asarray(corner) - center[:2])
            if np.any(np.abs(local) + clearance_m > halves + 1e-9):
                return False
        for other_lo, other_hi in obstacles:
            if lo[2] >= other_hi[2] or hi[2] <= other_lo[2]:
                continue
            if np.all(hi[:2] + clearance_m > other_lo[:2]) and np.all(lo[:2] - clearance_m < other_hi[:2]):
                return False
        return True

    def result(xy):
        return {'object_id': object_id, 'body_target_xyz': [*map(float, xy), z],
            'support_geom': surface['support_geom'], 'fixture_id': surface['fixture_id'],
            'payload_names': list(payload_names), 'clearance_m': clearance_m,
            'scope': '只兑现已选家具表面；不挪动占位对象，不替换目标，不保证路径或任务成功。'}

    if fixed_xy is not None:
        point = np.asarray(fixed_xy, dtype=float)
        if point.shape != (2,) or not np.isfinite(point).all() or not feasible(point):
            raise PlacementAreaFull('此前选择的家具表面点已被占用或不能容纳该物品')
        return result(point)
    local_preferred = axes.T @ (preferred - center[:2])
    candidates = [np.clip(local_preferred, -halves, halves)]
    candidates.extend(np.asarray(x) for x in product(*(np.linspace(-h, h, 33) for h in halves)))
    candidates.sort(key=lambda p: (float(np.linalg.norm(p-local_preferred)), tuple(p)))
    for local in candidates:
        xy = center[:2] + axes @ local
        if feasible(xy):
            return result(xy)
    raise PlacementAreaFull('已选家具表面没有可容纳该物品的当前空位')
