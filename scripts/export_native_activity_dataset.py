#!/usr/bin/env python3
"""导出真实策略观测及实际执行动作；失败保留，不将模型轨迹当作专家示范。"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

import numpy as np

from hrc_pilot.native_trajectory_dataset import NativeTrajectoryDataset,NativeMixedTrajectoryDataset


def rows(p):return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--include-coordination-primitives',action='store_true',help='使用带控制来源与学习动作掩码的混合策略数据契约')
    args=parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):parser.error('输出目录必须为空')
    frames=args.output_dir/'frames';frames.mkdir(parents=True)
    source_receipts=[];total=0;qualified_total=0;diagnostic_total=0;source_action_counts={}
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
        hand_path=root/'hand_verification.json'
        hand_qualified=all(e['motion_qualified'] for e in json.loads(hand_path.read_text())['episodes']) if hand_path.exists() else None
        eligible=motion_eligible and avatar_qualified is not False and hand_qualified is not False
        destination_frames=frames if eligible else args.output_dir/'diagnostic_frames'
        destination_frames.mkdir(exist_ok=True)
        prefix=(provenance['model_server_metadata']['config']+'__'+metrics['autonomous_human_context'] if autonomous else metrics['activity_profile'])
        if provenance.get('scene_case'):prefix+='__'+provenance['scene_case']['key']
        if provenance.get('human_policy_architecture','flat')!='flat':prefix+='__'+provenance['human_policy_architecture']
        if provenance.get('robot_planner_metadata'):prefix+='__visual_coordination'
        if args.include_coordination_primitives:prefix+='__mixed_control'
        identifier=f'{prefix}__task{metrics["task_id"]:02d}_init{metrics["init_state_id"]:03d}_seed{metrics["seed"]:03d}'
        if 'vla_language_interface' in provenance:
            identifier+='__language_'+provenance['vla_language_interface']
            identifier+='__persona_'+str(provenance.get('human_persona'))
            identifier+='__memory_'+str(provenance.get('human_memory_scope'))
        if provenance.get('human_command_delivery'):identifier+='__delivery_'+provenance['human_command_delivery']
        target=args.output_dir/'episodes'/identifier;target.mkdir(parents=True)
        activity_files=['personal_context.json','personal_evidence.json','human_intentions.jsonl','public_dialogue.jsonl'] if autonomous else ['activity_plan.json','activity_events.json','activity_evidence.json']
        source_files=activity_files+['metrics.json','scene.xml',
                      'trace.jsonl','human_policy_io.jsonl','human_control.jsonl','placement_evidence.jsonl','model_calls.jsonl','policy_io.jsonl','video_timeline.json']
        if (episode/'human_planner_io.jsonl').exists():source_files.append('human_planner_io.jsonl')
        if (episode/'robot_planner_io.jsonl').exists():
            assert json.loads((root/'coordination_verification.json').read_text())['status']=='verified'
            source_files.append('robot_planner_io.jsonl')
        for name in source_files:(target/name).symlink_to((episode/name).resolve())
        auxiliary_audits={}
        for name in ['relative_geometry_verification.json','multi_actor_release_verification.json','scene_integrity_verification.json','continual_activity_verification.json','hand_robot_contact_verification.json','spatial_motion_verification.json','coordination_verification.json','human_command_delivery_verification.json','cached_request_audit.json']:
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
                                'benchmark_episode_eligible':eligible,'motion_eligible':motion_eligible,'avatar_qualified':avatar_qualified,'hand_motion_qualified':hand_qualified,'world_initializations':1,'robot_model':provenance['model_server_metadata']['config'],
                                'robot_planner_metadata':provenance.get('robot_planner_metadata'),
                                'vla_language_interface':provenance.get('vla_language_interface'),
                                'human_command_delivery':provenance.get('human_command_delivery')})
        for call in calls:
            executed=[r['action'] for r in actions if r['model_call']==call['model_call']]
            assert executed
            source=call['action_source']
            if not args.include_coordination_primitives:assert source=='learned_vla','混合控制须显式启用来源契约'
            else:assert source in NativeMixedTrajectoryDataset.SOURCES
            stem=identifier+f'__step{call["step"]:06d}';base=destination_frames/stem
            shutil.copyfile(episode/call['exterior_artifact'],str(base)+'.png')
            shutil.copyfile(episode/call['wrist_artifact'],str(base)+'_wrist.png')
            np.save(str(base)+'.state.npy',np.asarray(call['state'],dtype=np.float32))
            np.save(str(base)+'.action.npy',np.asarray(executed,dtype=np.float32))
            np.save(str(base)+'.action_valid.npy',np.ones(len(executed),dtype=np.bool_))
            Path(str(base)+'.prompt.txt').write_text(call['prompt'])
            if args.include_coordination_primitives:Path(str(base)+'.action_source.txt').write_text(source)
            source_action_counts[source]=source_action_counts.get(source,0)+len(executed)
            total+=1
            if eligible:qualified_total+=1
            else:diagnostic_total+=1
    assert source_receipts
    action_count=qualified_actions=diagnostic_actions=0
    for directory,count in [(frames,qualified_total),(args.output_dir/'diagnostic_frames',diagnostic_total)]:
        if not count:continue
        loader=NativeMixedTrajectoryDataset if args.include_coordination_primitives else NativeTrajectoryDataset
        dataset=loader(directory);assert len(dataset)==count
        actual=sum(int(dataset[i]['action_valid'].sum()) for i in range(len(dataset)))
        action_count+=actual
        if directory==frames:qualified_actions=actual
        else:diagnostic_actions=actual
    metadata={'status':'exported_and_loaded','episodes':len(source_receipts),'observations':total,
              'actual_native_actions':action_count,'qualified_observations':qualified_total,'diagnostic_observations':diagnostic_total,
              'qualified_native_actions':qualified_actions,'diagnostic_native_actions':diagnostic_actions,
              'qualification_rule':'motion and available avatar/hand-motion gates; ineligible episodes retained only in diagnostic_frames, not in qualified frames',
              'pair_rule':'same stem .png / _wrist.png / .state.npy / .prompt.txt / .action.npy / .action_valid.npy',
              'label_semantics':'actual executed learned-policy OSC actions, not expert or successful-demonstration targets',
              'mixed_control_contract':args.include_coordination_primitives,'source_native_action_counts':source_action_counts,
              'split_rule':'keep complete episodes together; no frame-wise random train/test split',
              'episode_assets':'local symlinks to audited raw logs and runtime video; original scene mesh dependencies remain external',
              'sources':source_receipts}
    if args.include_coordination_primitives:
        metadata['label_semantics']='actual executed hybrid controls with explicit source; learned_vla_action_mask excludes holds and Cartesian primitives'
        metadata['pair_rule']+=' / .action_source.txt; all relationships resolved by the identical stem'
    (args.output_dir/'dataset_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
    print(f'{len(source_receipts)}条持续运行，{total}组实际观测，{action_count}个原生动作；合格观测{qualified_total}、诊断观测{diagnostic_total}；按stem加载通过')


if __name__=='__main__':main()
