import numpy as np

from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
from hrc_pilot.goal_regions import GOAL_SURFACES, surface_for, visible_goal_scenario


def bounds_at(point):
    return np.asarray(point) + np.array([[-0.025, -0.025, -0.05], [0.025, 0.025, 0.05]])


def test_all_named_goal_anchors_are_inside_their_visible_surface():
    for destination, point in CONTINUOUS_SCENARIOS['relay'].regions.items():
        assert surface_for(destination).contains(bounds_at(point))


def test_partial_footprint_or_wrong_height_cannot_count_as_placement():
    surface = GOAL_SURFACES['tray']
    assert surface.contains(bounds_at([0.42, -0.30, 0.81]))
    assert not surface.contains(bounds_at([0.42, -0.18, 0.81]))
    assert not surface.contains(bounds_at([0.42, -0.30, 0.05]))


def test_visible_layout_is_deterministic_separated_and_not_already_placed():
    for seed in range(32):
        a = visible_goal_scenario(CONTINUOUS_SCENARIOS['relay'], seed)
        b = visible_goal_scenario(CONTINUOUS_SCENARIOS['relay'], seed)
        assert a.objects == b.objects
        for index, item in enumerate(a.objects):
            assert not any(surface.contains(bounds_at(item.position)) for surface in GOAL_SURFACES.values())
            for other in a.objects[index + 1:]:
                assert np.linalg.norm(np.array(item.position[:2]) - other.position[:2]) >= 0.075
