import json
from pathlib import Path
from dataclasses import replace

from hrc_pilot.native_activity import WorkUpdate,evaluate_activity,activity_plan
from hrc_pilot.native_contact_human import NativeQwenHuman
from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
from hrc_pilot.protocol import Observation


def trace(times,position=(0,0,.9),body_y=.6,hand_y=.6):
    return [{'time_s':t,'physics_time_s':t,'objects':{'plate_1':list(position)},
             'human_position':[0,body_y,0],'human_hand_position':[0,hand_y,1.], 'contacts':[]} for t in times]


def test_future_contact_cannot_credit_a_terminated_goal():
    plan=[WorkUpdate(0,'old','old','plate_1','home'),WorkUpdate(.25,'new','new','plate_1','other')]
    t=trace([i*.05 for i in range(11)])
    controls=[{'physics_time_s':.3,'contact_geoms':['plate_1_geom'] }]
    s=evaluate_activity(plan,{'home':(0,0,.9),'other':(.3,0,.9)},t,controls,[],[])['stages']
    assert not s[0]['physical_completion_observed']


def test_selecting_new_action_is_not_physical_completion():
    p=[WorkUpdate(0,'new','new','plate_1','other')]
    d=[{'time_s':.05,'parsed_decision':{'intent':'push','object_id':'plate_1','destination':'other'}}]
    result=evaluate_activity(p,{'other':(.3,0,.9)},trace([i*.05 for i in range(11)]),[],d,[])
    assert result['stages'][0]['first_matching_action_latency_s']==.05
    assert not result['human_final_goal_success']


def test_return_cannot_be_completed_without_actual_clearance():
    p=[WorkUpdate(0,'away','away',requirement='clearance'),WorkUpdate(.25,'back','back',requirement='return')]
    result=evaluate_activity(p,{},trace([i*.05 for i in range(11)]),[],[],[])
    assert not result['stages'][1]['physical_completion_observed']


def test_activity_update_replaces_board_but_preserves_model_owned_goal_and_experience():
    observed=[]
    def generate(prompt):
        observed.append(json.loads(prompt.split('\n',1)[1]))
        return json.dumps({'intent':'observe','current_goal':'模型自主保留的目标','memory_note':'记得刚才在观察'})
    policy=NativeQwenHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),model_path=Path('/unused/local-generator'),generator=generate,decision_interval_steps=40)
    policy.reset(0);plan=activity_plan('receiver_changes')
    base=Observation(objects={'plate_1':(0,0,.9)},regions={'plate_ready':(0,.12,.9),'plate_home':(0,0,.9)},
                     messages=tuple(plan[0].messages('robot bowl task')),robot_ee=(0,0,1.),human_position=(0,.6,0),
                     held_by_human=(),completed_skills=(),time_s=0)
    policy.step(base)
    policy.step(replace(base,time_s=15,messages=base.messages+tuple(plan[1].messages('robot bowl task'))))
    assert observed[-1]['your_current_assignments'][0]['destination']=='plate_home'
    assert observed[-1]['your_current_generated_goal']=='模型自主保留的目标'
    assert observed[-1]['generated_goal_predates_current_activity']
    assert len(policy.policy_io)==2 and len(policy.experience_memory)==2
