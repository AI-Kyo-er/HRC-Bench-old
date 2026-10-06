#!/usr/bin/env python3
"""独立重建放置接触与释放；旧记录明确区分原生几何判定与物理完成。"""
import argparse
import json
from pathlib import Path

import numpy as np

from hrc_pilot.native_placement import NativePlacementEvidence


def rows(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def verify_episode(directory):
    trace=rows(directory/'trace.jsonl');metrics=json.loads((directory/'metrics.json').read_text())
    recorded_path=directory/'placement_evidence.jsonl'
    score=NativePlacementEvidence('akita_black_bowl_1','plate_1')
    if recorded_path.exists():
        recorded=rows(recorded_path);assert len(recorded)==len(trace)-1
        for index,observed in enumerate(recorded):
            score.update(trace[index],trace[index+1],observed['native_geometry_satisfied'])
            actual=score.records[-1]
            for key in ['gripper_aperture_m','object_speed_m_s','receiver_speed_m_s','stable_duration_s']:
                np.testing.assert_allclose(actual[key],observed[key],atol=1e-8)
            for key in ['receiver_contact','gripper_contact','released','released_stable_placement']:
                assert actual[key]==observed[key]
        verified=score.records[-1]['released_stable_placement']
        status='reconstructed_physical_criterion'
    else:
        score.update(trace[-2],trace[-1],bool(metrics.get('native_geometry_success',metrics.get('robot_goal_success',False))))
        verified=False
        status='legacy_terminal_contact_diagnostic_only'
    return {'episode':str(directory),'status':status,'raw_task_success':metrics['task_success'],
            'physical_placement_completion_verified':verified,'terminal_contact_measurement':score.records[-1],
            'interpretation':'旧记录没有连续几何判定，不能事后证明完成；末帧仍夹持可直接排除释放。新记录重建持续稳定的物理判据，不代替真人效度。'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args()
    episodes=[verify_episode(path.parent) for path in sorted(args.input_dir.rglob('metrics.json'))]
    assert episodes
    output={'status':'audited','episodes':episodes,'physical_completion_verified_count':sum(e['physical_placement_completion_verified'] for e in episodes)}
    (args.input_dir/'placement_verification.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
    print(f'{len(episodes)}条接触释放审计，{output["physical_completion_verified_count"]}条物理完成已验证')


if __name__=='__main__':main()
