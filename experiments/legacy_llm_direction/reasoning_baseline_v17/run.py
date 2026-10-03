"""固定Qwen3-14B两mode各40调用；原v4输入和评分不变。"""
import argparse
import copy
import datetime
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess
import time
from experiments.physical.run import ROOT,save,sha
from experiments.model_scale_v4.run import classify
from experiments.reasoning_baseline_v17.adapter import PARAMETERS,MAX_NEW_TOKENS,score

RESULT=ROOT/'results/reasoning_baseline_v17'
SOURCE=ROOT/'experiments/model_scale_v4/cases/freeze.json'
FREEZE=ROOT/'experiments/reasoning_baseline_v17/cases/freeze_v1.json'
SPEC=RESULT/'model_spec.json'
SOURCES=['experiments/reasoning_baseline_v17/'+n for n in ('assets.py','adapter.py','run.py')]+[
    'experiments/model_scale_v4/run.py','experiments/physical/protocol.py','experiments/physical_v3_2/progress.py','tests/test_reasoning_baseline_v17.py']


def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def hashes():return {n:sha(ROOT/n) for n in SOURCES}
def records():
    original=json.loads(SOURCE.read_text())['records'];assert len(original)==40
    return [dict(id=f'{mode}__{r["id"]}',mode=mode,case_index=i,seed=17000+i,record=copy.deepcopy(r),messages_sha256=digest(r['messages'])) for mode in PARAMETERS for i,r in enumerate(original)]

def freeze():
    from transformers import AutoTokenizer,Qwen3ForCausalLM
    if FREEZE.exists():raise RuntimeError('禁止覆盖冻结。')
    spec=json.loads(SPEC.read_text());tokenizer=AutoTokenizer.from_pretrained(spec['path'],local_files_only=True)
    rows=records()
    for row in rows:
        messages=row['record']['messages'];enabled=row['mode']=='thinking'
        row['rendered_template']=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=enabled)
        row['input_ids']=tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=enabled)
        assert row['input_ids']==tokenizer(row['rendered_template'],add_special_tokens=False)['input_ids']
        # 官方thinking模板只开assistant，由模型自己生成<think>；非thinking输入闭合空think。
        assert row['rendered_template'].endswith('<|im_start|>assistant\n') if enabled else row['rendered_template'].endswith('<think>\n\n</think>\n\n')
    max_input=max(len(r['input_ids']) for r in rows);c=spec['config']
    kv=2*c['num_hidden_layers']*c['num_key_value_heads']*c['head_dim']*2*(max_input+MAX_NEW_TOKENS)
    estimate=dict(maximum_input_tokens=max_input,maximum_output_tokens=MAX_NEW_TOKENS,maximum_total_tokens=max_input+MAX_NEW_TOKENS,
        bf16_weight_bytes=spec['total_weights_bytes'],kv_cache_bytes=kv,workspace_margin_bytes=3*1024**3,
        required_free_mib=math.ceil((spec['total_weights_bytes']+kv+3*1024**3)/1024**2),kv_basis='2(K,V)*layers*KVheads*head_dim*2(BF16)*max(input+output),batch1;额外3GiB工作区/上下文裕量')
    assert estimate['maximum_total_tokens']<c['max_position_embeddings']
    assert tokenizer.encode('</think>',add_special_tokens=False)==[151668]
    save(FREEZE,dict(version='reasoning-baseline-v17.1',records=rows,source_freeze_sha256=sha(SOURCE),source_sha256=hashes(),model_spec_sha256=sha(SPEC),model_spec=spec,
        parameters=PARAMETERS,max_new_tokens=MAX_NEW_TOKENS,dtype='bfloat16',attention='sdpa',batch=1,per_case_seed='17000+original_case_index，两mode同seed',memory_estimate=estimate,
        packages={n:importlib.metadata.version(n) for n in ('torch','transformers','tokenizers','huggingface-hub','accelerate')},
        gate={'single':16,'full_history':12,'aid_does_not_replace_full':True},
        supersedes_unexecuted_freeze_sha256=sha(ROOT/'experiments/reasoning_baseline_v17/cases/freeze.json'),
        parser='thinking按官方最后一个</think>(151668)边界，仅其后strict旧JSONparser，缺标记失败；nonthinking输入模板闭合空think，输出不接受think标记；不自动修复/重抽。'))
    print('冻结80',sha(FREEZE),estimate,flush=True)


