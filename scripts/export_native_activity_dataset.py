#!/usr/bin/env python3
"""导出真实策略观测及实际执行动作；失败保留，不将模型轨迹当作专家示范。"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

import numpy as np

from hrc_pilot.native_trajectory_dataset import NativeTrajectoryDataset


def rows(p):return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('输出目录必须为空')
    frames=args.output_dir/'frames';frames.mkdir(parents=True)
    source_receipts=[];total=0;qualified_total=0;diagnostic_total=0
    plans=sorted(args.input_dir.rglob('activity_plan.json'))+sorted(args.input_dir.rglob('personal_context.json'))
    for plan in plans:
        episode=plan.parent;root=episode.parents[1]
        provenance=json.loads((root/'provenance.json').read_text());metrics=json.loads((episode/'metrics.json').read_text())
        assert not provenance['source_files_changed_during_run']
        autonomous=plan.name=='personal_context.json'
        verification='personal_verification.json' if autonomous else 'activity_verification.json'
        for name in ['video_verification.json','model_execution_verification.json',verification]:
            assert json.loads((root/name).read_text())['status']=='verified'
        motion_eligible=json.loads((root/'model_execution_verification.json').read_text())['motion_eligible_episode_count']==1
        avatar_path=root/'avatar_verification.json'
        avatar_qualified=json.loads(avatar_path.read_text())['qualified_count']==1 if avatar_path.exists() else None
        eligible=motion_eligible and avatar_qualified is not False
        destination_frames=frames if eligible else args.output_dir/'diagnostic_frames'
        destination_frames.mkdir(exist_ok=True)
        prefix=(provenance['model_server_metadata']['config']+'__'+metrics['autonomous_human_context'] if autonomous else metrics['activity_profile'])
        if provenance.get('scene_case'):prefix+='__'+provenance['scene_case']['key']
        identifier=f'{prefix}__task{metrics["task_id"]:02d}_init{metrics["init_state_id"]:03d}_seed{metrics["seed"]:03d}'
        target=args.output_dir/'episodes'/identifier;target.mkdir(parents=True)
        activity_files=['personal_context.json','personal_evidence.json','human_intentions.jsonl','public_dialogue.jsonl'] if autonomous else ['activity_plan.json','activity_events.json','activity_evidence.json']
        source_files=activity_files+['metrics.json','scene.xml',
                      'trace.jsonl','human_policy_io.jsonl','human_control.jsonl','placement_evidence.jsonl','model_calls.jsonl','policy_io.jsonl','video_timeline.json']
        for name in source_files:(target/name).symlink_to((episode/name).resolve())
        auxiliary_audits={}
        for name in ['relative_geometry_verification.json','multi_actor_release_verification.json','scene_integrity_verification.json']:
            path=root/name
            if path.exists():
                (target/name).symlink_to(path.resolve())
                auxiliary_audits[name]={'source':str(path.resolve()),'sha256':sha256(path.read_bytes()).hexdigest()}
        (target/'demo.mp4').symlink_to((episode/'demo.mp4').resolve())
        trace=rows(episode/'trace.jsonl');actions=rows(episode/'policy_io.jsonl');calls=rows(episode/'model_calls.jsonl')
        np.save(target/'initial.qpos.npy',np.asarray(trace[0]['qpos']))
        np.save(target/'initial.qvel.npy',np.asarray(trace[0]['qvel']))
        storage_path=root/'storage_verification.json'
        stored_joint=metrics['task_success']
        score_protocol='recorded_episode_protocol'
        if storage_path.exists():
            candidates=json.loads(storage_path.read_text())['episodes']
            match=next(r for r in candidates if Path(r['episode']).resolve()==episode.resolve())
            stored_joint=match['final_joint_released_stable'];score_protocol='posthoc_released_support_protocol'
        source_receipts.append({'episode':identifier,'source':str(episode.resolve()),'auxiliary_audits':auxiliary_audits,
                                'source_sha256':{n:sha256((episode/n).read_bytes()).hexdigest() for n in source_files},
                                'joint_success':stored_joint if eligible and metrics.get('human_goal_evaluable',True) else None,
                                'raw_joint_predicate':metrics['task_success'],'joint_success_protocol':score_protocol,
                                'joint_goal_evaluable':metrics.get('human_goal_evaluable',True),
                                'benchmark_episode_eligible':eligible,'motion_eligible':motion_eligible,'avatar_qualified':avatar_qualified,'world_initializations':1,'robot_model':provenance['model_server_metadata']['config']})
        for call in calls:
            executed=[r['action'] for r in actions if r['model_call']==call['model_call']]
            assert executed and call['action_source']=='learned_vla'
            stem=identifier+f'__step{call["step"]:06d}';base=destination_frames/stem
            shutil.copyfile(episode/call['exterior_artifact'],str(base)+'.png')
            shutil.copyfile(episode/call['wrist_artifact'],str(base)+'_wrist.png')
            np.save(str(base)+'.state.npy',np.asarray(call['state'],dtype=np.float32))
            np.save(str(base)+'.action.npy',np.asarray(executed,dtype=np.float32))
            np.save(str(base)+'.action_valid.npy',np.ones(len(executed),dtype=np.bool_))
            Path(str(base)+'.prompt.txt').write_text(call['prompt'])
            total+=1
            if eligible:qualified_total+=1
            else:diagnostic_total+=1
    assert source_receipts
    action_count=qualified_actions=diagnostic_actions=0
    for directory,count in [(frames,qualified_total),(args.output_dir/'diagnostic_frames',diagnostic_total)]:
        if not count:continue
        dataset=NativeTrajectoryDataset(directory);assert len(dataset)==count
        actual=sum(int(dataset[i]['action_valid'].sum()) for i in range(len(dataset)))
        action_count+=actual
        if directory==frames:qualified_actions=actual
        else:diagnostic_actions=actual
    metadata={'status':'exported_and_loaded','episodes':len(source_receipts),'observations':total,
              'actual_native_actions':action_count,'qualified_observations':qualified_total,'diagnostic_observations':diagnostic_total,
              'qualified_native_actions':qualified_actions,'diagnostic_native_actions':diagnostic_actions,
              'qualification_rule':'motion and available avatar gates; ineligible episodes retained only in diagnostic_frames, not in qualified frames',
              'pair_rule':'same stem .png / _wrist.png / .state.npy / .prompt.txt / .action.npy / .action_valid.npy',
              'label_semantics':'actual executed learned-policy OSC actions, not expert or successful-demonstration targets',
              'split_rule':'keep complete episodes together; no frame-wise random train/test split',
              'episode_assets':'local symlinks to audited raw logs and runtime video; original scene mesh dependencies remain external',
              'sources':source_receipts}
    (args.output_dir/'dataset_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
    print(f'{len(source_receipts)}条持续运行，{total}组实际观测，{action_count}个原生动作；合格观测{qualified_total}、诊断观测{diagnostic_total}；按stem加载通过')


if __name__=='__main__':main()
