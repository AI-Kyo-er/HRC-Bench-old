import numpy as np

from hrc_pilot.robot_coordination import decode_image,hold_actions,image_payload,validate_decision,execution_feedback


def test_visual_frames_roundtrip_without_label_or_score_injection():
    image=np.random.default_rng(0).integers(0,256,(32,32,3),dtype=np.uint8)
    np.testing.assert_array_equal(np.asarray(decode_image(image_payload(image))),image)


def test_model_plan_does_not_route_to_execute_when_current_decision_is_hold():
    decision,error=validate_decision('{"mode":"hold","plan":["execute next"],"reason":"等待对方"}')
    assert error is None and decision['mode']=='hold'


def test_invalid_execute_has_explicit_error_and_safe_hold_not_teacher_repair():
    decision,error=validate_decision('{"mode":"execute","instruction":""}')
    assert error and decision['mode']=='hold' and not decision['instruction']


def test_hold_primitive_preserves_gripper_and_never_moves_ee():
    for fingers,expected in [([.04,-.04],-1),([.006,-.006],1)]:
        actions=hold_actions([0]*6+fingers,10)
        np.testing.assert_array_equal(actions[:,:6],np.zeros((10,6)))
        assert np.all(actions[:,-1]==expected)


def test_wide_object_grasp_keeps_previous_close_command_when_holding():
    actions=hold_actions([0]*6+[.03,-.03],10,last_gripper_action=.8)
    assert np.all(actions[:,-1]==.8)


def test_factual_execution_is_distinct_from_generated_plan_and_has_no_goal_label():
    record={'robot_ee':[0,0,1.],'robot_qpos':[0]*7+[.04,-.04],'contacts':[]}
    feedback=execution_feedback(record,[0,0,1.,0,0,0,.04,-.04],[],[])
    assert feedback['completed_native_control_steps']==0
    assert feedback['issued_learned_vla_blocks']==0
    assert feedback['measured_gripper_aperture_m']==.08
    assert feedback['finger_contact_sample_counts']=={'finger_1':0,'finger_2':0}
    assert 'task_success' not in feedback and 'grasped' not in feedback
