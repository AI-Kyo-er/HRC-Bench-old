from dataclasses import replace
from pathlib import Path
import json

from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
from hrc_pilot.native_reflective_human import ReflectiveArticulatedHuman
from hrc_pilot.protocol import Observation,Message
from hrc_pilot.reflective_human_verification import verify_reflective_records


def observation(t=0,messages=()):
    return Observation(objects={'plate':(0.,0.,.9),'food':(.1,0.,.9)},regions={'personal':(.1,.3,.9),'home':(0.,0.,.9)},
        messages=messages,robot_ee=(0.,0.,1.),human_position=(0.,.6,0.),held_by_human=(),completed_skills=(),time_s=t,
        human_execution={'manipulable_object_ids':['plate','food'],'object_measured_in_hand':None})


def intention(destination='personal',kind='continue'):
    return {'decision_kind':kind,'long_term_intention':'整理自己的餐盘','personal_targets':[{'object_id':'plate','destination':destination}],
            'plan':['grasp plate','place plate '+destination],'observed_changes':'餐盘仍在桌面','assumption_corrections':'命令不等于握住',
            'negotiation_proposal':{'kind':'request_space','text':'Please leave room for my plate.'}}


def policy(values):
    queue=iter(values);calls=[]
    def generate(prompt):
        calls.append(prompt);value=next(queue)
        return value if isinstance(value,str) else json.dumps(value)
    p=ReflectiveArticulatedHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),autonomous_context='pantry_work',
        model_path=Path('/unused'),generator=generate,decision_interval_steps=40,reflection_interval_s=6)
    p.reset(0);return p,calls


def test_reflection_and_motor_are_independent_neural_calls_and_plans_never_route():
    p,calls=policy([intention(),{'intent':'observe','message':'I need room.'}, {'intent':'grasp','object_id':'plate'},
                   intention('home','revise'),{'intent':'observe','personal_targets':[{'object_id':'food','destination':'personal'}]}])
    initial=(Message('environment','assignment','Robot handles food',None,'robot'),)
    output=p.step(observation(messages=initial))
    assert output.command.intent=='observe' and p.generated_plan[0]=='grasp plate'
    assert len(calls)==2 and calls[0].startswith('阶段：意图反思') and calls[1].startswith('阶段：当前动作')
    p.step(observation(.05,initial+output.messages));assert len(calls)==2
    output=p.step(observation(2,initial+output.messages));assert output.command.intent=='grasp' and len(p.planning_io)==1
    p.step(observation(6,initial));assert len(p.planning_io)==2
    assert p.personal_targets==[{'object_id':'plate','destination':'home'}]
    assert len(p.policy_io)==3 and p.audit_state()['total_neural_inferences']==5
    assert json.loads(p.policy_io[-1]['public_input'].split('\n',1)[1])['active_intention_plan']['decision_kind']=='revise'
    assert verify_reflective_records(p.planning_io,p.policy_io)['total_neural_calls']==5


def test_invalid_reflection_retains_previous_intent_without_cancelling_valid_motor():
    p,_=policy([intention(),{'intent':'observe'},'not json',{'intent':'push','object_id':'plate','destination':'personal'}])
    p.step(observation());output=p.step(observation(6))
    assert output.command.intent=='push'
    assert p.personal_targets==[{'object_id':'plate','destination':'personal'}]
    assert p.planning_io[-1]['validation_error'] and p.policy_io[-1]['parse_error'] is None
    assert verify_reflective_records(p.planning_io,p.policy_io)['total_neural_calls']==4


def test_keep_intention_is_not_forced_to_change_at_reflection_time():
    p,_=policy([intention(),{'intent':'observe'},intention(),{'intent':'observe'}])
    p.step(observation());revision=p.target_revision;p.step(observation(6))
    assert p.target_revision==revision and len(p.planning_io)==2


def test_stage_verifier_rejects_motor_goal_tampering():
    from copy import deepcopy
    import pytest
    p,_=policy([intention(),{'intent':'observe'}]);p.step(observation())
    tampered=deepcopy(p.policy_io);tampered[0]['personal_goal_state']['personal_targets']=[]
    with pytest.raises(AssertionError):verify_reflective_records(p.planning_io,tampered)


def test_model_pair_array_encoding_keeps_same_goal_semantics_as_object_encoding():
    value=intention();value['personal_targets']=[['plate','personal']]
    p,_=policy([value,{'intent':'observe'}]);p.step(observation())
    assert p.personal_targets==[{'object_id':'plate','destination':'personal'}]
    assert p.planning_io[0]['validation_error'] is None
    assert verify_reflective_records(p.planning_io,p.policy_io)['status']=='verified'
