import importlib.util
import json
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('native_feedback_verifier',Path(__file__).resolve().parents[1]/'scripts/verify_native_dynamic_feedback.py')
verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)


def episode(tmp_path, *, false_position=False, routed_intent=False):
    feedback={'body_xy':[.25,.6],'body_target_xy':[.25,.6], 'body_remaining_distance_m':0.,
              'fingertip_xyz':[.25,.6,1.1],'accepted_intent':'observe'}
    first={'time_s':0.,'step':0,'robot_ee':[0,0,1.], 'human_position':[.25,.6,0.],
           'human_hand_position':[.25,.6,1.1], 'human_execution':feedback}
    second={**first,'step':1,'time_s':.05,'human_execution':{'accepted_intent':'push' if routed_intent else 'return'}}
    public={'robot_action':'native_joint_control','your_measured_execution':feedback,
            'robot_measured_motion':{'eef_speed_m_s':0.}}
    if false_position:public['your_measured_execution']={**feedback,'body_xy':[.25,.8]}
    decision={'time_s':0.,'step':0,'parse_error':None,'parsed_decision':{'intent':'return'},
              'public_input':'公开反馈\n'+json.dumps(public)}
    (tmp_path/'trace.jsonl').write_text('\n'.join(json.dumps(row) for row in [first,second]))
    (tmp_path/'human_policy_io.jsonl').write_text(json.dumps(decision)+'\n')
    return tmp_path


def test_actual_feedback_and_model_command_chain_can_be_reconstructed(tmp_path):
    assert verifier.verify_episode(episode(tmp_path))['status']=='verified'


def test_false_body_feedback_is_rejected(tmp_path):
    with pytest.raises(AssertionError):verifier.verify_episode(episode(tmp_path,false_position=True))


def test_runtime_command_differing_from_model_is_rejected(tmp_path):
    with pytest.raises(AssertionError):verifier.verify_episode(episode(tmp_path,routed_intent=True))
