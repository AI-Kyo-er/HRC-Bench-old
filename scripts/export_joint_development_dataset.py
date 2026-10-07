#!/usr/bin/env python3
"""按稳定run目录软链完整开发数据，并全量核查实际动作；不创建配对manifest。"""
import argparse
import json
from pathlib import Path

from hrc_pilot.joint_activity_dataset import JointActivityDataset
from build_joint_progress_report import RUNS


def export(results,output):
    output.mkdir(parents=True,exist_ok=True)
    for name,_,_ in RUNS:
        source=results/name
        if not (source/'summary.json').is_file():continue
        video=json.loads((source/'independent_video_verification.json').read_text())
        if video['status']!='verified':raise ValueError(name+'视频未核查')
        run=output/name;run.mkdir(exist_ok=True)
        link=run/'episode';target=(source/'episode').resolve()
        if link.exists():
            if link.resolve()!=target:raise ValueError('已有同名目录指向不同来源：'+str(link))
        else:link.symlink_to(target,target_is_directory=True)
    dataset=JointActivityDataset(output);actions=0;ids=set();counts={}
    for i in range(len(dataset)):
        source,target,meta=dataset[i]
        if meta['sample_id'] in ids:raise ValueError('样本标识重复')
        ids.add(meta['sample_id']);actions+=len(target)
        counts[meta['action_source']]=counts.get(meta['action_source'],0)+1
        if set(source)!={'image','wrist_image','state','prompt'}:raise ValueError('机器人输入边界改变')
    report={'status':'verified','episodes':len(dataset.episodes),'observation_blocks':len(dataset),
        'actual_executed_actions':actions,'distinct_sample_ids':len(ids),'source_counts':counts,
        'private_human_state_in_robot_input':False,'role':'development_behavior_not_success_expert_data',
        'formal_split':'not_frozen'}
    (output/'dataset_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    (output/'README.md').write_text(f'''# 动态共同活动开发行为数据

{report['episodes']}条完整运行、{report['observation_blocks']}组观测、{report['actual_executed_actions']}步实际动作。
包含参考控制、真实VLA、协调保持和失败行为；不是成功专家标签，正式训练／测试划分尚未冻结。

按 `<run>/episode/observation_<step>` 同stem匹配 `.png`、`_wrist.png`、`_state.npy`、`_actions.npy`。
run/episode软链到保留的原始结果，不重复大文件，不用manifest配对。
JointActivityDataset从真实robot_control恢复已执行动作前缀，给出跨run唯一sample_id；机器人输入只含实际相机、状态和prompt。
人私有策略、协调推理和公开交流保留在原始episode，供研究审阅，不直接注入机器人训练输入。

全量加载核查与各动作来源数量见dataset_verification.json。未执行尾部不当标签；适配模型前须另行确定用途、有效标签和数据划分，开发数据不冒充正式评测。
''')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir',type=Path,default=Path('results/continuous_v2'))
    parser.add_argument('--output-dir',type=Path,default=Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/dynamic_joint_activity_dev_20261008'))
    args=parser.parse_args();export(args.results_dir,args.output_dir)
