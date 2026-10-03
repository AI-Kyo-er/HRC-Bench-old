"""先12明确识别，再独立24真实自主闭环；不按结果筛选或自动重抽。"""
import argparse
import copy
import datetime
import importlib.metadata
import json
import math
import os
import subprocess
import time
import traceback
from experiments.physical.run import ROOT,save,sha,asset_hashes,versions
from experiments.reasoning_baseline_v17.adapter import PARAMETERS,MAX_NEW_TOKENS
from experiments.sustained_activity_v18.run import SOURCES as OLD_SOURCES,terminal_score
from experiments.sustained_activity_v18.protocol import Episode,SYSTEM,candidates
from experiments.responsive_transport_v16.world import ResponsiveWorld,DT
from experiments.responsive_transport_v16.canonical import trace_digest
from experiments.structure_v5.run import keyframe
from experiments.sustained_model_v19.inputs import base_cases,messages,recognition_records,digest

RESULT=ROOT/'results/sustained_model_v19';FREEZE=ROOT/'experiments/sustained_model_v19/cases/freeze.json'
SOURCES=OLD_SOURCES+['experiments/sustained_model_v19/'+n for n in ('inputs.py','backend.py','run.py')]+[
    'experiments/reasoning_baseline_v17/adapter.py','experiments/physical/protocol.py','tests/test_sustained_model_v19.py']
def hashes():return {n:sha(ROOT/n) for n in SOURCES}

def initial_records():
    records=[]
    for view in ('full_history','public_ledger_aid'):
        for case in base_cases():
            ident=f'Reference_{case["initial_blue"]}_{case["update"]}_{case["availability"]}_public_ledger_parallel_100'
            path=ROOT/'results/sustained_activity_v18/raw/reference'/ident/'decisions.json'
            row=json.loads(path.read_text())[0];o=row['observation']
            records.append(dict(id=f'{view}_{case["index"]:02d}',view=view,case=case,initial_observation=copy.deepcopy(o),initial_messages=messages(o,view),
                source_case=ident,source_sequence=0,source_observation_sha256=digest(o),source_messages_sha256=digest(row['messages'])))
    return records

