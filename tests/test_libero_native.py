import numpy as np

from hrc_pilot.libero_native import native_policy_input, input_audit
from hrc_pilot.native_contact_human import NativeQwenHuman
from hrc_pilot.continuous import CONTINUOUS_SCENARIOS, ContinuousWorld


def test_native_input_preserves_quaternion_branch_signed_fingers_and_camera_convention():
    pixels = np.arange(18, dtype=np.uint8).reshape(2, 3, 3)
    obs = {'robot0_eef_pos': [0.1, 0.2, 1.1], 'robot0_eef_quat': [1., 0, 0, 0],
           'robot0_gripper_qpos': [.04, -.04], 'agentview_image': pixels,
           'robot0_eye_in_hand_image': pixels + 10, 'private_task_labels': ['secret']}
    request = native_policy_input(obs, 'Pick up the bowl.')
    assert set(request) == {'observation/image', 'observation/wrist_image', 'observation/state', 'prompt'}
    np.testing.assert_allclose(request['observation/state'], [.1, .2, 1.1, np.pi, 0, 0, .04, -.04])
    np.testing.assert_array_equal(request['observation/image'], pixels[::-1, ::-1])
    audit = input_audit(request)
    assert audit['exterior_rgb_sha256'] != audit['wrist_rgb_sha256']
    assert 'secret' not in str(audit)


def test_native_human_push_is_model_generated_and_unsupported_grasps_are_rejected():
    scene=CONTINUOUS_SCENARIOS['relay']
    world=ContinuousWorld(scene)
    policy=NativeQwenHuman(scene,model_path='/tmp/unused',generator=lambda _:
        '{"intent":"push","object_id":"red","destination":"tray_red","current_goal":"推动当前公开目标"}')
    output=policy.step(world.observe())
    assert output.command.intent=='push'
    assert output.command.object_id=='red'
    assert policy.current_goal=='推动当前公开目标'
    assert policy._validated_command({'intent':'carry','object_id':'red','destination':'tray_red'},world.observe()).intent=='observe'
