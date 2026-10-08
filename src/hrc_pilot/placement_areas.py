"""只解算已选区域内的放置参数；不移动世界、替换目标或选择任务策略。"""
from itertools import product

import numpy as np

from .activity_workspace import object_collision_bounds


class PlacementAreaFull(ValueError):
    pass


def table_placement_areas(workspace):
    center = np.asarray(workspace['zone_surface_positions']['snack_delivery'])
    return {'snack_delivery': {
        'center_xy_min': (center[:2] - [.16, .12]).tolist(),
        'center_xy_max': (center[:2] + [.16, .11]).tolist(),
        'surface_z_m': float(center[2]), 'support_geom': 'table_collision',
        'scope': '物品中心可在该范围内；完整碰撞包围盒须留在真实桌面内，避开当前物品和固定物件。'}}


def area_placement(model, data, object_id, area, obstacle_names, *, payload_names=(),
                   preferred_xy=None, clearance_m=.015, fixed_xy=None):
    """当前盒几何的保守解算，允许物品中心在区域中分开放置。"""
    minimum = np.asarray(area['center_xy_min'], dtype=float)
    maximum = np.asarray(area['center_xy_max'], dtype=float)
    if minimum.shape != (2,) or maximum.shape != (2,) or not np.isfinite([minimum, maximum]).all() or np.any(minimum > maximum):
        raise ValueError('区域中心边界须为有限且有序的二维坐标')
    if not np.isfinite(clearance_m) or clearance_m < 0:
        raise ValueError('间距须有限且非负')
    support = model.geom_name2id(area['support_geom'])
    if int(model.geom_type[support]) != 6:
        raise ValueError('区域支撑须为实际碰撞盒')
    rotation = data.geom_xmat[support].reshape(3, 3)
    if np.max(np.abs(rotation[2] - [0, 0, 1])) > 1e-6:
        raise ValueError('当前区域只支持水平支撑')
    surface_z = float(data.geom_xpos[support][2] + model.geom_size[support][2])
    if abs(surface_z - area['surface_z_m']) > 1e-6:
        raise ValueError('声明表面与实际碰撞面不符')
    origin = np.asarray(data.body_xpos[model.body_name2id(object_id + '_main')])
    group = list(dict.fromkeys([object_id, *payload_names]))
    bounds = [object_collision_bounds(model, data, name) for name in group]
    lower = np.min([b[0] for b in bounds], axis=0) - origin
    upper = np.max([b[1] for b in bounds], axis=0) - origin
    z = surface_z - lower[2] + .002
    obstacles = {name: object_collision_bounds(model, data, name)
                 for name in obstacle_names if name not in group}
    preferred = origin[:2] if preferred_xy is None else np.asarray(preferred_xy, dtype=float)
    if preferred.shape != (2,) or not np.isfinite(preferred).all():
        raise ValueError('优先点须是有限二维坐标')

    def feasible(xy):
        if np.any(xy < minimum - 1e-9) or np.any(xy > maximum + 1e-9):
            return False
        lo, hi = np.r_[xy, z] + lower, np.r_[xy, z] + upper
        # 虚拟区域限定中心；真实支撑边界限定整个碰撞占用，包含旋转桌面。
        for corner in product(*zip(lo[:2], hi[:2])):
            local = rotation[:2, :2].T @ (np.asarray(corner) - data.geom_xpos[support][:2])
            if np.any(np.abs(local) + clearance_m > model.geom_size[support][:2] + 1e-9):
                return False
        for other_lo, other_hi in obstacles.values():
            if lo[2] >= other_hi[2] or hi[2] <= other_lo[2]:
                continue
            if np.all(hi[:2] + clearance_m > other_lo[:2]) and np.all(lo[:2] - clearance_m < other_hi[:2]):
                return False
        return True

    if fixed_xy is not None:
        point = np.asarray(fixed_xy, dtype=float)
        if point.shape != (2,) or not np.isfinite(point).all() or not feasible(point):
            raise PlacementAreaFull('此前选定的区域放置点当前不可用')
        return {'object_id': object_id, 'body_target_xyz': [float(point[0]), float(point[1]), z],
                'support_geom': area['support_geom'], 'payload_names': list(payload_names),
                'clearance_m': clearance_m, 'scope': '只验证此前选定点，不另选目标。'}
    axes = []
    for axis in range(2):
        candidates = [minimum[axis], maximum[axis], np.clip(preferred[axis], minimum[axis], maximum[axis]),
                      np.clip(origin[axis], minimum[axis], maximum[axis])]
        candidates.extend(np.linspace(minimum[axis], maximum[axis], 17))
        for lo, hi in obstacles.values():
            candidates.extend([lo[axis] - upper[axis] - clearance_m - 1e-7,
                               hi[axis] - lower[axis] + clearance_m + 1e-7])
        axes.append(sorted(set(float(x) for x in candidates if minimum[axis] <= x <= maximum[axis])))
    candidates = sorted(product(*axes), key=lambda xy: (float(np.linalg.norm(np.asarray(xy) - preferred)), xy))
    for xy in candidates:
        if feasible(np.asarray(xy)):
            return {'object_id': object_id, 'body_target_xyz': [float(xy[0]), float(xy[1]), z],
                    'support_geom': area['support_geom'], 'payload_names': list(payload_names),
                    'clearance_m': clearance_m,
                    'scope': '已选区域内当前占用的放置参数；不选择下一贡献，不保证后续他方运动或完整路径。'}
    raise PlacementAreaFull('已选区域没有符合当前占用和桌边约束的放置点')
