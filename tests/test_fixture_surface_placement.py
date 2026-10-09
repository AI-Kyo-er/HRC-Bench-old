import numpy as np
import pytest
from robosuite.utils.binding_utils import MjSim

from hrc_pilot.fixture_surface_placement import horizontal_fixture_surface, fixture_surface_placement
from hrc_pilot.placement_areas import PlacementAreaFull


def scene(occupied=False):
    # 上表面的法向在局部x轴，覆盖原桌面求解器不接受的90度旋转盒。
    xml = '''<mujoco><worldbody>
      <body name="cab_main"><joint name="cab_slide" type="slide" axis="1 0 0"/>
        <geom name="cab_g0" type="box" size=".01 .12 .2"
        pos="0 0 .5" quat=".70710678 0 .70710678 0"/></body>
      <body name="plate_main" pos=".4 0 .1"><freejoint/>
        <geom name="plate_g0" type="box" size=".07 .07 .01"/></body>'''
    if occupied:
        xml += '''<body name="wine_main" pos="0 0 .58"><freejoint/>
          <geom name="wine_g0" type="box" size=".04 .04 .07"/></body>'''
    return MjSim.from_xml_string(xml + '</worldbody></mujoco>')


def test_rotated_surface_and_empty_placement_preserve_world():
    sim = scene();m,d = sim.model,sim.data;sim.forward()
    before = d.qpos.copy()
    surface = horizontal_fixture_surface(m,d,'cab','cab_g0')
    assert surface['surface_center_xyz'][2] == pytest.approx(.51)
    target = fixture_surface_placement(m,d,'plate',surface,['cab','plate'])
    assert target['body_target_xyz'][2] == pytest.approx(.522)
    np.testing.assert_array_equal(d.qpos,before)


def test_occupied_surface_returns_a_different_free_point_not_other_goal():
    sim = scene(True);m,d = sim.model,sim.data;sim.forward()
    surface = horizontal_fixture_surface(m,d,'cab','cab_g0')
    target = fixture_surface_placement(m,d,'plate',surface,['cab','plate','wine'])
    assert target['fixture_id'] == 'cab'
    assert abs(target['body_target_xyz'][0]) >= .115-1e-6
    with pytest.raises(PlacementAreaFull):
        fixture_surface_placement(m,d,'plate',surface,['cab','plate','wine'],fixed_xy=[0,0])


def test_support_too_small_refuses_instead_of_forcing_contact():
    sim = scene(True);m,d = sim.model,sim.data
    gid=m.geom_name2id('cab_g0');m.geom_size[gid,2]=.11;sim.forward()
    surface=horizontal_fixture_surface(m,d,'cab','cab_g0')
    with pytest.raises(PlacementAreaFull):
        fixture_surface_placement(m,d,'plate',surface,['cab','plate','wine'])


def test_stale_surface_cannot_be_used_after_fixture_moved():
    sim=scene();m,d=sim.model,sim.data;sim.forward()
    surface=horizontal_fixture_surface(m,d,'cab','cab_g0')
    d.set_joint_qpos('cab_slide',.1);sim.forward()
    with pytest.raises(ValueError,match='重新观察'):
        fixture_surface_placement(m,d,'plate',surface,['cab','plate'])
