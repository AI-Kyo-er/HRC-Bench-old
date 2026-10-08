#!/usr/bin/env python3
"""对保存的真实人输入运行一次有限文本生成，不执行Sim或修复原轨迹。"""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True)
    parser.add_argument('--time-s',type=float,required=True)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists():raise ValueError('禁止覆盖已存在的接口检查')
    selected=os.environ.get('CUDA_VISIBLE_DEVICES')
    values=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.free',
        '--format=csv,noheader,nounits'],text=True)
    free={line.split(',')[0].strip():int(line.split(',')[1]) for line in values.splitlines()}
    required=sum(p.stat().st_size for p in args.model.glob('*.safetensors'))//1024**2+8192
    if selected not in free or free[selected]<required:raise ValueError('需要显存足够的单张GPU')
    source=args.input_dir/'episode/human_policy_io.jsonl'
    lines=[line for line in source.read_text().splitlines() if line.strip()]
    index=next(i for i,line in enumerate(lines) if json.loads(line)['time_s']==args.time_s)
    line=lines[index];row=json.loads(line)
    from hrc_pilot.bounded_human_protocol import bounded_output_schema
    import hrc_pilot.reasoning_constrained_human as reasoning
    from hrc_pilot.constrained_human_decision import parse_constrained_decision
    from hrc_pilot.joint_activity import ACTIVITIES
    from jsonschema import validate,ValidationError
    import torch

    original_tool=reasoning.constrained_tool;original_schema=reasoning.decision_json_schema
    def tool(scene):
        value=deepcopy(original_tool(scene))
        value['function']['parameters']=bounded_output_schema(value['function']['parameters'])
        return value
    reasoning.constrained_tool=tool
    reasoning.decision_json_schema=lambda scene:bounded_output_schema(original_schema(scene))
    activity=row['private_input']['activity']['key']
    policy=reasoning.ReasoningConstrainedHumanPolicy(ACTIVITIES[activity],model_path=args.model,seed=args.seed)
    policy._current_source_scene=deepcopy(row['observation_source_scene'])
    payload=deepcopy(row['native_tool_model_input'])
    args.output_dir.mkdir(parents=True)
    source_files=[Path(__file__),Path('src/hrc_pilot/bounded_human_protocol.py'),
        Path('src/hrc_pilot/reasoning_constrained_human.py'),Path('src/hrc_pilot/thinking_schema_filter.py'),
        Path('src/hrc_pilot/llm_human.py')]
    provenance={'role':'one_saved_input_neural_interface_check_not_sim_benchmark',
        'input_run':args.input_dir.name,'source_nonempty_row':index,'source_record_sha256':sha256(line.encode()).hexdigest(),
        'model':str(args.model.resolve()),'seed':args.seed,'cuda_visible_devices':selected,
        'source_sha256':{str(p):sha256(p.read_bytes()).hexdigest() for p in source_files},
        'overrides':'仅本独立进程的constrained_tool及decision_json_schema自由文本长度；不修改源文件',
        'agenda':'使用源记录的实际已生成私人意图及原有历史；不生成新的独立活动前缀',
        'neural_inferences':1,'sim_action_execution':False,'formal_samples':0}
    (args.output_dir/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
    started=time.perf_counter()
    try:
        policy.prepare()
        load_wall_s=time.perf_counter()-started
        torch.manual_seed(args.seed)
        started=time.perf_counter()
        raw=policy._generate_tool(payload)
    except Exception as error:
        (args.output_dir/'failure.json').write_text(json.dumps({'error':str(error)},ensure_ascii=False,indent=2))
        raise
    choice=normalization=call=None;parse_error=None
    try:
        validate(json.loads(policy._generated_json),policy._current_schema)
        choice,normalization,call=parse_constrained_decision(raw,policy._current_source_scene)
    except (ValueError,TypeError,KeyError,ValidationError) as error:parse_error=str(error)
    result={'status':'actual_neural_interface_result','time_s':args.time_s,'latency_wall_s':time.perf_counter()-started,
        'model_load_wall_s':load_wall_s,
        'parse_error':parse_error,'choice':choice,'selected_tool_call':call,'contribution_normalization':normalization,
        'model_input':payload,'output_json_schema':policy._current_schema,'input_token_ids':policy._current_token_ids,
        'actual_generated_json':policy._generated_json,'actual_generated_token_ids':policy._generated_token_ids,
        'reasoning_text':policy._reasoning_text,'reasoning_token_ids':policy._reasoning_token_ids,
        'whole_generated_token_ids':policy._whole_output_token_ids,'actual_raw_generated_text':policy._raw_generated_text,
        'reasoning_close_forced':policy._forced_close,'raw_output':raw,
        'inference_precision':getattr(policy,'inference_precision',None),
        'scope':'实际生成、解析及选择记录；无Sim动作或完整伙伴历史，不认证语义、协作、单因素效果或真人拟真。'}
    (args.output_dir/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'status':result['status'],'parse_error':parse_error,'choice':choice,
        'generated_tokens':len(policy._whole_output_token_ids),'latency_wall_s':result['latency_wall_s']},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
