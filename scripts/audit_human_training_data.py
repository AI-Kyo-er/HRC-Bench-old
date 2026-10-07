#!/usr/bin/env python3
"""独立重建数据教师的释放稳定关系、请求参数与运动，不把教师计作模型。"""
import argparse,json
from pathlib import Path
import numpy as np
from hrc_pilot.native_personal_evidence import evaluate_personal_goals


def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True);root=parser.parse_args().input_dir
    assert read(root/'video_verification.json')['status']=='verified'
    provenance=read(root/'provenance.json');assert provenance['actual_neural_calls']==0 and not provenance['source_files_changed_during_run']
    results=[]
    for p in sorted((root/'episodes').glob('*/metrics.json')):
        ep=p.parent;m=read(p);trace=rows(ep/'trace.jsonl');control=rows(ep/'human_control.jsonl');teacher=rows(ep/'teacher_io.jsonl')
        source=read(next((root/'samples'/m['split']).glob(m['episode_id']+'__step*.source.json')))
        public=json.loads(source['public_input'].split('\n',1)[1]);regions=public['regions_xyz']
        # 保存的region在提示中舍入；重新从初始库存规则恢复真实目标坐标。
        from hrc_pilot.native_scene_catalog import scene_regions
        movable=trace[0]['human_execution']['manipulable_object_ids'];regions=scene_regions(trace[0]['objects'],movable)
        fake=[{'time_s':t['time_s'],'personal_goal_state':{'personal_targets':m['targets'],'long_term_intention':t['requested']['long_term_intention'],'target_validation_error':None}} for t in teacher]
        evidence=evaluate_personal_goals(regions,trace,control,fake,[],require_table_release=True)
        stable=[g['object_id'] for g in evidence['target_intervals'] if g['terminal_relation_satisfied']]
        assert set(stable)==set(m['terminal_released_stable_targets'])
        assert all(t['command_validation']['status']=='accepted' for t in teacher)
        assert all(t['accepted']['intent']==t['requested']['intent'] for t in teacher)
        assert all(r['human_object_pose_writes']==0 for r in control)
        np.testing.assert_allclose([r['physics_time_s']-trace[0]['physics_time_s'] for r in trace],np.arange(len(trace))/20,atol=1e-7)
        hand_speed=max(float(np.linalg.norm(r['actual_velocity'])) for r in control)
        speeds=[float(np.linalg.norm(np.asarray(b['object_position'])-a['object_position'])/(b['physics_time_s']-a['physics_time_s']))
            for a,b in zip(control,control[1:]) if a['object_id']==b['object_id'] and a.get('object_position') is not None and b.get('object_position') is not None]
        object_speed=max(speeds,default=0.);qualified=len(stable)==len(m['targets']) and hand_speed<=.65 and object_speed<=1.5
        results.append({'episode_id':m['episode_id'],'released_stable_targets':stable,'source':'teacher_actual_contact_not_neural_benchmark',
            'motion_qualified':hand_speed<=.65 and object_speed<=1.5,'human_peak_speed_m_s':hand_speed,'object_peak_speed_m_s':object_speed,
            'supervision_eligible':qualified,'first_stable_relations':[{k:g[k] for k in ['object_id','first_stable_relation_s']} for g in evidence['target_intervals']]})
    result={'status':'verified','episodes':results,'qualified_episodes':sum(r['supervision_eligible'] for r in results),
        'pair_rule':'same stem .source.json / .target.json; episode stem before __step','interpretation':'真实接触教师训练范例核查，不是NN伙伴操作或HRC能力结果。'}
    (root/'training_data_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