def freeze():
    from transformers import AutoTokenizer,Qwen3ForCausalLM
    if FREEZE.exists():raise RuntimeError('禁止覆盖冻结')
    predecessor=ROOT/'results/sustained_activity_v18';proof={}
    for stage,count in (('recovery',4),('negative',4),('reference',48)):
        a=json.loads((predecessor/f'{stage}_audit.json').read_text());assert a['passed']==count
        proof[stage]=sha(predecessor/f'{stage}_audit.json')
    receipt=json.loads((predecessor/'execution_receipt.json').read_text());assert all(h['run_exit_code']==h['audit_exit_code']==0 for h in receipt['handles'].values())
    old=json.loads((ROOT/'experiments/reasoning_baseline_v17/cases/freeze_v1.json').read_text());spec=old['model_spec']
    download=json.loads((ROOT/'results/reasoning_baseline_v17/download_receipt.json').read_text());assert download['all_weights_match_official'] and download['revision']==spec['revision']
    tokenizer=AutoTokenizer.from_pretrained(spec['path'],local_files_only=True);identification=recognition_records(ROOT);episodes=initial_records()
    token_lengths=[]
    for r in identification:
        r['input_ids']=tokenizer.apply_chat_template(r['messages'],tokenize=True,add_generation_prompt=True,enable_thinking=True);token_lengths.append(len(r['input_ids']))
    for r in episodes:
        r['initial_input_ids']=tokenizer.apply_chat_template(r['initial_messages'],tokenize=True,add_generation_prompt=True,enable_thinking=True);token_lengths.append(len(r['initial_input_ids']))
    # 资源规划用实际参考中最长输入，再留足12步新反馈及账本增长裕量。此探针不作为任何正式模型输入。
    observed_lengths=[]
    for c in base_cases():
        ident=f'Reference_{c["initial_blue"]}_{c["update"]}_{c["availability"]}_public_ledger_parallel_100'
        for row in json.loads((predecessor/'raw/reference'/ident/'decisions.json').read_text()):
            for view in ('full_history','public_ledger_aid'):
                observed_lengths.append(len(tokenizer.apply_chat_template(messages(row['observation'],view),tokenize=True,add_generation_prompt=True,enable_thinking=True)))
    actual_max=max(token_lengths+observed_lengths);bound=max(8192,actual_max+4096);config=spec['config']
    assert bound+MAX_NEW_TOKENS<=config['max_position_embeddings'];assert tokenizer.encode('</think>',add_special_tokens=False)==[151668]
    kv=2*config['num_hidden_layers']*config['num_key_value_heads']*config['head_dim']*2*(bound+MAX_NEW_TOKENS)
    estimate=dict(frozen_input_max_tokens=max(token_lengths),reference_dynamic_max_tokens=max(observed_lengths),input_upper_bound_tokens=bound,output_tokens=MAX_NEW_TOKENS,total_context_bound=bound+MAX_NEW_TOKENS,
        model_max_position_embeddings=config['max_position_embeddings'],weight_bytes=spec['total_weights_bytes'],kv_bytes=kv,workspace_margin_bytes=3*1024**3,
        required_free_mib=math.ceil((spec['total_weights_bytes']+kv+3*1024**3)/1024**2),basis='batch1 BF16：2KV*layers*KVheads*head_dim*2bytes*(inputbound+8192)，实际参考最大输入+4096至少8192；超界保存基础设施失败，不截历史/不重抽。')
    save(FREEZE,dict(version='sustained-model-v19.0',source_sha256=hashes(),assets_sha256=asset_hashes(),physics_packages=versions(),
        packages={n:importlib.metadata.version(n) for n in ('torch','transformers','tokenizers','huggingface-hub','accelerate')},model_spec=spec,download_receipt_sha256=sha(ROOT/'results/reasoning_baseline_v17/download_receipt.json'),
        v18_audit_sha256=proof,v18_receipt_sha256=sha(predecessor/'execution_receipt.json'),identification=identification,episodes=episodes,system=SYSTEM,candidates=candidates(),step_budget=12,
        parameters=PARAMETERS['thinking'],max_new_tokens=MAX_NEW_TOKENS,dtype='bfloat16',attention='sdpa',memory_estimate=estimate,
        seed_rule='识别1909000+固定条目索引；闭环190000+基础caseindex*100+从0开始decisionindex，两view相同规则。',
        invalid_rule='缺think边界/空final/严格JSON或候选失败：ep.act(None)，耗1决策0物理tick、公开未知候选反馈；无fallback、重试。',
        dynamic_input_rule='只冻结初始观察/案例/构造源。自主后续完整history由本回合实际事件产生，逐步保存和后审计；不以参考后续状态替换。'))
    print('冻结',sha(FREEZE),estimate,flush=True)

def preflight(f):
    visible=os.environ.get('CUDA_VISIBLE_DEVICES','');assert visible.isdigit()
    query=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
    selected=next(line.split(',') for line in query.splitlines() if int(line.split(',')[0])==int(visible))
    result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=os.getpid(),physical_gpu=int(visible),query=query,free_mib=int(selected[4]),required_free_mib=f['memory_estimate']['required_free_mib'])
    save(RESULT/'raw/gpu_preflight.json',result);assert result['free_mib']>=result['required_free_mib'];return result