def preflight(frozen):
    visible=os.environ.get('CUDA_VISIBLE_DEVICES','');assert visible.isdigit(),'必须指定单张物理GPU'
    raw=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
    selected=next(r.split(',') for r in raw.splitlines() if int(r.split(',')[0])==int(visible))
    receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=os.getpid(),physical_gpu=int(visible),all_gpu_query=raw,
        selected_free_mib=int(selected[4]),required_free_mib=frozen['memory_estimate']['required_free_mib'],estimate=frozen['memory_estimate'])
    assert receipt['selected_free_mib']>=receipt['required_free_mib'],receipt
    return receipt


def evaluate(mode):
    import torch
    from transformers import AutoTokenizer,Qwen3ForCausalLM
    f=json.loads(FREEZE.read_text());assert f['source_sha256']==hashes() and f['source_freeze_sha256']==sha(SOURCE) and f['model_spec_sha256']==sha(SPEC)
    assert f['packages']=={n:importlib.metadata.version(n) for n in f['packages']}
    download=json.loads((RESULT/'download_receipt.json').read_text());assert download['all_weights_match_official'] and download['revision']==f['model_spec']['revision']
    out=RESULT/'raw'/mode;out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise RuntimeError('禁止重复/覆写mode输出。')
    pf=preflight(f);save(out/'gpu_preflight.json',pf);print('GPU检查',pf,flush=True)
    tokenizer=AutoTokenizer.from_pretrained(download['path'],local_files_only=True)
    model=Qwen3ForCausalLM.from_pretrained(download['path'],local_files_only=True,torch_dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa').eval()
    torch.cuda.reset_peak_memory_stats();rows=[]
    for record in (r for r in f['records'] if r['mode']==mode):
        torch.manual_seed(record['seed']);torch.cuda.manual_seed_all(record['seed'])
        ids=tokenizer.apply_chat_template(record['record']['messages'],tokenize=True,add_generation_prompt=True,enable_thinking=mode=='thinking')
        assert ids==record['input_ids']
        inputs=torch.tensor([ids],dtype=torch.long,device='cuda:0');start=time.monotonic()
        with torch.inference_mode():output=model.generate(input_ids=inputs,attention_mask=torch.ones_like(inputs),**PARAMETERS[mode],max_new_tokens=MAX_NEW_TOKENS,pad_token_id=tokenizer.eos_token_id)
        generated=output[0,len(ids):].tolist();response=tokenizer.decode(generated,skip_special_tokens=True)
        scored=score(record['record'],response,mode);scored['errors']=classify(record['record'],scored['choice'],scored['parse_error'])
        eos=model.generation_config.eos_token_id;eos=[eos] if isinstance(eos,int) else eos
        prediction=dict(response=response,response_with_special_tokens=tokenizer.decode(generated,skip_special_tokens=False),generated_ids=generated,input_tokens=len(ids),output_tokens=len(generated),
            generation_hit_limit=len(generated)==MAX_NEW_TOKENS and generated[-1] not in eos,seconds=time.monotonic()-start)
        row=dict(record=record,prediction=prediction,**scored);rows.append(row);save(out/'calls.json',rows)
        print(len(rows),record['id'],scored['choice'],scored['acceptable'],len(generated),scored['errors'],flush=True)
    groups={}
    for view in ('single','full_history','public_progress_aid'):
        subset=[r for r in rows if r['record']['record']['view']==view];errors={}
        for row in subset:
            for error in row['errors']:errors[error]=errors.get(error,0)+1
        groups[view]=dict(total=len(subset),acceptable=sum(r['acceptable'] for r in subset),parse_errors=sum(r['parse_error'] is not None for r in subset),truncated=sum(r['prediction']['generation_hit_limit'] for r in subset),errors=errors)
    metadata=dict(model_id=f['model_spec']['model_id'],revision=f['model_spec']['revision'],model_path=download['path'],mode=mode,parameters=PARAMETERS[mode],max_new_tokens=MAX_NEW_TOKENS,
        packages=f['packages'],parameter_count=model.num_parameters(),dtype=str(model.dtype),cuda=torch.version.cuda,device=torch.cuda.get_device_name(0),physical_gpu=pf['physical_gpu'],attention='sdpa',quantization=None,offload=False,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
    summary=dict(groups=groups,gate_passed=groups['single']['acceptable']==16 and groups['full_history']['acceptable']==12,metadata=metadata,freeze_sha256=sha(FREEZE),source_sha256=hashes(),download_receipt_sha256=sha(RESULT/'download_receipt.json'))
    save(out/'summary.json',summary);save(RESULT/(mode+'_summary.json'),summary);print('完成',mode,groups,summary['gate_passed'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('freeze','evaluate'));p.add_argument('--mode',choices=tuple(PARAMETERS));a=p.parse_args();freeze() if a.stage=='freeze' else evaluate(a.mode)
