from copy import deepcopy

import numpy as np
import pytest

from hrc_pilot.placement_areas import area_placement, PlacementAreaFull
from test_activity_workspace import scene


def area():
    return {'center_xy_min': [-.2, -.1], 'center_xy_max': [.2, .3],
            'surface_z_m': .9, 'support_geom': 'table_collision'}


def test_current_occupant_causes_separate_placement_without_moving_other_objects():
    sim = scene(); before = sim.data.qpos.copy(); a = area(); original = deepcopy(a)
    result = area_placement(sim.model, sim.data, 'packet', a, ['bowl', 'packet'], preferred_xy=[0., 0.])
    assert np.linalg.norm(np.asarray(result['body_target_xyz'])[:2]) > .08
    np.testing.assert_array_equal(sim.data.qpos, before)
    assert a == original


def test_full_region_rejects_instead_of_moving_an_occupant_or_choosing_another_goal():
    sim = scene(); a = area(); a.update(center_xy_min=[0., 0.], center_xy_max=[0., 0.])
    with pytest.raises(PlacementAreaFull):
        area_placement(sim.model, sim.data, 'packet', a, ['bowl'])


def test_support_height_and_full_footprint_are_checked_and_payload_is_excluded():
    sim = scene(); a = area(); a['surface_z_m'] = 1.
    with pytest.raises(ValueError, match='碰撞面'):
        area_placement(sim.model, sim.data, 'packet', a, [])
    a = area(); a.update(center_xy_min=[.49, .0], center_xy_max=[.49, .0])
    with pytest.raises(PlacementAreaFull):
        area_placement(sim.model, sim.data, 'bowl', a, [])
    result = area_placement(sim.model, sim.data, 'bowl', area(), ['packet'], payload_names=['packet'])
    assert result['payload_names'] == ['packet']
