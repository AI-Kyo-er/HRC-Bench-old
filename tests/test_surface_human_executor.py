from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from hrc_pilot.surface_human_executor import SurfaceDestinations
from test_activity_workspace import scene


def actor(sim):
    return SimpleNamespace(env=SimpleNamespace(sim=sim),held='bowl',object_id='packet',
        auto_buffer=True,phase='transfer_lower',_table_input_choice=None)


def test_selected_object_geometry_is_separate_from_public_surface_and_unrelated_relation_targets():
    sim=scene();a=actor(sim);public={'serve':[.16,.04,.9],'packet__in__bowl':[.1,.2,.95]}
    before=deepcopy(public);qpos=sim.data.qpos.copy();view=SurfaceDestinations(a,public,['serve'])
    np.testing.assert_allclose(view['serve'],[.16,.04,.927])
    assert view['packet__in__bowl']==public['packet__in__bowl']
    assert public==before
    np.testing.assert_array_equal(sim.data.qpos,qpos)
    a.object_id='bowl'
    np.testing.assert_allclose(view['serve'],[.16,.04,.912])


def test_owned_object_buffer_and_new_object_have_their_own_heights_without_choosing_new_goal():
    sim=scene();a=actor(sim);public={'bowl_personal':[.35,.24,.9],'serve':[.16,.04,.9]}
    view=SurfaceDestinations(a,public,public)
    a._table_input_choice={'action':'relocate','object_id':'packet','destination':'serve'}
    np.testing.assert_allclose(view['bowl_personal'],[.35,.24,.912])
    np.testing.assert_allclose(view['serve'],[.16,.04,.927])
    a._table_input_choice=None;a.phase='buffer_owned_object'
    np.testing.assert_allclose(view['bowl_personal'],[.35,.24,.912])
    a.phase='transfer_lower';a.held='packet'
    np.testing.assert_allclose(view['serve'],[.16,.04,.927])
    assert a.object_id=='packet' and public['serve'][2]==.9


def test_unknown_surface_cannot_silently_become_a_destination():
    sim=scene()
    with pytest.raises(ValueError,match='公开表面'):SurfaceDestinations(actor(sim),{},['serve'])


def test_continuous_selected_macro_uses_per_object_height_preserves_public_coordinates_and_never_moves_robot(monkeypatch):
    from test_human_owned_buffer import make_actor
    from hrc_pilot.surface_human_executor import SurfaceHumanExecutor
    import hrc_pilot.surface_human_executor as module
    a,data=make_actor(True);a.__class__=SurfaceHumanExecutor;a.cancelled_requests=[]
    a.env.sim.model=SimpleNamespace()
    offsets={'plate':.025,'cream':.010}
    def resolve(model,state,obj,surface):return [surface[0],surface[1],surface[2]+offsets[obj]]
    monkeypatch.setattr(module,'body_target_on_surface',resolve)
    public={'plate_personal':[.2,.3,1.],'serve':[.05,-.1,1.]}
    original=deepcopy(public);robot=data.qpos[20:].copy()
    a.regions=SurfaceDestinations(a,public,public);a._table_input_choice=None
    choice={'action':'relocate','object_id':'cream','destination':'serve'}
    a.accept_choice(choice,1)
    assert a._table_input_choice is None
    assert a.receipts[-1]['table_surface_placement']['resolved_object_body_xyz']==[.05,-.1,1.01]
    for i in range(20000):
        if i==100:a.accept_choice(choice,2)
        a.physics_step();data.time+=a.dt
        if a.phase=='idle':break
    assert a.completed_requests==[1] and a.held is None
    np.testing.assert_allclose(data.qpos[6:9],[.2,.3,1.025],atol=.0041)
    np.testing.assert_allclose(data.qpos[13:16],[.05,-.1,1.01],atol=.0041)
    np.testing.assert_array_equal(data.qpos[20:],robot)
    assert public==original
    assert all(np.linalg.norm(row['hand_velocity'])<=.200001 and row['robot_pose_writes']==0 for row in a.records)
