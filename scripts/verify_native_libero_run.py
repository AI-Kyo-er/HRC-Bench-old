#!/usr/bin/env python3
"""独立核查原生模型像素、状态、原始动作、实际控制与视频。"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image

from hrc_pilot.libero_native import native_policy_input
from hrc_pilot.video_verification import verify_result


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def verify_episode(directory):
    trace=rows(directory/'trace.jsonl')
    actions=rows(directory/'policy_io.jsonl')
    calls=rows(directory/'model_calls.jsonl')
    assert actions and calls
    by_step={r['step']:r for r in trace}
    by_call={r['model_call']:r for r in calls}
    rotation_verified=True
    for call in calls:
        assert call['model_input_keys']==['observation/image','observation/wrist_image','observation/state','prompt']
        assert call['image_orientation']=='rotate_180_from_raw_simulator'
        for key,field in [('exterior_artifact','exterior_rgb_sha256'),('wrist_artifact','wrist_rgb_sha256')]:
            pixels=np.asarray(Image.open(directory/call[key]).convert('RGB'))
            assert pixels.shape==(256,256,3)
            assert sha256(pixels.tobytes()).hexdigest()==call[field]
        state=np.asarray(call['state'])
        public=by_step[call['step']]
        assert state.shape==(8,) and np.isfinite(state).all()
        np.testing.assert_allclose(state[:3],public['robot_ee'],atol=1e-6)
        np.testing.assert_allclose(state[-2:],public['robot_qpos'][-2:],atol=1e-6)
        if 'eef_quaternion_xyzw' in public:
            dummy=np.zeros((1,1,3),np.uint8)
            expected=native_policy_input({'robot0_eef_pos':public['robot_ee'],
                'robot0_eef_quat':public['eef_quaternion_xyzw'],'robot0_gripper_qpos':public['robot_qpos'][-2:],
                'agentview_image':dummy,'robot0_eye_in_hand_image':dummy},call['prompt'])['observation/state']
            np.testing.assert_allclose(state,expected,atol=1e-6)
        else:rotation_verified=False
    eef_peak=0.
    for row in actions:
        chunk=by_call[row['model_call']]['raw_action_chunk']
        action=np.asarray(row['action'])
        assert action.shape==(7,) and np.isfinite(action).all()
        np.testing.assert_array_equal(action,chunk[row['executed_chunk_index']])
        assert np.isclose(row['post_physics_time_s']-row['pre_physics_time_s'],.05,atol=1e-7)
        before,after=by_step[row['step']],by_step[row['step']+1]
        np.testing.assert_allclose(after['ctrl'],row['actuator_ctrl'])
        assert np.isclose(after['physics_time_s']-before['physics_time_s'],.05,atol=1e-7)
        assert np.isfinite(after['qpos']).all() and np.isfinite(after['qvel']).all()
        eef_peak=max(eef_peak,float(np.linalg.norm(np.asarray(after['robot_ee'])-before['robot_ee'])/.05))
    result={'episode':str(directory),'model_calls':len(calls),'native_actions':len(actions),
            'pixels_verified':True,'model_input_boundary_verified':True,
            'state_pose_and_signed_gripper_verified':True,'axis_angle_from_raw_quaternion_verified':rotation_verified,
            'all_native_actions_reconstructed':True,'actual_actuator_ctrl_verified':True,
            'physics_clock_verified':True,'robot_eef_peak_sampled_speed_m_s':eef_peak,
            'robot_sampled_motion_check_passed':eef_peak<=1.5}
    human_path=directory/'human_control.jsonl'
    if human_path.exists():
        human=rows(human_path)
        assert human and all(r['human_object_pose_writes']==0 for r in human)
        assert all(np.isfinite(r['actual_velocity']).all() and np.isfinite(r['motor_force_n']).all() for r in human)
        assert all(max(abs(x) for x in r['motor_force_n'])<=8+1e-6 for r in human)
        speed=max(float(np.linalg.norm(r['actual_velocity'])) for r in human)
        object_speeds=[float(np.linalg.norm(np.asarray(b['object_position'])-a['object_position'])/
                             (b['physics_time_s']-a['physics_time_s']))
                       for a,b in zip(human,human[1:]) if a['object_id']==b['object_id']
                       and a.get('object_position') is not None and b.get('object_position') is not None]
        object_peak=max(object_speeds,default=0.)
        result.update(human_control_count=len(human),human_peak_speed_m_s=speed,
                      human_object_peak_speed_m_s=object_peak,
                      human_motion_check_passed=speed<=.65 and object_peak<=1.5)
    result['motion_eligible']=result['robot_sampled_motion_check_passed'] and result.get('human_motion_check_passed',True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args()
    episodes=[verify_episode(p.parent) for p in sorted(args.input_dir.rglob('metrics.json'))]
    assert episodes
    video=verify_result(args.input_dir,require_timeline=True)
    assert video['status']=='verified'
    result={'status':'verified','episodes':episodes,'episode_count':len(episodes),
            'motion_eligible_episode_count':sum(r['motion_eligible'] for r in episodes),
            'model_calls':sum(r['model_calls'] for r in episodes),
            'native_actions':sum(r['native_actions'] for r in episodes),
            'interpretation':'独立链路、视频与采样运动核查；不验证真人效度、完整人体动力学或模型HRC泛化。原始无人体参照未保存原生四元数，只核对位置与有符号双指，轴角源转换另外由单元测试覆盖。'}
    (args.input_dir/'model_execution_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(f'{len(episodes)}条链路与视频核查通过，{result["model_calls"]}次真实推理，运动合格{result["motion_eligible_episode_count"]}/{len(episodes)}')


if __name__=='__main__':main()
