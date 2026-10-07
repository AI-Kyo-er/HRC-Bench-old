import json
from pathlib import Path
from dataclasses import replace

from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
from hrc_pilot.native_grounded_human import GroundedReflectiveHuman
from hrc_pilot.protocol import Observation,Message
from hrc_pilot.reflective_human_verification import verify_reflective_records


def observation():
    return Observation(objects={'plate':(0.,0.,.9),'bowl':(.1,0.,.9)},regions={'personal':(0.,.3,.9)},
        messages=(Message('environment','assignment','Robot handles bowl',None,'robot'),),
        robot_ee=(0.,0.,1.),human_position=(0.,.6,0.),held_by_human=(),completed_skills=(),
        human_execution={'manipulable_object_ids':['plate','bowl'],'object_measured_in_hand':None})


def test_grounded_state_does_not_promote_old_generated_claims_to_evidence():
    outputs=iter(['I should consider the measured plate, not assume a grasp. </think>'+json.dumps({
        'decision_kind':'continue','long_term_intention':'整理餐盘','personal_targets':[['plate','personal']],
        'plan':['grasp plate','place plate personal']}),json.dumps({'intent':'grasp','object_id':'plate'})])
    p=GroundedReflectiveHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),model_path=Path('/unused'),
        autonomous_context='pantry_work',generator=lambda _:next(outputs))
    p.reset(0);p.experience_memory=[{'memory_id':'old','text':'I already placed everything.'}]
    output=p.step(observation());public=json.loads(p.policy_io[0]['public_input'].split('\n',1)[1])
    assert output.command.intent=='grasp' and output.command.object_id=='plate'
    assert 'your_personal_experience_memory' not in public and 'your_recent_public_decisions' not in public
    assert public['robot_current_assignments'][0]['assigned_role']=='robot'
    assert p.planning_io[0]['raw_model_output'].startswith('I should consider')
    assert p.planning_io[0]['thinking_enabled'] and not p.policy_io[0]['thinking_enabled']
    assert verify_reflective_records(p.planning_io,p.policy_io)['status']=='verified'


def test_truncated_thinking_retains_intention_and_is_not_parsed_as_final_decision():
    outputs=iter(['I am still reasoning and might consider {"personal_targets":[]} ',json.dumps({'intent':'observe'})])
    p=GroundedReflectiveHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),model_path=Path('/unused'),
        autonomous_context='pantry_work',generator=lambda _:next(outputs))
    p.reset(0);p.step(observation())
    assert p.planning_io[0]['validation_error'] and p.planning_io[0]['raw_output']==''
    assert p.personal_targets==[] and verify_reflective_records(p.planning_io,p.policy_io)['status']=='verified'
