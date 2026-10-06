#!/usr/bin/env python3
"""核查真实LIBERO模型输入、末端变换、实际关节请求与视频。"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation

from hrc_pilot.robot_control import hand_rotation
from hrc_pilot.video_verification import finalize_video_verification


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args()
    episodes=[]
    for path in args.input_dir.rglob('metrics.json'):
        directory=path.parent
        rows=[json.loads(line) for line in (directory/'policy_io.jsonl').read_text().splitlines()]
        calls=set()
        for row in rows:
            audit=row['adapter'];obs=row['observation']
            assert audit['model_input_keys']==['observation/image','observation/wrist_image','observation/state','prompt']
            raw=np.asarray(audit['raw_action_chunk'][audit['executed_chunk_index']])
            assert raw.shape==(7,) and np.isfinite(raw).all()
            rotation=hand_rotation(audit['current_quaternion_wxyz'])
            flange=np.asarray(audit['current_flange']);offset=np.asarray(audit['tcp_offset'])
            np.testing.assert_allclose(flange,obs['robot_ee'])
            expected_rotation=Rotation.from_rotvec(np.clip(raw[3:6],-1,1)*0.5).as_matrix()@rotation
            expected_flange=flange+rotation@offset+np.clip(raw[:3],-1,1)*0.05-expected_rotation@offset
            np.testing.assert_allclose(expected_flange,audit['target_flange'])
            np.testing.assert_allclose(expected_rotation,hand_rotation(audit['target_quaternion_wxyz']),atol=1e-7)
            np.testing.assert_allclose(row['action']['joints'],audit['solved_joint_target'])
            assert row['action']['control_mode']=='libero_osc_delta_to_ik'
            if audit['model_call'] not in calls:
                assert audit['executed_chunk_index']==0
                for field,key in [('rgb_artifact','exterior_rgb_sha256'),('wrist_rgb_artifact','wrist_rgb_sha256')]:
                    pixels=np.asarray(Image.open(directory/obs[field]).convert('RGB'))
                    assert sha256(pixels.tobytes()).hexdigest()==audit[key]
                calls.add(audit['model_call'])
        controls=[json.loads(line) for line in (directory/'robot_control.jsonl').read_text().splitlines()]
        cursor=0
        for control in controls:
            while cursor+1<len(rows) and rows[cursor+1]['step']<=control['time_s']+1e-8:cursor+=1
            np.testing.assert_allclose(control['requested_target'],rows[cursor]['action']['joints'])
        assert rows and controls
        episodes.append({'episode':directory.relative_to(args.input_dir).as_posix(),'model_calls':len(calls),
                         'joint_actions':len(rows),'pixels_and_pose_transforms_verified':True,
                         'requested_joints_match_model_ik':True})
    assert episodes
    finalize_video_verification(args.input_dir,required=True)
    (args.input_dir/'model_execution_verification.json').write_text(json.dumps({'status':'verified','episodes':episodes,
        'interpretation':'核查模型和执行链路；坐标/相机域匹配、IK可达性和HRC效度仍需独立验证。'},ensure_ascii=False,indent=2))
    print('核查通过',episodes)


if __name__=='__main__':main()
