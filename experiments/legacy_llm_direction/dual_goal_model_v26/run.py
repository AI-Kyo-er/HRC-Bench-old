"""先CPU冻结→独立非任务容量探针→经验收后80完整闭环；无重试。"""
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
from experiments.dual_goal_v25.run import SOURCES as PARENT_SOURCES,requirement
from experiments.dual_goal_v25.protocol import terminal_score,CONFIG,SYSTEM,candidates
from experiments.sustained_combination_v23.world import CombinationWorld
from experiments.transport_cycle_v22.canonical import digest,content_equal
from experiments.structure_v5.run import keyframe
from experiments.dual_goal_model_v26.inputs import Episode,messages,records,source_record,public_ledger,OLD_NOTE,NEW_NOTE
from experiments.dual_goal_model_v26.backend import FLAGS
from experiments.reasoning_baseline_v17.adapter import PARAMETERS

RESULT=ROOT/'results/dual_goal_model_v26';FREEZE=ROOT/'experiments/dual_goal_model_v26/freeze.json'
SOURCES=sorted(set(PARENT_SOURCES+['experiments/dual_goal_model_v26/'+n for n in ('inputs.py','backend.py','run.py')]+[
    'experiments/reasoning_baseline_v17/adapter.py','experiments/sustained_model_v19/inputs.py','experiments/sustained_activity_v18/protocol.py','experiments/physical/protocol.py','tests/test_dual_goal_model_v26.py']))


def hashes():return {p:sha(ROOT/p) for p in SOURCES}


def capacity_probe(tokenizer):
    system='这是非任务显存容量探针。生成连续文本，直到输出预算结束；没有机器人、物品目标或候选操作，不评价回复内容。'
    prefix='下列重复文本仅用于填满输入预算，请继续生成普通文本。\n'
    def build(n):return [dict(role='system',content=system),dict(role='user',content=prefix+' hello'*n)]
    template=lambda m:tokenizer.apply_chat_template(m,tokenize=True,add_generation_prompt=True,enable_thinking=True)
    n=24576-len(template(build(0)))
    for _ in range(4):
        m=build(n);ids=template(m)
        if len(ids)==24576:break
        n+=24576-len(ids)
    assert len(ids)==24576 and all(t not in tokenizer.all_special_ids for t in tokenizer.encode(' hello',add_special_tokens=False))
    return dict(messages=m,input_ids=ids,input_tokens=len(ids),seed=2699000,max_new_tokens=8192,min_new_tokens=8192,
        filler_repetitions=n,flags=FLAGS,purpose='仅非任务最大正式输入/输出预算路径；无World、无动作解析/能力评分。最后输出token通常不再forward，32768 KV仅保守上界，不冒称缓存精确实测。')


