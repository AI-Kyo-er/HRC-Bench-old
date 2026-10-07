#!/usr/bin/env python3
"""生成可核对的候选样本表和当前磁盘模型指纹；不宣称正式评测已开始。"""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path

from hrc_pilot.joint_activity import ACTIVITIES
from hrc_pilot.joint_situations import SITUATIONS


SYSTEMS=('visual_coordinator_plus_vla','symbolic_coordinator_plus_vla')
PROFILES={'join':'busy','leave_return':'busy','change_use':'participating',
          'detour':'participating','correction':'particular','robot_request':'busy'}
MODELS={'human_and_symbolic_coordinator':'Qwen/Qwen3-14B',
        'visual_coordinator':'Qwen/Qwen3-VL-8B-Instruct','robot_vla':'lerobot/pi05-libero'}


def condition_rows():
    rows=[]
    for ai,activity in enumerate(ACTIVITIES):
        for si,situation in enumerate(SITUATIONS):
            for init in (4,5):
                seed=1000+ai*100+si*10+init
                for system in SYSTEMS:
                    rows.append({'sample_id':f'{activity}_{situation}_init{init}_{system}',
                        'activity':activity,'situation':situation,'init_state_id':init,'seed':seed,
                        'profile':PROFILES[situation],'system':system,'steps':2400,
                        'human_decision_steps':80,'coordinator_decision_steps':80,
                        'protocol_status':'candidate_not_frozen'})
    return rows


def content_record(path):
    before=path.stat();digest=sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(4*1024*1024),b''):digest.update(chunk)
    after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise RuntimeError('指纹计算期间文件变化：'+str(path))
    return {'path':str(path.resolve()),'bytes':after.st_size,'sha256':digest.hexdigest()}


def model_records(root):
    result={}
    for role,name in MODELS.items():
        folder=root/name;files=set()
        for index in folder.glob('*.safetensors.index.json'):
            files.add(index)
            files.update(folder/f for f in json.loads(index.read_text())['weight_map'].values())
        files.update(folder.glob('*.safetensors'))
        files.update(folder.glob('*.json'));files.update(folder.glob('*.txt'))
        if not any(p.suffix=='.safetensors' for p in files):raise ValueError('没有可核对的模型权重：'+str(folder))
        result[role]={'model_directory':str(folder.resolve()),'files':[content_record(p) for p in sorted(files)]}
    tokenizer=root/'Physical-Intelligence/openpi-cache/big_vision/paligemma_tokenizer.model'
    result['robot_language_tokenizer']={'files':[content_record(tokenizer)]}
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--model-root',type=Path,default=Path('/data1/sieniwgroup/sieniw/models'))
    parser.add_argument('--hash-model-files',action='store_true')
    args=parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=False)
    rows=condition_rows()
    with (args.output_dir/'candidate_conditions.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    receipt={'status':'candidate_not_frozen','samples':len(rows),'executed_formal_samples':0,
        'scope':'固定候选条件，不编码训练数据配对；不是正式结果或准入证书。',
        'readiness_requirements':['三活动伙伴条件有效','六情境真实行为覆盖','当前共同安排评分手册',
                                 '模型接口与初始化可比性','运行源与模型版本冻结'],
        'source_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
    (args.output_dir/'preparation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
    if args.hash_model_files:
        snapshot={'scope':'当前磁盘文件指纹；不追溯证明旧进程的内存参数，也不宣称协议已冻结。',
                  'models':model_records(args.model_root)}
        (args.output_dir/'model_file_fingerprints.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2))
    print(json.dumps({'candidate_samples':len(rows),'formal_samples_executed':0,'output':str(args.output_dir)},ensure_ascii=False))


if __name__=='__main__':main()
