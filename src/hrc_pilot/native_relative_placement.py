"""从当前碰撞几何读支撑面，提供物体相对放置；不移动物体或读取任务分数。"""
import numpy as np


def box_vertical_surface(center, axes, half_size, xy):
    """竖直射线与有姿态盒体的最高交点；射线不穿过盒体时返回 None。"""
    origin = np.r_[xy, center[2]]
    offset = axes.T @ (origin - center)
    direction = axes.T @ np.array([0., 0., 1.])
    lower, upper = -np.inf, np.inf
    for value, slope, size in zip(offset, direction, half_size):
        if abs(slope) < 1e-10:
            if abs(value) > size:
                return None
        else:
            ends = sorted(((-size - value) / slope, (size - value) / slope))
            lower, upper = max(lower, ends[0]), min(upper, ends[1])
    return float(origin[2] + upper) if lower <= upper else None


def central_support(env, receiver):
    """只公开具有盒体碰撞支撑面的可移动物体；不猜测 mesh 或柜内可达性。"""
    obj = env.env.objects_dict.get(receiver)
    if obj is None:
        return None
    xy = env.sim.data.body_xpos[env.env.obj_body_id[receiver]][:2]
    surfaces = []
    for name in obj.contact_geoms:
        geom = env.sim.model.geom_name2id(name)
        if env.sim.model.geom_type[geom] != 6:
            continue
        z = box_vertical_surface(env.sim.data.geom_xpos[geom],
                                 env.sim.data.geom_xmat[geom].reshape(3, 3),
                                 env.sim.model.geom_size[geom], xy)
        if z is not None:
            surfaces.append(z)
    return np.r_[xy, max(surfaces)] if surfaces else None


def object_bottom(env, name):
    """当前盒体碰撞包络底部；不将 body 原点等同物体底面。"""
    bottoms = []
    for geom_name in env.env.objects_dict[name].contact_geoms:
        geom = env.sim.model.geom_name2id(geom_name)
        if env.sim.model.geom_type[geom] != 6:
            raise ValueError('relative_placement_requires_box_collision_geometry')
        axes = env.sim.data.geom_xmat[geom].reshape(3, 3)
        radius = np.dot(np.abs(axes[2]), env.sim.model.geom_size[geom])
        bottoms.append(float(env.sim.data.geom_xpos[geom, 2] - radius))
    if not bottoms:
        raise ValueError('relative_placement_missing_collision_geometry')
    return min(bottoms)


def relative_destinations(env):
    return {f'on:{name}': {'receiver_object_id': name, 'support_xyz': point.tolist(),
                           'semantics': 'current central collision support; not a containment guarantee'}
            for name in env.env.objects_dict
            if (point := central_support(env, name)) is not None}


def receiver_contact(env, payload, receiver):
    model = env.sim.model
    payload_geoms = {model.geom_name2id(n) for n in env.env.objects_dict[payload].contact_geoms}
    receiver_geoms = {model.geom_name2id(n) for n in env.env.objects_dict[receiver].contact_geoms}
    return any((c.geom1 in payload_geoms and c.geom2 in receiver_geoms) or
               (c.geom2 in payload_geoms and c.geom1 in receiver_geoms)
               for c in (env.sim.data.contact[i] for i in range(env.sim.data.ncon)))
