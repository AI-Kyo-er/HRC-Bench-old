import pytest
from hrc_pilot.joint_process_metrics import measured_process


def state(t,y,completed=()):
    return {'time_s':t,'human_body_xy':[.25,y],'robot_ee':[t,0,0],
            'human_execution':{'completed_requests':list(completed)}}


def test_initial_aside_is_joining_not_departure_and_actual_return_is_measured():
    trace=[state(0,.95),state(1,.6),state(2,.95),state(3,.6)]
    controls=[{'source':'actual_vla_public_dialogue'},{'source':'coordinator_selected_hold'},
              {'source':'actual_vla_coordinator_instruction'}]
    metrics=measured_process(trace,[],controls,[])
    p=metrics['actual_participation']
    assert p['initially_aside'] and p['first_workspace_entry_s']==1
    assert p['departure_return_cycles']==[{'departure_s':2,'return_s':3,'duration_s':1}]
    assert metrics['robot_selected_hold_duration_s']==1


def test_claimed_departure_and_already_satisfied_request_are_not_new_contribution():
    trace=[state(0,.6),state(1,.6,[1])]
    human=[{'decision_id':0,'time_s':0,'choice':{'action':'message','message':'I left.'}},
           {'decision_id':1,'time_s':.5,'choice':{'action':'relocate'}}]
    receipts=[{'request_id':1,'accepted':True,'effect':'already_at_requested_supported_position'}]
    result=measured_process(trace,human,[{'source':'coordinator_selected_hold'}],receipts)
    assert result['actual_participation']['departures_s']==[]
    assert result['accepted_already_satisfied_request_count']==1
    assert result['human_action_requests'][0]['completed_s']==1
    assert 'cobalance_score' not in result
    with pytest.raises(ValueError,match='时间轴'):
        measured_process([state(0,.6),state(0,.95)],[],[],[])
