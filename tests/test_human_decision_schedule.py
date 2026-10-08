from copy import deepcopy

import pytest

from hrc_pilot.human_decision_schedule import HumanDecisionSchedule


def state(time,moving=False,held=None,completed=(),effect=None):
    return {'time_s':time,'human_body_xy':[.25,.6],
        'human_execution':{'held_object':held,'carried_objects':[], 'phase':'transfer_translate' if moving else 'idle',
            'motion_in_progress':moving,'completed_requests':list(completed),
            'last_receipt':{'accepted':True,'effect':effect}},
        'observable_world':{'object_contacts':{}}}


def test_macro_runs_without_repeated_decisions_and_completion_or_new_context_reopens_neural_choice():
    policy=HumanDecisionSchedule()
    assert policy.check(state(0),[],[])['call_neural_policy']
    assert not policy.check(state(4,True),[],[])['call_neural_policy']
    assert not policy.check(state(8,True),[],[])['call_neural_policy']
    result=policy.check(state(12,False,completed=[0]),[],[])
    assert result['call_neural_policy'] and 'own_execution_update' in result['observed_reasons']
    assert not {'next_action','intention','participation','task_success'}.intersection(result)
    cue={'time_s':13.,'text':'Visitor needs the snack to take away.'}
    assert not policy.check(state(13),[],[cue])['call_neural_policy']
    # 过早出现的新信息会保留到下一可调用时刻，不丢掉或自动执行正确策略。
    result=policy.check(state(16),[],[cue])
    assert result['call_neural_policy'] and 'new_private_context' in result['observed_reasons']


def test_repeated_robot_statement_and_noop_completion_do_not_create_replanning_loop_but_periodic_choice_remains():
    policy=HumanDecisionSchedule();messages=[{'time_s':0.,'speaker':'robot','kind':'response','text':'Waiting for confirmation.'}]
    assert policy.check(state(0),messages,[])['call_neural_policy']
    messages.append({**messages[0],'time_s':4.})
    assert not policy.check(state(4,completed=[1],effect='already_at_requested_supported_position'),messages,[])['call_neural_policy']
    assert not policy.check(state(8,completed=[1]),messages,[])['call_neural_policy']
    assert policy.check(state(20,completed=[1]),messages,[])['observed_reasons']==['periodic_reconsideration']
    messages.append({**messages[0],'time_s':24.,'text':'Can you make the bowl available?'} )
    assert policy.check(state(24,completed=[1]),messages,[])['call_neural_policy']


def test_future_information_is_rejected_and_robot_contact_is_observed_without_task_score():
    policy=HumanDecisionSchedule();r=state(0);r.update(task_success=True,private_intention='serve')
    before=deepcopy(r);policy.check(r,[],[])
    assert r==before
    with pytest.raises(ValueError,match='未来'):policy.check(state(4),[{'time_s':5.,'speaker':'robot'}],[])
    with pytest.raises(ValueError,match='尚未送达'):policy.check(state(4),[],[{'time_s':6.,'text':'Call'}])
    r=state(4,True);r['observable_world']['object_contacts']={'bowl':{'robot_hand_contact':True}}
    result=policy.check(r,[],[])
    assert result['call_neural_policy'] and 'robot_contact_change' in result['observed_reasons']