def freeze():
    from transformers import AutoTokenizer
    assert not FREEZE.exists(),'冻结不能覆盖'
    predecessor=ROOT/'results/dual_goal_v25';proof={}
    for stage,count in (('control',8),('reference',32),('local',8)):
        a=json.loads((predecessor/f'{stage}_audit_dev0.json').read_text());assert a['passed']==a['physically_safe']==count
        proof[stage]=sha(predecessor/f'{stage}_audit_dev0.json')
    final=json.loads((predecessor/'final_summary.json').read_text());assert final['strict_passed']==48 and final['task_success']==46 and all(final['checks'].values())
    receipt=json.loads((predecessor/'execution_receipt.json').read_text());assert not any(receipt['pid_probes'].values())
    old=json.loads((ROOT/'experiments/reasoning_baseline_v17/cases/freeze_v1.json').read_text());spec=old['model_spec']
    download=json.loads((ROOT/'results/reasoning_baseline_v17/download_receipt.json').read_text());assert download['all_weights_match_official'] and download['revision']==spec['revision']
    t=AutoTokenizer.from_pretrained(spec['path'],local_files_only=True);entries=[]
    for record in records():
        r=dict(record,**source_record(ROOT,record));r['initial_input_ids']=t.apply_chat_template(r['initial_messages'],tokenize=True,add_generation_prompt=True,enable_thinking=True)
        r['source_file_sha256']=sha(ROOT/r['source_path']);assert len(r['initial_input_ids'])<=24576;entries.append(r)
    probe=capacity_probe(t);config=spec['config'];assert 32768<=config['max_position_embeddings'] and t.encode('</think>',add_special_tokens=False)==[151668]
    kv=2*config['num_hidden_layers']*config['num_key_value_heads']*config['head_dim']*2*32768
    estimate=dict(input_upper_bound_tokens=24576,output_tokens=8192,total_context_bound=32768,model_max_position_embeddings=config['max_position_embeddings'],
        frozen_input_max_tokens=max(len(r['initial_input_ids']) for r in entries),weight_bytes=spec['total_weights_bytes'],kv_bytes=kv,
        workspace_planning_bytes=3*1024**3,planning_required_mib=math.ceil((spec['total_weights_bytes']+kv+3*1024**3)/1024**2),
        required_free_mib=45000,minimum_measured_margin_mib=2048,basis='BF16 batch1 KV5GiB；纸面3GiB非保证；45000MiB启动，实测peakreserved+2048<=初始free及探针结束free>=2048。')
    save(FREEZE,dict(version='dual-goal-model-v26.0',source_sha256=hashes(),assets_sha256=asset_hashes(),physics_packages=versions(),
        packages={n:importlib.metadata.version(n) for n in ('torch','transformers','tokenizers','huggingface-hub','accelerate')},model_spec=spec,
        model_verification_receipt_sha256=sha(ROOT/'results/reasoning_baseline_v17/download_receipt.json'),predecessor_proof=proof,predecessor_final_sha256=sha(predecessor/'final_summary.json'),predecessor_receipt_sha256=sha(predecessor/'execution_receipt.json'),
        episodes=entries,capacity_probe=probe,system=SYSTEM,candidates=candidates(),workspace_note_exact_diff=dict(old=OLD_NOTE,new=NEW_NOTE),
        memory_estimate=estimate,parameters=PARAMETERS['thinking'],max_new_tokens=8192,generation_flags=FLAGS,dtype='bfloat16',attention='sdpa',
        seed_rule='local270000+100h+d；full260000+100floor(g/2)+d；prefix不消耗d。每Episode及决策独立重设。',
        invalid_rule='沿v19最后think边界及原JSON/candidate parser；None耗一步、0tick，公开未知候选反馈，无fallback重抽。',
        dynamic_input_rule='完整history不截断；初始/局部起点源自25真实记录；后续自主分叉仅实际事件，超24576记input_capacity_failure，不扩预算。'))
    print('CPU冻结',sha(FREEZE),'最大初始',estimate['frozen_input_max_tokens'],'探针',len(probe['input_ids']),'最低free',estimate['required_free_mib'],flush=True)


def frozen():
    f=json.loads(FREEZE.read_text());assert f['source_sha256']==hashes() and f['assets_sha256']==asset_hashes() and f['physics_packages']==versions()
    assert f['packages']=={n:importlib.metadata.version(n) for n in f['packages']};return f


def preflight(f,stage):
    visible=os.environ.get('CUDA_VISIBLE_DEVICES','');assert visible.isdigit()
    query=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
    selected=next(l.split(',') for l in query.splitlines() if int(l.split(',')[0])==int(visible))
    r=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=os.getpid(),physical_gpu=int(visible),query=query,free_mib=int(selected[4]),required_free_mib=f['memory_estimate']['required_free_mib'])
    save(RESULT/'raw'/f'{stage}_gpu_preflight.json',r);assert r['free_mib']>=45000;return r


