"""128次真实参考checkpoint离线单决策；不rollout、不设置新gate。"""
import argparse
import datetime
import json
import math
import os
import subprocess
from pathlib import Path

from experiments.physical.run import ROOT,save,sha,versions
from experiments.physical.protocol import parse
from experiments.model_scale_v4.backend import ConfigurableLocalModel
from experiments.state_readout_v13.dataset import build_records,public_truth,REPLACEMENTS
from experiments.state_readout_v13.scoring import parse_state,score_state
from experiments.structure_diagnostic_v12.scoring import score as action_score

RESULT=ROOT/'results/state_readout_v13'
FREEZE=ROOT/'experiments/state_readout_v13/cases/freeze.json'
INPUTS=RESULT/'raw/frozen_inputs.json'
SPEC=ROOT/'results/model_scale_v4/model_spec.json'
DOWNLOAD=ROOT/'results/model_scale_v4/download_receipt.json'
SOURCES=['experiments/state_readout_v13/dataset.py','experiments/state_readout_v13/scoring.py',
    'experiments/state_readout_v13/run.py','experiments/state_readout_v13/analysis.py',
    'experiments/model_scale_v4/backend.py','experiments/language/backend.py',
    'experiments/physical/protocol.py','experiments/structure_v11/protocol.py','experiments/structure_diagnostic_v9/analysis.py','experiments/structure_diagnostic_v12/scoring.py','experiments/structure_diagnostic_v12/analysis.py']


def source_hashes():return {n:sha(ROOT/n) for n in SOURCES}


def token_audit(records,model_path):
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True)
    rows=[dict(id=r['id'],stage=r['stage'],query=r['query'],seed=r['seed'],initial_blue=r['initial_blue'],effective_blue=r['effective_blue'],timing=r['timing'],acceptance=r['acceptance'],reverse_menu=r['reverse_menu'],
        input_tokens=len(tokenizer.apply_chat_template(r['messages'],tokenize=True,add_generation_prompt=True)),
        characters=sum(len(m['content']) for m in r['messages'])) for r in records]
    return rows


def freeze():
    if FREEZE.exists() or INPUTS.exists():raise RuntimeError('禁止覆盖冻结/原始输入。')
    records,sources=build_records()
    spec=json.loads(SPEC.read_text());download=json.loads(DOWNLOAD.read_text())
    if not download['all_weights_match_official'] or download['revision']!=spec['revision']:raise RuntimeError('官方权重来源未核验。')
    model_path=ROOT/'models/Qwen2.5-14B-Instruct'
    if model_path.resolve()!=Path(download['path']).resolve():raise RuntimeError('权重路径不一致。')
    lengths=token_audit(records,model_path)
    for r,l in zip(records,lengths):r['frozen_input_tokens']=l['input_tokens']
    save(INPUTS,records)
    maximum=max(r['input_tokens'] for r in lengths);config=spec['config']
    kv_bytes=(maximum+96)*config['num_hidden_layers']*config['num_key_value_heads']*(config['hidden_size']//config['num_attention_heads'])*2*2
    estimate=dict(max_input_tokens=maximum,max_output_tokens=96,bf16_weight_bytes=spec['total_weights_bytes'],
        kv_cache_bytes_upper_estimate=kv_bytes,kv_cache_mib_upper_estimate=kv_bytes/1024**2,
        required_free_mib=math.ceil((spec['total_weights_bytes']+3*1024**3)/1024**2),
        basis='BF16官方分片字节+3GiB，含短上下文KV/prefill/CUDA/裕量；单卡，不量化/offload。')
    save(FREEZE,dict(version='state-readout-v13.0',records=128,original_checkpoints=64,
        frozen_inputs_path=str(INPUTS.relative_to(ROOT)),frozen_inputs_sha256=sha(INPUTS),source_files_sha256=sources,
        source_sha256=source_hashes(),model_spec=spec,model_spec_sha256=sha(SPEC),download_receipt_sha256=sha(DOWNLOAD),
        packages=versions(),token_audit=lengths,memory_estimate=estimate,
        design='v12全部64 full，action原样重放及同user独立state query，128calls；不重跑旧aid。',
        system_replacements=[dict(old=old,new=new) for old,new in REPLACEMENTS],
        system_modification_points=[dict(old=old,count=records[0]['messages'][0]['content'].count(old),character_index=records[0]['messages'][0]['content'].index(old)) for old,new in REPLACEMENTS],
        generation=dict(seed=0,do_sample=False,max_new_tokens=96,dtype='bfloat16',attention='sdpa',batch_size=1),
        no_new_gate=True,old_gate_status='14B旧40门槛未通过；本诊断不替代/放宽。',
        interpretation='全部64原full观察的独立action/state报告；修改system任务指令，非内在知识读出/向action提供状态/闭环/显著性推断。'))
    print('128输入冻结',sha(FREEZE),'max_tokens',maximum,'required_mib',estimate['required_free_mib'],flush=True)


def gpu_preflight(frozen):
    visible=os.environ.get('CUDA_VISIBLE_DEVICES','')
    if not visible.isdigit():raise RuntimeError('必须显式指定唯一物理GPU。')
    raw=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
    selected=next(r.split(',') for r in raw.splitlines() if int(r.split(',')[0])==int(visible))
    record=dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),physical_gpu=int(visible),name=selected[1].strip(),
        memory_total_mib=int(selected[2]),memory_used_mib=int(selected[3]),memory_free_mib=int(selected[4]),
        required_free_mib=frozen['memory_estimate']['required_free_mib'],max_input_tokens=frozen['memory_estimate']['max_input_tokens'],raw_gpu_query=raw)
    if record['memory_free_mib']<record['required_free_mib']:raise RuntimeError(json.dumps(record,ensure_ascii=False))
    return record


