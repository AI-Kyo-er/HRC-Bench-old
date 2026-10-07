from types import SimpleNamespace

import numpy as np

from hrc_pilot.settled_placement_human import SettledPlacementHuman
from test_human_owned_buffer import make_actor


def settled_actor():
    actor,data=make_actor(True);actor.__class__=SettledPlacementHuman;actor.held=None
    actor.carried_offsets={};actor.carried_quaternions={}
    data.qpos[13:16]=np.asarray(actor.regions['drawer'])-[0,0,.018]
    data.ncon=1;data.contact=[SimpleNamespace(geom1=0,geom2=1)]
    actor.env.sim.model=SimpleNamespace(geom_id2name=lambda i:'cream_g1' if i==0 else 'table_collision')
    return actor,data


def test_settled_selected_placement_is_satisfied_without_regrasp_or_target_rewrite():
    actor,data=settled_actor();point=data.qpos[13:16].copy();target=actor.regions['drawer'];robot=data.qpos[20:].copy()
    actor.accept_choice({'action':'relocate','object_id':'cream','destination':'drawer'},2)
    assert actor.phase=='idle' and actor.completed_requests==[2] and actor.held is None
    assert actor.receipts[-1]['effect']=='already_at_requested_supported_position'
    np.testing.assert_array_equal(data.qpos[13:16],point)
    np.testing.assert_array_equal(data.qpos[20:],robot)
    assert actor.regions['drawer']==target


def test_satisfied_object_does_not_silently_satisfy_an_explicit_body_return():
    actor,data=settled_actor();actor.body_base=np.array([.25,.95]);actor.body_target=actor.body_base.copy()
    actor.accept_choice({'action':'relocate','object_id':'cream','destination':'drawer','presence_choice':'return_to_work'},3)
    assert actor.phase=='return' and actor.completed_requests==[]
    for _ in range(10000):
        actor.physics_step();data.time+=actor.dt
        if actor.phase=='idle':break
    assert actor.completed_requests==[3] and actor.body_base[1]<.61 and actor.held is None


def test_fast_or_unreachable_object_is_not_a_settled_placement():
    actor,data=settled_actor();data.qvel[13:16]=[.1,0,0]
    actor.accept_choice({'action':'relocate','object_id':'cream','destination':'drawer'},4)
    assert actor.phase=='pick_approach' and actor.completed_requests==[]
    actor,data=settled_actor();actor.env.env._hrc_region_accessibility={'drawer':False}
    actor.accept_choice({'action':'relocate','object_id':'cream','destination':'drawer'},5)
    assert actor.receipts[-1]['error']=='destination_not_physically_accessible'
