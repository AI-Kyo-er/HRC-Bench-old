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
    source_receipts=[];total=0
    for plan in sorted(args.input_dir.rglob('activity_plan.json')):
        episode=plan.parent;root=episode.parents[1]
        provenance=json.loads((root/'provenance.json').read_text());metrics=json.loads((episode/'metrics.json').read_text())
        assert not provenance['source_files_changed_during_run']
        for name in ['video_verification.json','model_execution_verification.json','activity_verification.json']:
            assert json.loads((root/name).read_text())['status']=='verified'
        assert json.loads((root/'model_execution_verification.json').read_text())['motion_eligible_episode_count']==1
        identifier=f'{metrics["activity_profile"]}__task{metrics["task_id"]:02d}_init{metrics["init_state_id"]:03d}_seed{metrics["seed"]:03d}'
        target=args.output_dir/'episodes'/identifier;target.mkdir(parents=True)
        source_files=['activity_plan.json','activity_events.json','activity_evidence.json','metrics.json','scene.xml',
                      'trace.jsonl','human_policy_io.jsonl','human_control.jsonl','placement_evidence.jsonl','model_calls.jsonl','policy_io.jsonl','video_timeline.json']
        for name in source_files:(target/name).symlink_to((episode/name).resolve())
        (target/'demo.mp4').symlink_to((episode/'demo.mp4').resolve())
        trace=rows(episode/'trace.jsonl');actions=rows(episode/'policy_io.jsonl');calls=rows(episode/'model_calls.jsonl')
        np.save(target/'initial.qpos.npy',np.asarray(trace[0]['qpos']))
        np.save(target/'initial.qvel.npy',np.asarray(trace[0]['qvel']))
        source_receipts.append({'episode':identifier,'source':str(episode.resolve()),
                                'source_sha256':{n:sha256((episode/n).read_bytes()).hexdigest() for n in source_files},
                                'joint_success':metrics['task_success'],'world_initializations':1})
        for call in calls:
            executed=[r['action'] for r in actions if r['model_call']==call['model_call']]
            assert executed and call['action_source']=='learned_vla'
            stem=identifier+f'__step{call["step"]:06d}';base=frames/stem
            shutil.copyfile(episode/call['exterior_artifact'],str(base)+'.png')
            shutil.copyfile(episode/call['wrist_artifact'],str(base)+'_wrist.png')
            np.save(str(base)+'.state.npy',np.asarray(call['state'],dtype=np.float32))
            np.save(str(base)+'.action.npy',np.asarray(executed,dtype=np.float32))
            np.save(str(base)+'.action_valid.npy',np.ones(len(executed),dtype=np.bool_))
            Path(str(base)+'.prompt.txt').write_text(call['prompt'])
            total+=1
    assert source_receipts
    dataset=NativeTrajectoryDataset(frames);assert len(dataset)==total
    action_count=sum(int(dataset[i]['action_valid'].sum()) for i in range(len(dataset)))
    metadata={'status':'exported_and_loaded','episodes':len(source_receipts),'observations':total,
              'actual_native_actions':action_count,'pair_rule':'same stem .png / _wrist.png / .state.npy / .prompt.txt / .action.npy / .action_valid.npy',
              'label_semantics':'actual executed learned-policy OSC actions, not expert or successful-demonstration targets',
              'split_rule':'keep complete episodes together; no frame-wise random train/test split',
              'episode_assets':'local symlinks to audited raw logs and runtime video; original scene mesh dependencies remain external',
              'sources':source_receipts}
    (args.output_dir/'dataset_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
    print(f'{len(source_receipts)}条持续运行，{total}组实际观测，{action_count}个原生动作；按stem加载通过')


if __name__=='__main__':main()