def evaluate():
    frozen=json.loads(FREEZE.read_text())
    if frozen['source_sha256']!=source_hashes() or frozen['frozen_inputs_sha256']!=sha(INPUTS):raise RuntimeError('冻结源/输入改变。')
    for n,h in frozen['source_files_sha256'].items():
        if sha(ROOT/n)!=h:raise RuntimeError('原轨迹源变更。')
    if frozen['model_spec_sha256']!=sha(SPEC) or frozen['download_receipt_sha256']!=sha(DOWNLOAD):raise RuntimeError('模型来源规格改变。')
    output=RESULT/'raw/model'
    output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()):raise RuntimeError('禁止覆盖已开始的128调用。')
    preflight=gpu_preflight(frozen);save(output/'gpu_preflight.json',preflight)
    save(output/'started.json',dict(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        freeze_sha256=sha(FREEZE),inputs_sha256=sha(INPUTS),source_sha256=source_hashes(),gpu_preflight=preflight))
    print('GPU前检',json.dumps(preflight,ensure_ascii=False),flush=True)
    spec=frozen['model_spec'];model_path=ROOT/'models/Qwen2.5-14B-Instruct'
    model=ConfigurableLocalModel(model_path,spec['model_id'],spec['revision'],max_new_tokens=96)
    rows=[]
    for record in json.loads(INPUTS.read_text()):
        prediction=model.predict(record['messages'])
        if prediction['input_tokens']!=record['frozen_input_tokens']:raise RuntimeError('实际tokenizer长度与冻结不符。')
        obs=json.loads(record['messages'][1]['content'])
        if record['query']=='action_replay':
            choice,error=parse(prediction['response'],record['menu']);state_value=None
            scored=action_score(choice,error,obs,record['reference_action'])
        else:
            choice=None;state_value,error=parse_state(prediction['response'])
            scored=score_state(state_value,error,public_truth(obs))
        row=dict(record=record,prediction=prediction,choice=choice,state_value=state_value,parse_error=error,score=scored,truncated=prediction['generation_hit_limit'])
        rows.append(row);save(output/'calls.json',rows)
        print(len(rows),record['id'],choice if record['query']=='action_replay' else state_value,scored.get('protocol_progress',scored.get('joint_state_correct')),error,flush=True)
    from experiments.state_readout_v13.analysis import summarize
    summary=summarize(rows)
    summary.update(model=model.metadata(),gpu_preflight=preflight,freeze_sha256=sha(FREEZE),source_sha256=source_hashes(),
        inputs_sha256=sha(INPUTS),no_new_gate=True,interpretation=frozen['interpretation'])
    save(output/'summary.json',summary);save(RESULT/'summary.json',summary)
    save(output/'finished.json',dict(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),completed_calls=len(rows),model=model.metadata()))
    print('128调用完成',json.dumps(summary['by_stage'],ensure_ascii=False),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('freeze','evaluate'));args=parser.parse_args()
    freeze() if args.stage=='freeze' else evaluate()
