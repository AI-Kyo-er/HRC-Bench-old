import json
from dataclasses import replace
from pathlib import Path

from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
from hrc_pilot.native_autonomous_human import AutonomousNativeHuman
from hrc_pilot.protocol import Observation,Message


def observation(time=0,messages=()):
    return Observation(objects={'plate_1':(0,0,.9),'cookies_1':(.1,0,.9)},regions={'plate_ready':(0,.12,.9),'cookies_ready':(.1,.12,.9)},
                       messages=messages,robot_ee=(0,0,1.),human_position=(0,.6,0),held_by_human=(),completed_skills=(),time_s=time)


def policy(outputs):
    queue=iter(outputs)
    return AutonomousNativeHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),autonomous_context='snack_host',
        model_path=Path('/unused/generator'),generator=lambda _:json.dumps(next(queue)),decision_interval_steps=40)


def test_generated_goals_never_route_actions_and_proposals_do_not_become_assignments():
    p=policy([{'intent':'observe','personal_targets':[{'object_id':'cookies_1','destination':'cookies_ready'}],
               'plan':['push cookies_1'],'negotiation_proposal':{'kind':'request_help','text':'Please help me.'}}]);p.reset(0)
    o=observation();r=p.step(o)
    assert r.command.intent=='observe' and p.personal_targets[0]['object_id']=='cookies_1'
    assert len(r.messages)==1 and r.messages[0].kind=='negotiation_proposal'
    p.step(replace(o,time_s=.05,messages=r.messages))
    assert len(p.policy_io)==1 and not p.public_task_memory


def test_invalid_target_does_not_overwrite_goal_or_cancel_valid_model_action():
    p=policy([{'intent':'observe','personal_targets':[{'object_id':'cookies_1','destination':'cookies_ready'}]},
              {'intent':'push','object_id':'plate_1','destination':'plate_ready','personal_targets':[{'object_id':'invisible','destination':'cookies_ready'}]}]);p.reset(0)
    p.step(observation());r=p.step(observation(2))
    assert p.personal_targets[0]['object_id']=='cookies_1'
    assert r.command.intent=='push' and r.command.object_id=='plate_1'
    assert p.policy_io[-1]['personal_goal_state']['target_validation_error']


def test_private_profile_and_targets_are_own_memory_not_public_task_assignments():
    p=policy([{'intent':'observe','personal_targets':[]}]);p.reset(0)
    o=observation(messages=(Message('environment','assignment','Place bowl',None,'robot'),));p.step(o)
    public=json.loads(p.policy_io[0]['public_input'].split('\n',1)[1])
    assert public['your_current_assignments']==[] and public['personal_context']
    assert not {'task_success','personal_evidence','human_goal_success'}.intersection(public)
