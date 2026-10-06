import json

from hrc_pilot.motion_continuity import verify_motion_continuity


def write_episode(directory, displacement, *, human_held=True):
    rows = [{"time_s": index / 60, "objects": {"blue": {
        "position": [index * displacement, 0, 0.82], "human_held": human_held and index == 0}}}
        for index in range(2)]
    (directory / "contacts.jsonl").write_text("\n".join(json.dumps(row) for row in rows))
    controls = [{"time_s": index / 60, "applied_target": [0.01 * index] * 7 + [0.0001 * index] * 2}
                for index in range(2)]
    (directory / "robot_control.jsonl").write_text("\n".join(json.dumps(row) for row in controls))
    (directory / "physics_contract.json").write_text(json.dumps({
        "arm_target_speed_limit_rad_s": 1.2, "finger_target_speed_limit_m_s": 0.04}))


def test_human_release_jump_is_invalid_even_when_no_longer_held(tmp_path):
    write_episode(tmp_path, 0.6)
    result = verify_motion_continuity(tmp_path)
    assert result["status"] == "failed"
    assert not result["benchmark_eligible"]
    assert result["violations"][0]["now_held"] is False


def test_continuous_motion_and_robot_target_rates_pass(tmp_path):
    write_episode(tmp_path, 0.005)
    result = verify_motion_continuity(tmp_path)
    assert result["status"] == "verified"
    assert result["benchmark_eligible"]


def test_free_rigid_body_motion_is_not_misclassified_as_human_teleport(tmp_path):
    write_episode(tmp_path, 0.6, human_held=False)
    assert verify_motion_continuity(tmp_path)["status"] == "verified"


def test_missing_contact_log_remains_unverified(tmp_path):
    result = verify_motion_continuity(tmp_path)
    assert result["status"] == "unverified"
    assert not result["benchmark_eligible"]


def test_new_velocity_controller_requires_finite_bounded_requests(tmp_path):
    write_episode(tmp_path, 0.005)
    path = tmp_path / 'physics_contract.json'
    contract = json.loads(path.read_text())
    contract.update(human_hand_controller='bounded_velocity_tracking_with_position_fingers',
                    human_linear_velocity_request_limit_m_s=.65,
                    human_yaw_velocity_request_limit_rad_s=1.)
    path.write_text(json.dumps(contract))
    result = verify_motion_continuity(tmp_path)
    assert not result['benchmark_eligible']
    controls = tmp_path / 'human_control.jsonl'
    controls.write_text(json.dumps({'time_s': 0, 'applied_velocity_target': [.3, .2, 0, .5]}))
    assert verify_motion_continuity(tmp_path)['human_velocity_requests_verified'] is True
    controls.write_text(json.dumps({'time_s': 0, 'applied_velocity_target': [1., 0, 0, .5]}))
    result = verify_motion_continuity(tmp_path)
    assert not result['benchmark_eligible']
    assert result['violations'][-1]['kind'] == 'human_control_velocity_request'
