import json
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from hrc_pilot.interactive_human import InteractiveArticulatedHuman,hand_target
from hrc_pilot.continuous import CONTINUOUS_SCENARIOS,HumanCommand
from hrc_pilot.native_articulated_hand import NativeArticulatedHuman
from test_native_grounded_human import observation


def test_contact_summary_and_prior_measurements_are_actual_observations():
    p=InteractiveArticulatedHuman(CONTINUOUS_SCENARIOS['relay'],model_path=Path('/unused'),autonomous_context='shared_meal')
    p.reset(0);o=observation()
    o=replace(o,human_execution={**o.human_execution,'hand_contact_report':{'contact_with_other_agent':True},
        'hand_contact_geoms':['robot0_link5_collision'],'fingertip_remaining_distance_m':.12})
    a=json.loads(p._prompt(o).split('\n',1)[1]);b=json.loads(p._prompt(replace(o,time_s=2)).split('\n',1)[1])
    assert a['hand_contact_summary']['contact_with_other_agent']
    assert b['recent_measured_world_history'][0]['fingertip_remaining_distance_m']==.12
    assert a['observation_projection']=='compact_contact_history_v2'
    assert not {'task_success','human_goal_success'}.intersection(a)


def test_move_hand_preserves_pressure_and_uses_physical_target():
    actor=object.__new__(NativeArticulatedHuman);actor.signature=None;actor.phase='holding'
    actor.env=SimpleNamespace(sim=SimpleNamespace(data=SimpleNamespace(time=4.)))
    actor.finger_target=.021;actor.carry_object='bowl'
    actor.accept(HumanCommand('move_hand',target=(.25,.6,1.3)))
    assert actor.finger_target==.021 and actor.carry_object=='bowl'
    assert actor.phase=='hand_waypoint';np.testing.assert_allclose(actor.target,[.25,.6,1.3])
    with pytest.raises(ValueError):hand_target({'hand_target_xyz':[.25,.6,2.]})
