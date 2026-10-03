"""冻结216输入，一次greedy文本生成；两模型各用隔离环境，顺序运行。"""
import argparse
import datetime
import json
import math
import os
import subprocess

from experiments.physical.run import ROOT,save,sha
from experiments.state_calibration_v14.dataset import RESULT,build_records
from experiments.state_calibration_v14.scoring import score_record
from experiments.state_calibration_v14.analysis import summarize

FREEZE=ROOT/'experiments/state_calibration_v14/cases/freeze.json'
INPUTS=RESULT/'raw/frozen_inputs.json'
MODELS={'qwen2_5_14b':dict(path=ROOT/'models/Qwen2.5-14B-Instruct',env=ROOT/'.venv-llm/bin/python',model_id='Qwen/Qwen2.5-14B-Instruct'),
        'qwen3_vl_8b':dict(path=ROOT/'models/Qwen3-VL-8B-Instruct',env=ROOT/'.venv-qwen3-v14/bin/python',model_id='Qwen/Qwen3-VL-8B-Instruct')}
SOURCES=['experiments/state_calibration_v14/'+n for n in ('dataset.py','backend.py','scoring.py','analysis.py','run.py')]+[
    'experiments/state_readout_v13/semantic.py','experiments/state_readout_v13/scoring.py','experiments/state_readout_v13/analysis.py','experiments/state_readout_v13/dataset.py',
    'experiments/structure_v11/protocol.py','experiments/structure_diagnostic_v12/scoring.py','experiments/structure_diagnostic_v12/analysis.py',
    'experiments/model_scale_v4/backend.py','experiments/model_scale_v4/run.py','experiments/language/backend.py','experiments/physical/protocol.py']
SOURCE_INPUTS=['results/state_readout_v13/raw/frozen_inputs.json','experiments/state_readout_v13/cases/freeze.json',
    'experiments/model_scale_v4/cases/freeze.json','results/state_calibration_v14/model_receipt.json','results/state_calibration_v14/environment_receipt.json',
    'results/model_scale_v4/download_receipt.json']


def hashes(names):return {n:sha(ROOT/n) for n in names}


def tokens(model):
    from transformers import AutoTokenizer
    rows=[r for r in json.loads((RESULT/'raw/prepared_inputs.json').read_text()) if r['model']==model]
    tokenizer=AutoTokenizer.from_pretrained(MODELS[model]['path'],local_files_only=True)
    lengths=[]
    for r in rows:
        rendered=tokenizer.apply_chat_template(r['messages'],tokenize=False,add_generation_prompt=True)
        assert all(m['content'] in rendered for m in r['messages'])
        ids=tokenizer.apply_chat_template(r['messages'],tokenize=True,return_dict=False,add_generation_prompt=True)
        assert isinstance(ids,list) and len(ids)>10
        lengths.append(dict(id=r['id'],tokens=len(ids),characters=sum(len(m['content']) for m in r['messages'])))
    save(RESULT/f'raw/tokens_{model}.json',lengths)


