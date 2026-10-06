#!/usr/bin/env python3
"""检查原生完整人物的接触点对齐、身体位移与骨骼显示连续性。"""
import argparse
import json
from pathlib import Path

import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args();episodes=[]
    for path in sorted(args.input_dir.rglob('human_avatar.jsonl')):
        rows=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        assert rows
        alignment=max(row['alignment_error_m'] for row in rows)
        body_speed=bone_step=0.
        for first,second in zip(rows,rows[1:]):
            dt=second['physics_time_s']-first['physics_time_s'];assert dt>0
            first_body=first.get('body_position',first['bone_positions'][0])
            second_body=second.get('body_position',second['bone_positions'][0])
            body_speed=max(body_speed,float(np.linalg.norm(np.asarray(second_body[:2])-first_body[:2])/dt))
            bone_step=max(bone_step,float(np.linalg.norm(np.asarray(second['bone_positions'])-first['bone_positions'],axis=1).max()))
        episodes.append({'episode':str(path.parent),'pose_records':len(rows),'max_alignment_error_m':alignment,
                         'max_horizontal_body_speed_m_s':body_speed,'max_bone_displacement_between_pose_frames_m':bone_step,
                         'body_speed_source':'body_base' if 'body_position' in rows[0] else 'root_bone_horizontal_displacement',
                         'qualification_passed':alignment<=.025 and body_speed<=.30 and bone_step<=.08})
    assert episodes
    qualified_count=sum(r['qualification_passed'] for r in episodes)
    result={'status':'verified' if qualified_count==len(episodes) else 'failed','episodes':episodes,'qualified_count':qualified_count,
            'interpretation':'显示骨骼与接触点、身体速度及离散位移核查；不证明人体动力学、身体碰撞或真人动作效度。'}
    (args.input_dir/'avatar_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(f'人物显示核查：{result["qualified_count"]}/{len(episodes)} 合格')
    if result['status']!='verified':raise SystemExit(1)


if __name__=='__main__':main()
