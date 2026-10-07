import importlib.util
import json
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('spatial_audit',Path(__file__).resolve().parents[1]/'scripts/audit_neural_spatial_motion.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


def fixture(ep,target=.1):
    def write(name,value):
        (ep/name).write_text(''.join(json.dumps(r)+'\n' for r in value))
    write('robot_planner_io.jsonl',[{'step':0,'decision_id':1,'raw_output':'{"mode":"move_ee","delta_xyz_m":[0.1,0,0]}',
        'parse_error':None,'decision':{'mode':'move_ee','reason':'请求空间','message':'Moving away'},
        'public_input':{'state':[0]*8},'cartesian_target_xyz_m':[target,0,0]},
        {'step':2,'decision_id':2,'decision':{'mode':'hold'}}])
    write('trace.jsonl',[{'step':i,'time_s':i*.05,'robot_ee':[i*.001,0,0],
        'contacts':[{'geom1':'human_palm_contact','geom2':'robot0_link7_collision','distance_m':0}] if i==1 else []} for i in range(3)])
    write('model_calls.jsonl',[{'planner_decision_id':1,'action_source':'vlm_selected_cartesian_primitive'}])
    write('human_policy_io.jsonl',[{'time_s':0,'negotiation_proposal_messages':[{'text':'request_space: Please make room'}]}])


def test_describes_actual_partial_motion_without_declaring_cooperation_success(tmp_path):
    fixture(tmp_path);result=audit.audit(tmp_path);event=result['events'][0]
    assert event['actual_eef_displacement_m']==.002 and event['requested_displacement_m']==.1
    assert event['remaining_target_distance_m']==.098
    assert event['human_robot_contact_time_during_move_s']==.05
    assert 'task_success' not in result and 'joint_success' not in result


def test_rejects_target_that_does_not_come_from_original_neural_choice(tmp_path):
    fixture(tmp_path,target=-.1)
    with pytest.raises(AssertionError):audit.audit(tmp_path)