def freeze():
    if FREEZE.exists() or INPUTS.exists():raise RuntimeError('禁止覆盖冻结。')
    records=build_records();save(RESULT/'raw/prepared_inputs.json',records)
    models={}
    new=json.loads((RESULT/'model_receipt.json').read_text());old=json.loads((ROOT/'results/model_scale_v4/model_spec.json').read_text())
    assert new['local_all_passed']
    for name,spec in MODELS.items():
        subprocess.run([str(spec['env']),'-m','experiments.state_calibration_v14.run','tokens','--model',name],check=True)
        lengths=json.loads((RESULT/f'raw/tokens_{name}.json').read_text());maximum=max(r['tokens'] for r in lengths)
        config=(old['config'] if name=='qwen2_5_14b' else new['config']['text_config'])
        weights=old['total_weights_bytes'] if name=='qwen2_5_14b' else new['total_weight_bytes']
        head_dim=config.get('head_dim',config['hidden_size']//config['num_attention_heads'])
        kv=(maximum+96)*config['num_hidden_layers']*config['num_key_value_heads']*head_dim*4
        models[name]=dict(model_id=spec['model_id'],path=str(spec['path'].resolve()),environment=str(spec['env'].parent.parent.resolve()),
            revision=old['revision'] if name=='qwen2_5_14b' else new['revision'],records=len(lengths),max_input_tokens=maximum,
            kv_bytes_estimate=kv,kv_mib_estimate=kv/1024**2,weight_bytes=weights,required_free_mib=math.ceil((weights+3*1024**3)/1024**2),
            token_audit=lengths,estimate='BF16全部权重+3GiB，含短上下文KV/prefill/CUDA/裕量，单卡。')
        lookup={r['id']:r['tokens'] for r in lengths}
        for r in records:
            if r['model']==name:r['frozen_input_tokens']=lookup[r['id']]
    save(INPUTS,records)
    save(FREEZE,dict(version='state-calibration-v14.0',total_calls=216,source_sha256=hashes(SOURCES),source_inputs_sha256=hashes(SOURCE_INPUTS),
        inputs_sha256=sha(INPUTS),models=models,generation=dict(seed=0,do_sample=False,max_new_tokens=96,dtype='bfloat16',attention='sdpa',batch_size=1),
        design='24基础控制×两模型48，Qwen3原v13全部128+原v4全部40，共216。基础纯文本，不执行物理，不调提示。',
        controls_synthetic=True,controls_not_new_gate=True,json_key_order_compliance_separate=True,
        v4_gate=dict(single_required=16,full_history_required=12),no_new_downloaded_weights=True))
    print('冻结',sha(FREEZE),json.dumps({n:{k:v for k,v in s.items() if k in ('records','max_input_tokens','required_free_mib')} for n,s in models.items()}),flush=True)


def gpu_preflight(spec):
    visible=os.environ.get('CUDA_VISIBLE_DEVICES','')
    if not visible.isdigit():raise RuntimeError('须显式唯一物理GPU。')
    raw=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
    selected=next(r.split(',') for r in raw.splitlines() if int(r.split(',')[0])==int(visible))
    record=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),physical_gpu=int(visible),memory_free_mib=int(selected[4]),required_free_mib=spec['required_free_mib'],raw_gpu_query=raw)
    if record['memory_free_mib']<record['required_free_mib']:raise RuntimeError(json.dumps(record))
    return record


def evaluate(name):
    frozen=json.loads(FREEZE.read_text());assert frozen['source_sha256']==hashes(SOURCES) and frozen['source_inputs_sha256']==hashes(SOURCE_INPUTS) and frozen['inputs_sha256']==sha(INPUTS)
    import sys
    assert str(MODELS[name]['env'].parent.parent.resolve())==str(__import__('pathlib').Path(sys.prefix).resolve())
    spec=frozen['models'][name];output=RESULT/f'raw/model_{name}';output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()):raise RuntimeError('禁止覆盖已开始调用。')
    pre=gpu_preflight(spec);save(output/'gpu_preflight.json',pre)
    save(output/'started.json',dict(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),freeze_sha256=sha(FREEZE),gpu_preflight=pre))
    if name=='qwen2_5_14b':
        from experiments.model_scale_v4.backend import ConfigurableLocalModel
        cls=ConfigurableLocalModel
    else:
        from experiments.state_calibration_v14.backend import LocalQwen3Text
        cls=LocalQwen3Text
    model=cls(spec['path'],spec['model_id'],spec['revision'],max_new_tokens=96)
    records=[r for r in json.loads(INPUTS.read_text()) if r['model']==name];rows=[]
    for record in records:
        prediction=model.predict(record['messages'])
        assert prediction['input_tokens']==record['frozen_input_tokens']
        row=dict(record=record,prediction=prediction,truncated=prediction['generation_hit_limit'],**score_record(record,prediction['response']))
        rows.append(row);save(output/'calls.json',rows)
        print(len(rows),'/',len(records),record['id'],row['choice'] or row['state_value'],row['score'].get('joint_state_correct',row['score'].get('protocol_progress',row['score'].get('acceptable'))),flush=True)
    summary=summarize(rows);summary['model']=model.metadata();save(output/'summary.json',summary)
    save(output/'finished.json',dict(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),calls=len(rows),model=model.metadata()))
    print('完成',len(rows),'calls',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('tokens','freeze','evaluate'));p.add_argument('--model',choices=MODELS);a=p.parse_args()
    if a.stage=='freeze':freeze()
    elif a.stage=='tokens':tokens(a.model)
    else:evaluate(a.model)