def probe():
    from experiments.dual_goal_model_v26.backend import Backend
    f=frozen();out=RESULT/'raw/probe';assert not out.exists(),'禁止重复容量探针';out.mkdir(parents=True)
    for p in SOURCES:dest=out/'source'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/p).read_bytes())
    pf=preflight(f,'probe');backend=None
    try:
        backend=Backend(f);save(out/'loaded_metadata.json',backend.metadata());backend.torch.cuda.reset_peak_memory_stats()
        result=backend.generate(f['capacity_probe']['messages'],f['capacity_probe']['seed'],capacity_only=True);save(out/'call.json',result)
        assert result['input_ids']==f['capacity_probe']['input_ids'] and result['output_tokens']==8192
        meta=backend.metadata();query=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.free','--format=csv,noheader,nounits'],text=True)
        free=int(next(l.split(',')[1] for l in query.splitlines() if int(l.split(',')[0])==pf['physical_gpu']))
        peak=meta['peak_reserved_bytes']/1024**2;margin=pf['free_mib']-peak
        checks=dict(input_exact=result['input_tokens']==24576,decode_budget=result['output_tokens']==8192,peak_margin=margin>=2048,free_after_probe=free>=2048)
        save(RESULT/'capacity_probe_receipt.json',dict(passed=all(checks.values()),checks=checks,preflight=pf,metadata=meta,peak_reserved_mib=peak,margin_to_initial_free_mib=margin,
            free_mib_after_probe=free,nvidia_query_after=query,freeze_sha256=sha(FREEZE),call_sha256=sha(out/'call.json'),
            scope='最大输入/输出预算路径覆盖；return_dict=False，不获取缓存精确长度，32768仅保守KV上界。min_new8192仅非任务，正式不带。'))
        assert all(checks.values());print('容量预检通过',checks,meta,flush=True)
    except Exception:
        save(out/'failure.json',dict(traceback=traceback.format_exc(),preflight=pf,metadata=None if backend is None else backend.metadata()));raise


