import numpy as np
import pytest

from hrc_pilot.human_support_targets import cabinet_placement_targets


def test_support_height_comes_from_collision_geometry_and_actual_object_orientation():
    pytest.importorskip('robosuite')
    from robosuite.utils.binding_utils import MjSim
    sim=MjSim.from_xml_string('''<mujoco><worldbody>
    <geom name="wooden_cabinet_1_g9" type="box" pos=".1 -.2 1" size=".2 .2 .002"/>
    <body name="wine_main" pos="0 0 .5"><freejoint/>
    <geom name="wine_g1" type="box" size=".02 .05 .1" group="0"/></body>
    </worldbody></mujoco>''')
    sim.forward()
    point=cabinet_placement_targets(sim.model,sim.data,['wine'])['wine_on_cabinet']
    np.testing.assert_allclose(point,[.1,-.2,1.104])
    sim.data.qpos[3:7]=[np.sqrt(.5),np.sqrt(.5),0,0];sim.forward()
    point=cabinet_placement_targets(sim.model,sim.data,['wine'])['wine_on_cabinet']
    np.testing.assert_allclose(point,[.1,-.2,1.054])
