#!/usr/bin/env python3
"""独立核对人策略资格检查中的泊车、静止控制、真实时钟与原始推理。"""
import argparse
import json
from pathlib import Path

import numpy as np


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def verify(root):
    ep=root/'human_activity'
    provenance=json.loads((root/'provenance.json').read_text())
    assert not provenance['source_files_changed_during_run']
    assert not rows(ep/'model_calls.jsonl')
    controls=rows(ep/'stationary_robot_control.jsonl');trace=rows(ep/'trace.jsonl')
    parking=json.loads((ep/'parking_control.json').read_text())
    assert len(parking)==80 and len(trace)==len(controls)+1 and controls
    np.testing.assert_allclose([r['physics_time_s'] for r in parking],
        parking[0]['physics_time_s']+np.arange(80)/20,atol=1e-7)
    for c,first,second in zip(controls,trace,trace[1:]):
        assert c['source']=='calibrated_stationary_robot_no_model'
        assert c['action']==[0.]*6+[-1.]
        assert c['step']==first['step']
        np.testing.assert_allclose([c['pre_physics_time_s'],c['post_physics_time_s']],
            [first['physics_time_s'],second['physics_time_s']],atol=1e-7)
        np.testing.assert_allclose(second['physics_time_s']-first['physics_time_s'],.05,atol=1e-7)
    assert all(c['human_object_pose_writes']==0 for c in rows(ep/'human_control.jsonl'))
    human=rows(ep/'human_policy_io.jsonl');plans=rows(ep/'human_planner_io.jsonl')
    assert human and plans and all('raw_model_output' in p for p in plans)
    speed=max(np.linalg.norm(np.asarray(b['robot_ee'])-a['robot_ee'])*20 for a,b in zip(trace,trace[1:]))
    result={'status':'verified','human_action_calls':len(human),'human_planner_calls':len(plans),
        'robot_neural_calls':0,'parking_real_control_steps':80,'human_activity_steps':len(controls),
        'human_activity_duration_s':len(controls)/20,'robot_peak_measured_eef_speed_m_s':float(speed),
        'robot_eef_displacement_from_park_m':float(np.linalg.norm(np.asarray(trace[-1]['robot_ee'])-trace[0]['robot_ee'])),
        'interpretation':'验证零机器人模型调用、实际泊车和静止控制指令；静止指令不保证接触下身体绝对静止，也不构成HRC成绩。'}
    (root/'qualification_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True)
    print(json.dumps(verify(parser.parse_args().input_dir),ensure_ascii=False))