def rollout(record,backend):
    case=record['case'];stage=record['stage'];folder=RESULT/'raw/episodes'/record['id'];folder.mkdir(parents=True)
    world=CombinationWorld(120,trace_path=folder/'ticks.jsonl.gz',service_trace_path=folder/'service_ticks.jsonl.gz')
    ep=Episode(world,case['initial_blue'],requirement(case),case['reply'],case['timing']);initial=copy.deepcopy(world.state());rows=[];calls=[];checkpoint=None;start=time.monotonic()
    def act(choice,phase,prediction=None):
        o=ep.observation();before=copy.deepcopy(world.state());service_before=ep.service.snapshot();m=messages(o,record['view']);known=public_ledger(o['history'])
        result=ep.act(choice);after=copy.deepcopy(world.state())
        rows.append(dict(sequence=len(rows),phase=phase,observation=o,messages=m,choice=choice,prediction=prediction,before_state=before,after_state=after,before_tick=before['tick'],after_tick=after['tick'],
            history_after=copy.deepcopy(ep.history),known_at_start=known,actual_updates_during_skill=[e for e in copy.deepcopy(ep.history) if e['kind'] in ('proposal','proposal_reply') and before['tick']<e['actual_tick']<=after['tick']],
            result=result,service_before=service_before,service_after=ep.service.snapshot(),decision_budget=ep.decision_budget,budget_origin=ep.budget_origin))
        save(folder/'decisions.json',rows);keyframe(world,folder/'frames');return result
    def wait(predicate):
        at=world.tick
        while not predicate():
            assert world.tick-at<6000 and not ep.terminated
            act('yield','prefix')
        assert world.tick-at<=6000
    try:
        keyframe(world,folder/'frames')
        if stage=='local':
            act('request_transport','prefix');act('careful_red_left','prefix');wait(lambda:world.cycle.active is None and world.carrier_facts()['near'] and world.carrier_facts()['payload_stable'])
            act('place_blue_inspection','prefix');act('request_check','prefix');wait(lambda:ep.service.completed)
            act('request_return','prefix');wait(lambda:world.cycle.active is None and world.carrier_facts()['far'])
            checkpoint=dict(state=copy.deepcopy(world.state()),history=copy.deepcopy(ep.history),service=ep.service.snapshot(),cost=copy.deepcopy(ep.cost),row_boundary=len(rows));ep.begin_local()
            checkpoint['messages']=messages(ep.observation(),record['view'])
            assert checkpoint['cost']==record['prefix_cost']
        assert ep.observation()==record['initial_observation'] and messages(ep.observation(),record['view'])==record['initial_messages']
        for d in range(record['decision_budget']):
            if ep.terminated:break
            obs=ep.observation();m=messages(obs,record['view'])
            try:prediction=backend.generate(m,record['seed_base']+d)
            except ValueError as error:
                if 'input_capacity_failure' not in str(error):raise
                save(folder/'input_capacity_failure.json',dict(messages=m,seed=record['seed_base']+d,error=str(error),decision=d));ep.terminated=True;ep.termination_reason='input_capacity_failure';break
            calls.append(prediction);save(folder/'calls.json',calls)
            result=act(prediction['choice'],'model',prediction)
            print(record['id'],d+1,prediction['choice'],prediction['parse_error'],world.tick,result['feedback'],flush=True)
        final=copy.deepcopy(world.state());history=copy.deepcopy(ep.history);cost=copy.deepcopy(ep.cost);service=ep.service.snapshot()
        try:ep.act('yield');raise AssertionError('终态未拒绝')
        except RuntimeError:immutable=content_equal(final,world.state()) and history==ep.history and cost==ep.cost and service==ep.service.snapshot()
        score=terminal_score(ep,final);prefix_cost=None if checkpoint is None else checkpoint['cost'];local_cost=None if prefix_cost is None else {k:cost[k]-prefix_cost[k] for k in cost}
        summary=dict(record_id=record['id'],record=record,case=case,stage=stage,view=record['view'],initial_state=initial,final_state=final,public_history=history,service=service,cost=cost,
            prefix_cost=prefix_cost,local_cost=local_cost,checkpoints={} if checkpoint is None else {'local_start':checkpoint},common_start_tick=world.common_start_tick,end_tick=world.tick,makespan_ticks=world.tick-world.common_start_tick,
            local_makespan_ticks=None if checkpoint is None else world.tick-checkpoint['state']['tick'],score=score,termination_reason=ep.termination_reason,after_terminal_immutable=immutable,
            model_calls=len(calls),parse_failures=sum(p['parse_error'] is not None for p in calls),generation_hit_limit=sum(p['generation_hit_limit'] for p in calls),model_wall_seconds=sum(p['seconds'] for p in calls),wall_seconds=time.monotonic()-start,
            body_ids=dict(robot=world.robot,carrier=world.partner,inspection=world.inspection,inspection_walls=world.inspection_walls,presence=world.presence,objects=world.objects,trays=world.trays))
    except Exception:
        save(folder/'infrastructure_failure.json',dict(record=record,completed_decisions=len(rows),traceback=traceback.format_exc(),state=world.state(),history=ep.history));raise
    finally:world.close()
    summary['canonical_physics']=digest(folder/'ticks.jsonl.gz');save(folder/'summary.json',summary);return summary


def run():
    from experiments.dual_goal_model_v26.backend import Backend
    f=frozen();proof=json.loads((RESULT/'capacity_probe_receipt.json').read_text());assert proof['passed'] and proof['freeze_sha256']==sha(FREEZE)
    assert not (RESULT/'raw/episodes').exists(),'不覆盖/不自动重采样'
    for p in SOURCES:
        dest=RESULT/'raw/run_sources'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/p).read_bytes())
    pf=preflight(f,'run');backend=Backend(f);save(RESULT/'raw/run_loaded_metadata.json',backend.metadata());summaries=[]
    for r in f['episodes']:
        summaries.append(rollout(r,backend));save(RESULT/'episode_summaries.json',summaries)
    save(RESULT/'model_summary.json',dict(total=len(summaries),task_success=sum(s['score']['task_success'] for s in summaries),metadata=backend.metadata(),preflight=pf,freeze_sha256=sha(FREEZE)))
    print('正式80闭环完成',len(summaries),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('freeze','probe','run'));a=p.parse_args();globals()[a.stage]()
