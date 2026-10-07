import mujoco
import numpy as np
import pytest

from hrc_pilot.geometry_frame_replay import replay_recorded_geometry


def state(forward=False):
    model=mujoco.MjModel.from_xml_string('''<mujoco><option timestep="0.01" gravity="0 0 0" integrator="Euler"/>
    <worldbody><body name="cube_main" pos="0 0 1"><freejoint/><geom type="box" size="0.1 0.2 0.3" mass="1"/></body></worldbody></mujoco>''')
    data=mujoco.MjData(model);data.qvel[:]=[1.,.2,.3,.4,.5,.6]
    mujoco.mj_forward(model,data);mujoco.mj_step(model,data)
    if forward:mujoco.mj_forward(model,data)
    record={'qpos':data.qpos.tolist(),'qvel':data.qvel.tolist(),'objects':{'cube':data.xpos[1].tolist()}}
    matrix=data.geom_xmat.copy()
    return model,data,record,matrix


def test_cached_euler_geometry_is_reconstructed_without_fitting_target():
    model,data,record,matrix=state()
    value=replay_recorded_geometry(model,data,record)
    assert value['frame']=='cached_before_euler_position_integration'
    assert value['physics_offset_s']==-.01
    np.testing.assert_allclose(data.geom_xmat,matrix,atol=1e-12)


def test_forwarded_snapshot_uses_recorded_positions_and_rejects_inconsistent_record():
    model,data,record,matrix=state(forward=True)
    value=replay_recorded_geometry(model,data,record)
    assert value['frame']=='forwarded_recorded_qpos'
    np.testing.assert_allclose(data.geom_xmat,matrix,atol=1e-12)
    record['objects']['cube'][0]+=1.
    with pytest.raises(ValueError,match='不能.*独立对齐'):
        replay_recorded_geometry(model,data,record)
