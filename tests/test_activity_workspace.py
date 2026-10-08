import numpy as np
import pytest

from hrc_pilot.activity_workspace import make_table_workspace


def scene():
    pytest.importorskip('robosuite')
    from robosuite.utils.binding_utils import MjSim
    sim=MjSim.from_xml_string('''<mujoco><worldbody>
        <geom name="table_collision" type="box" pos="0 0 .875" size=".5 .6 .025"/>
        <body name="bowl_main" pos="0 0 .91"><freejoint/>
          <geom name="bowl_bottom" type="box" size=".05 .05 .01"/></body>
        <body name="packet_main" pos=".1 .1 .925"><freejoint/>
          <geom name="packet_box" type="box" size=".02 .025 .025"/></body>
        <body name="fixture_main" pos="-.3 -.25 1"><geom name="fixture_box" type="box" size=".08 .08 .1"/></body>
        </worldbody></mujoco>''');sim.forward();return sim


def test_separated_zones_use_current_collision_bottom_and_preserve_world_state():
    sim=scene();before=sim.data.qpos.copy()
    layout=make_table_workspace(sim.model,sim.data,['bowl','packet'],['fixture'])
    np.testing.assert_array_equal(sim.data.qpos,before)
    serving=layout['object_specific_body_targets']['serving_ready']
    np.testing.assert_allclose(serving['bowl'],[.16,.04,.912])
    np.testing.assert_allclose(serving['packet'],[.16,.04,.927])
    assert np.linalg.norm(np.asarray(layout['zone_surface_positions']['snack_delivery'])[:2]-
                          layout['zone_surface_positions']['akita_black_bowl_1_personal'][:2])>.2
    assert not {'task_success','next_action','accepted_arrangement'}.intersection(layout)


@pytest.mark.parametrize('zones,message',[
    ({'edge':(.49,.0)},'桌边'),
    ({'fixture':(-.3,-.25)},'固定物件'),
    ({'prepare':(.1,.2),'serve':(.1,.2)},'重叠'),
])
def test_invalid_layout_is_rejected_instead_of_silently_choosing_another_destination(zones,message):
    sim=scene()
    with pytest.raises(ValueError,match=message):make_table_workspace(sim.model,sim.data,['bowl','packet'],['fixture'],zones=zones)


def test_current_object_orientation_changes_placement_height_without_changing_functional_zone():
    sim=scene();before=make_table_workspace(sim.model,sim.data,['bowl','packet'])
    sim.data.qpos[10:14]=[np.sqrt(.5),0,np.sqrt(.5),0];sim.forward()
    after=make_table_workspace(sim.model,sim.data,['bowl','packet'])
    assert after['zone_surface_positions']==before['zone_surface_positions']
    np.testing.assert_allclose(after['object_specific_body_targets']['serving_ready']['packet'],[.16,.04,.922])
    assert after['object_specific_body_targets']['serving_ready']['bowl']==before['object_specific_body_targets']['serving_ready']['bowl']
