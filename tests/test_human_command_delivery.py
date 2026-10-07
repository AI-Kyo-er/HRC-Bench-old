from types import SimpleNamespace

import numpy as np
import pytest

from hrc_pilot.continuous import HumanCommand
from hrc_pilot.human_command_delivery import HumanCommandDelivery
from hrc_pilot.native_articulated_hand import NativeArticulatedHuman


def hand():
    actor=object.__new__(NativeArticulatedHuman)
    actor.env=SimpleNamespace(sim=SimpleNamespace(data=SimpleNamespace(time=0.),
        model=SimpleNamespace(geom_contype=np.zeros(1),geom_conaffinity=np.zeros(1))))
    actor.geom=0;actor.phase='holding';actor.signature=None
    actor.carry_object='plate';actor.surface_z=.9
    actor.regions={'personal':(0,.3,.9)}
    actor.position=lambda:np.array([0.,0.,1.1])
    return actor


def test_cached_place_after_release_does_not_create_a_false_missing_grasp_failure():
    actor=hand();delivery=HumanCommandDelivery();command=HumanCommand('place','plate','personal')
    assert delivery.submit(actor,command,0) and actor.phase=='place_transfer'
    # 原语完成真实释放和退手后的状态；没有新的NN回答。
    actor.carry_object=None;actor.phase='idle';actor.env.sim.data.time=1.
    assert not delivery.submit(actor,command,0)
    assert actor.phase=='idle' and actor.motor_failure is None
    # 一个新回答仍可明确请求相同place；未握持的真实请求正常报错。
    assert delivery.submit(actor,command,1)
    assert actor.phase=='failed' and actor.motor_failure=='requested_object_not_in_measured_hand'
    started=actor.command_started_at;actor.env.sim.data.time=1.1
    assert not delivery.submit(actor,command,1) and actor.command_started_at==started


def test_active_primitive_keeps_tracking_without_automatically_advancing_plan():
    actor=hand();delivery=HumanCommandDelivery();command=HumanCommand('place','plate','personal')
    delivery.submit(actor,command,0)
    actor.env.sim.data.time=.05
    assert delivery.submit(actor,command,0) and actor.phase=='place_transfer'
    assert actor.command_started_at==0.
    with pytest.raises(ValueError,match='请求内容'):
        delivery.submit(actor,HumanCommand('release'),0)
    with pytest.raises(ValueError,match='非负'):
        delivery.submit(actor,command,-1)
