#!/usr/bin/env python3
"""独立核对公开动态任务、模型实际收到的分工、完整物理时钟和分阶段结果。"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from hrc_pilot.native_activity import activity_plan,evaluate_activity


def read(path):return json.loads(path.read_text())
def rows(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def verify_episode(directory):
    spec=read(directory/'activity_plan.json');events=read(directory/'activity_events.json')
    plan=activity_plan(spec['profile']);assert spec['updates']==[asdict(w) for w in plan]
    trace=rows(directory/'trace.jsonl');controls=rows(directory/'human_control.jsonl')
    decisions=rows(directory/'human_policy_io.jsonl');calls=rows(directory/'model_calls.jsonl')
    placement=rows(directory/'placement_evidence.jsonl')
    assert len(events)==len(plan)
    for w,event in zip(plan,events):
        assert event=={'step':round(w.time_s*20),**asdict(w)}
    assert len(trace)==len(rows(directory/'policy_io.jsonl'))+1
    np.testing.assert_allclose([r['time_s'] for r in trace],np.arange(len(trace))/20,atol=1e-9)
    np.testing.assert_allclose([r['physics_time_s']-trace[0]['physics_time_s'] for r in trace],np.arange(len(trace))/20,atol=1e-7)
    xml=ET.fromstring((directory/'scene.xml').read_text())
    for name,position in spec['regions'].items():
        marker=('human_public_plate_region' if name in {'near_human','plate_ready'} else 'human_public_region_'+name)
        geom=xml.find(f".//geom[@name='{marker}']");assert geom is not None
        np.testing.assert_allclose(np.fromstring(geom.attrib['pos'],sep=' ')[:2],position[:2],rtol=0,atol=1e-6)  # MuJoCo XML export rounds to six significant digits.
        assert float(geom.attrib['size'].split()[0])==.025
    for d in decisions:
        work=max((w for w in plan if w.time_s<=d['time_s']),key=lambda w:w.time_s)
        public=json.loads(d['public_input'].split('\n',1)[1])
        assert public['current_public_activity']['text']==work.instruction
        assert public['your_current_assignments']==[{'source':'public_dialogue','observed_at_s':work.time_s,
               'speaker':'environment','kind':'assignment','text':work.instruction,'object_id':work.object_id,
               'assigned_role':'human','destination':work.destination}]
        for name,surface in public['public_goal_surfaces'].items():
            assert surface['center_xyz']==list(spec['regions'][name]) and surface['radius_m']==.025
        assert not {'dynamic_activity','activity_evidence','physical_completion_observed','task_success'}.intersection(public)
    for call in calls:
        w=max((w for w in plan if w.time_s<=call['time_s']),key=lambda w:w.time_s)
        assert spec['robot_instruction'] in call['prompt'] and w.instruction in call['prompt']
        assert call['action_source']=='learned_vla'
    rebuilt=evaluate_activity(plan,spec['regions'],trace,controls,decisions,placement)
    assert read(directory/'activity_evidence.json')==rebuilt
    metrics=read(directory/'metrics.json')
    assert metrics['dynamic_activity']==rebuilt
    assert metrics['task_success']==rebuilt['joint_final_goal_success']
    assert metrics['human_goal_success']==rebuilt['human_final_goal_success']
    return {'episode':str(directory),'profile':spec['profile'],'status':'verified',
            'public_updates_in_human_inputs_verified':True,'public_updates_in_robot_prompts_verified':True,
            'marker_geometry_reconstructed':True,'continuous_physics_clock_verified':True,
            'activity_metrics_reconstructed':True,'decisions':len(decisions),'vla_calls':len(calls)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args();episodes=[verify_episode(p.parent) for p in sorted(args.input_dir.rglob('activity_plan.json'))]
    assert episodes
    provenance=read(args.input_dir/'provenance.json');assert not provenance['source_files_changed_during_run']
    (args.input_dir/'activity_verification.json').write_text(json.dumps({'status':'verified','episodes':episodes},ensure_ascii=False,indent=2))
    print(f'{len(episodes)}条动态工作任务和实际模型输入核查通过')


if __name__=='__main__':main()