def rollout(record,backend):
    case=record['case'];folder=RESULT/'raw/episodes'/record['id'];folder.mkdir(parents=True)
    world=ResponsiveWorld(case['seed'],case['availability'],trace_path=folder/'ticks.jsonl.gz');ep=Episode(world,case['initial_blue'],case['update'],12)
    rows=[];start=time.monotonic();initial=copy.deepcopy(world.state())
    try:
        assert ep.observation()==record['initial_observation'];assert messages(ep.observation(),record['view'])==record['initial_messages']
        keyframe(world,folder/'frames')
        for index in range(12):
            if ep.terminated:break
            o=ep.observation();m=messages(o,record['view']);before=copy.deepcopy(world.state());history_before=copy.deepcopy(ep.history)
            prediction=backend.generate(m,190000+case['index']*100+index)
            result=ep.act(prediction['choice']) # None为非法解析，也耗一次真实决策。
            after=copy.deepcopy(world.state())
            rows.append(dict(sequence=index,observation=o,messages=m,prediction=prediction,choice=prediction['choice'],result=result,before_state=before,after_state=after,
                history_before=history_before,history_after=copy.deepcopy(ep.history),before_tick=before['tick'],after_tick=after['tick']))
            save(folder/'decisions.json',rows);keyframe(world,folder/'frames')
            print(record['id'],index+1,prediction['choice'],prediction['parse_error'],result['feedback'],world.tick,flush=True)
        scored=terminal_score(ep,world);final=copy.deepcopy(world.state());history_before=copy.deepcopy(ep.history)
        try:ep.act('yield');raise AssertionError('终止后动作未被拒绝')
        except RuntimeError:pass
        s=dict(record_id=record['id'],view=record['view'],case=case,initial_state=initial,final_state=final,common_start_tick=world.common_start_tick,end_tick=world.tick,
            termination_reason=ep.termination_reason,declaration=ep.declaration,terminal_score=scored,after_terminal_rejected_no_mutation=final==world.state() and history_before==ep.history,
            cost=copy.deepcopy(ep.cost),executions=copy.deepcopy(ep.executions),robot_intervals=copy.deepcopy(ep.robot_intervals),delivery_start_tick=world.delivery_start_tick,delivery_event=copy.deepcopy(world.delivery_event),
            public_final_history=copy.deepcopy(ep.history),availability_events=copy.deepcopy(ep.availability_events),legacy_left_only_goal_first_ticks=copy.deepcopy(world.goal_first_ticks),
            expected_blue_carrier_support_online=copy.deepcopy(world.support_audit),robot_partner_online=copy.deepcopy(world.contact_audit),other_objects_partner_online=copy.deepcopy(world.object_partner_audit),non_target_robot_online=copy.deepcopy(world.non_target_robot_audit),
            body_ids=dict(robot=world.robot,partner=world.partner,objects=dict(world.objects)),closed_activity_makespan_ticks=world.tick-world.common_start_tick,
            closed_activity_makespan_seconds=(world.tick-world.common_start_tick)*DT,makespan_includes_final_skill_parking=True,wall_seconds=time.monotonic()-start,model_wall_seconds=sum(r['prediction']['seconds'] for r in rows))
        save(folder/'summary.json',s)
    except Exception:
        save(folder/'infrastructure_failure.json',dict(record=record,completed_decisions=len(rows),traceback=traceback.format_exc(),state=world.state(),history=ep.history))
        raise
    finally:world.close()
    s['canonical_full_trace']=trace_digest(folder/'ticks.jsonl.gz');save(folder/'summary.json',s);return s

def run():
    from experiments.sustained_model_v19.backend import Backend
    f=json.loads(FREEZE.read_text());assert f['source_sha256']==hashes() and f['assets_sha256']==asset_hashes() and f['physics_packages']==versions()
    assert f['packages']=={n:importlib.metadata.version(n) for n in f['packages']}
    out=RESULT/'raw';assert not (out/'identification_calls.json').exists() and not (out/'episodes').exists(),'禁止覆盖或重跑'
    pf=preflight(f);backend=Backend(f);save(out/'loaded_metadata.json',backend.metadata());identified=[]
    for record in f['identification']:
        prediction=backend.generate(record['messages'],record['seed']);assert prediction['input_ids']==record['input_ids']
        identified.append(dict(record=record,prediction=prediction,correct=prediction['choice']==record['expected']))
        save(out/'identification_calls.json',identified);print('识别',len(identified),record['id'],prediction['choice'],identified[-1]['correct'],flush=True)
    summaries=[]
    for record in f['episodes']:
        summary=rollout(record,backend);summaries.append(summary);save(out/'episode_summaries.json',summaries)
    groups={v:dict(total=12,goal_compliant=sum(s['terminal_score']['goal_compliant'] for s in summaries if s['view']==v),termination_reasons={r:sum(s['termination_reason']==r for s in summaries if s['view']==v) for r in ('declared_done','budget_exhausted','physical_failure','wait_timeout')}) for v in ('full_history','public_ledger_aid')}
    result=dict(identification_correct=sum(r['correct'] for r in identified),identification_total=12,groups=groups,metadata=backend.metadata(),preflight=pf,freeze_sha256=sha(FREEZE),source_sha256=hashes())
    save(RESULT/'model_summary.json',result);print('完成',result,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('freeze','run'));a=p.parse_args();freeze() if a.stage=='freeze' else run()
