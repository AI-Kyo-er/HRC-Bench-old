import numpy as np

from hrc_pilot.robot_coordination import decode_image,hold_actions,image_payload,validate_decision


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
