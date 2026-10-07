import json
from pathlib import Path

import pytest

from scripts.audit_native_hand_robot_contacts import has_direct_contact_feedback
from scripts.verify_human_command_delivery import verify


def test_direct_contact_feedback_includes_compact_summary():
    def decision(public):
        return {'public_input': '测量\n'+json.dumps(public)}
    assert has_direct_contact_feedback(decision({'hand_contact_summary': {
        'contact_with_other_agent': False, 'contact_geoms': []}}))
    assert not has_direct_contact_feedback(decision({'your_measured_execution': {}}))


def test_receipt_waypoint_must_match_raw_neural_output(tmp_path):
    point=[.2,.6,1.3]
    command={'intent':'move_hand','object_id':None,'destination':None,'speed_mps':.2,'target':point}
    human=[{'time_s':0.,'parsed_decision':command,'hand_target_xyz':point,
            'raw_model_output':'思考</think>'+json.dumps({'hand_target_xyz':point})}]
    trace=[{'time_s':0.,'physics_time_s':4.,'human_execution':{'motor_phase':'idle'}},
           {'time_s':.05,'physics_time_s':4.05}]
    receipts=[{'command':command,'neural_decision_id':0,'physics_time_s':4.,
               'phase_before_delivery':'idle','new_request':True,'forwarded_to_primitive':True}]
    def write(name, rows):
        (tmp_path/name).write_text('\n'.join(json.dumps(r) for r in rows))
    write('human_policy_io.jsonl',human);write('trace.jsonl',trace)
    write('human_command_delivery.jsonl',receipts)
    assert verify(tmp_path)['status']=='verified'
    human[0]['raw_model_output']='</think>'+json.dumps({'hand_target_xyz':[.3,.6,1.3]})
    write('human_policy_io.jsonl',human)
    with pytest.raises(AssertionError):
        verify(tmp_path)
