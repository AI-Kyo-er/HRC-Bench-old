"""可见工作表面与公开任务语义共用的几何定义。"""
from dataclasses import asdict, dataclass, replace

import numpy as np


@dataclass(frozen=True)
class GoalSurface:
    name: str
    center: tuple[float, float, float]
    size_xy: tuple[float, float]
    color: tuple[float, float, float]

    def contains(self, aabb, tolerance_m=0.001, height_tolerance_m=0.025):
        bounds = np.asarray(aabb, dtype=float)
        if bounds.shape != (2, 3) or not np.isfinite(bounds).all():
            return False
        center, half = np.array(self.center[:2]), np.array(self.size_xy) / 2
        return bool(np.all(bounds[0, :2] >= center - half - tolerance_m)
                    and np.all(bounds[1, :2] <= center + half + tolerance_m)
                    and abs(bounds[0, 2] - self.center[2]) <= height_tolerance_m)


GOAL_SURFACES = {
    'tray': GoalSurface('蓝色收纳底板', (0.42, -0.30, 0.76), (0.50, 0.24), (0.25, 0.43, 0.72)),
    'keep': GoalSurface('绿色留用底板', (0.42, 0.24, 0.76), (0.50, 0.24), (0.37, 0.68, 0.48)),
}


def surface_for(destination):
    return GOAL_SURFACES.get(str(destination).split('_', 1)[0])


def visible_goal_scenario(scenario, seed=0):
    """声明可见区域目标并生成分散的待处理物体，初态不在目标表面内。"""
    rng = np.random.default_rng(seed)
    centers = {'red': (0.46, 0.045, 0.82), 'blue': (0.35, -0.055, 0.82), 'green': (0.29, 0.060, 0.82)}
    while True:
        objects = tuple(replace(item, position=tuple(np.array(centers[item.name]) +
                                                    np.r_[rng.uniform(-0.035, 0.035), rng.uniform(-0.025, 0.025), 0]))
                        for item in scenario.objects)
        if all(np.linalg.norm(np.array(a.position[:2]) - b.position[:2]) >= 0.075
               for index, a in enumerate(objects) for b in objects[index + 1:]):
            break
    return replace(scenario, objects=objects, assets={**scenario.assets,
                   'placement_geometry': 'visible_surface_footprint',
                   'public_goal_surfaces': {key: asdict(value) for key, value in GOAL_SURFACES.items()}})
