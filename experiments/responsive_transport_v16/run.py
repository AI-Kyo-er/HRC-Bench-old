"""先冻结并跑十启动控制，再冻结十二真实闭环参考，不覆盖失败。"""
import argparse
import copy
import json
from experiments.physical.run import ROOT,save,sha,versions,asset_hashes
from experiments.structure_v5.run import keyframe
from experiments.structure_v8.audit import audit_trace
from experiments.structure_v8.run import SOURCES as OLD_SOURCES
from experiments.responsive_transport_v16.world import ResponsiveWorld,CONFIG,CONFIG_PATH,BUSY_TICKS
from experiments.responsive_transport_v16.protocol import Episode,cases,reference,SYSTEM,candidates
from experiments.responsive_transport_v16.measure import review
from experiments.responsive_transport_v16.canonical import trace_digest,physics_equal

RESULT=ROOT/'results/responsive_transport_v16'
CONTROL_FREEZE=ROOT/'experiments/responsive_transport_v16/cases/control_freeze_public_status.json'
REFERENCE_FREEZE=ROOT/'experiments/responsive_transport_v16/cases/reference_freeze.json'
SOURCES=OLD_SOURCES+['experiments/responsive_transport_v16/'+n for n in ('world.py','protocol.py','canonical.py','measure.py','run.py')]+['experiments/structure_handoff_v15/reference_audit.py','tests/test_responsive_transport_v16.py']
KINDS=('ready_no_request','ready_accept','busy_reject','busy_retry','ready_duplicate')


def hashes():return {n:sha(ROOT/n) for n in SOURCES}


def control_cases():
    return [dict(id=f'Control_{kind}_{seed}',kind=kind,seed=seed,initial_availability='temporarily_busy' if kind.startswith('busy') else 'ready',window_ticks=5920 if kind=='busy_retry' else 4000)
        for seed in (80,81) for kind in KINDS]


def freeze(stage):
    target=CONTROL_FREEZE if stage=='controls' else REFERENCE_FREEZE
    if target.exists():raise RuntimeError('禁止覆盖冻结。')
    old=json.loads((ROOT/'experiments/structure_v8/cases/reference_freeze.json').read_text())
    assert all(sha(ROOT/n)==v for n,v in old['source_sha256'].items())
    extras={}
    if stage=='reference':
        control=json.loads((RESULT/'control_summary.json').read_text());audit=json.loads((RESULT/'control_audit.json').read_text())
        assert control['all_passed'] and audit['all_passed']
        assert json.loads(CONTROL_FREEZE.read_text())['source_sha256']==hashes()
        extras=dict(control_freeze_sha256=sha(CONTROL_FREEZE),control_summary_sha256=sha(RESULT/'control_summary.json'),control_audit_sha256=sha(RESULT/'control_audit.json'))
    f=dict(version='responsive-transport-v16.1-public-status-four-policies',stage=stage,cases=control_cases() if stage=='controls' else cases(),candidate_count=21,system=SYSTEM,
        source_sha256=hashes(),packages=versions(),assets_sha256=asset_hashes(),config=CONFIG,config_sha256=sha(CONFIG_PATH),busy_ticks=1920,busy_seconds=8,
        control_windows='前3及duplicate4000tick；retry先1920后4000共5920单列。',
        metrics='共同t0到blue释放并最终停车；首次目标满足另列；真实red技能/运输重叠含停留/停车；请求决策零tick，不模拟说话时间。',
        interpretation='伙伴抽象资源状态、脚本接受/拒绝与真实机械贡献，规则闭环/响应成本机制核验，无模型/六结构或组合泛化声称。',**extras)
    save(target,f);print(stage,'冻结',sha(target),flush=True)


def finish_summary(world,ep,folder):
    summary=review(world,ep);save(folder/'summary.json',summary);world.close()
    audit=audit_trace(folder,CONFIG);summary['independent_contact_delivery_audit']=audit
    summary['canonical_full_trace']=trace_digest(folder/'ticks.jsonl.gz');summary['canonical_initial_prefix']=trace_digest(folder/'ticks.jsonl.gz',summary['common_start_tick'])
    return summary


def contact_pass(summary):
    a=summary['independent_contact_delivery_audit']
    return a['safety_pass'] and a['online_match'] and a['event_history_consistent'] and a['missing_distance_or_position_pair_records']==0 and a['same_tick_current_FK_joint_max_y_error_m']<1e-6 and a['all_delivery_facts_match_independent_recomputation'] and a['goal_first_ticks_match'] and a['groups']['non_target_robot']['records']==0 and summary['green_preserved']


def control(case,folder):
    folder.mkdir(parents=True);world=ResponsiveWorld(case['seed'],case['initial_availability'],trace_path=folder/'ticks.jsonl.gz');ep=Episode(world,16);rows=[]
    def action(choice):
        observation=ep.observation();messages=ep.messages();before=world.tick;r=ep.act(choice)
        rows.append(dict(sequence=len(rows),kind='decision',observation=observation,messages=messages,result=r,before_tick=before,after_tick=world.tick))
    def wait(ticks):
        observation=ep.observation();messages=ep.messages();before=world.tick;world.phase='control_wait';world.simulate(ticks);ep.cost['wait_ticks']+=ticks;ep.sync_events()
        rows.append(dict(sequence=len(rows),kind='physical_wait',requested_ticks=ticks,observation=observation,messages=messages,before_tick=before,after_tick=world.tick))
    try:
        if case['kind']!='ready_no_request':action('request_transport')
        if case['kind']=='busy_retry':wait(1920);action('request_transport');wait(4000)
        elif case['kind']=='ready_duplicate':wait(1000);action('request_transport');wait(3000)
        else:wait(4000)
        save(folder/'steps.json',rows);s=finish_summary(world,ep,folder)
    finally:
        if not world.trace or not world.trace.closed:world.close()
    k=case['kind'];should_start=k not in ('ready_no_request','busy_reject');expected=['accepted'] if k=='ready_accept' else (['rejected','accepted'] if k=='busy_retry' else (['accepted','already_started'] if k=='ready_duplicate' else (['rejected'] if k=='busy_reject' else [])))
    replies=[r['result']['request_decision'] for r in rows if r['kind']=='decision']
    s.update(case=case,checks=dict(window_exact=s['end_tick']-s['common_start_tick']==case['window_ticks'],reply_sequence_exact=replies==expected,
        started_only_if_accepted=(s['delivery_start_tick'] is not None)==should_start,delivered_only_if_accepted=(s['delivery_event'] is not None)==should_start,
        no_restart=s['cost']['accepted_requests']==int(should_start),ready_without_auto_start=world.availability()['status']=='ready' and (should_start or s['delivery_start_tick'] is None),
        support_valid=s['independent_contact_delivery_audit']['support_coverage']==1 if should_start else s['independent_contact_delivery_audit']['transport_ticks']==0,
        safety_and_log=contact_pass(s)))
    s['passed']=all(s['checks'].values());save(folder/'summary.json',s);print(case['id'],'pass',s['passed'],'requests',replies,'start',s['delivery_start_tick'],'event',s['delivery_event']['first_tick'] if s['delivery_event'] else None,flush=True)
    return s


def rollout(case,folder):
    folder.mkdir(parents=True);world=ResponsiveWorld(case['seed'],case['initial_availability'],trace_path=folder/'ticks.jsonl.gz');ep=Episode(world,case['step_budget']);rows=[]
    try:
        rendered=case['seed']==80 and case['policy'] in ('availability_greedy','eager','wait_ready')
        if rendered:keyframe(world,folder/'frames')
        for _ in range(case['step_budget']):
            if ep.success():break
            observation=ep.observation();messages=ep.messages();assert json.loads(messages[1]['content'])==observation
            choice=reference(observation,case['policy']);before=world.tick;result=ep.act(choice)
            rows.append(dict(sequence=len(rows),observation=observation,messages=messages,prediction=dict(response=json.dumps({'choice':choice}),policy=case['policy']),result=result,before_tick=before,after_tick=world.tick))
            print(case['id'],len(rows),choice,result['feedback'],flush=True)
            if rendered:keyframe(world,folder/'frames')
        save(folder/'decisions.json',rows);s=finish_summary(world,ep,folder)
    finally:
        if not world.trace or not world.trace.closed:world.close()
    a=s['independent_contact_delivery_audit'];s.update(case=case)
    s['passed']=bool(s['success'] and all(e['success'] for e in s['executions']) and contact_pass(s) and a['support_coverage']==1 and a['event_persists_after_pickup'])
    save(folder/'summary.json',s);return s


def run(stage):
    freeze_path=CONTROL_FREEZE if stage=='controls' else REFERENCE_FREEZE;f=json.loads(freeze_path.read_text())
    assert f['source_sha256']==hashes() and f['packages']==versions() and f['assets_sha256']==asset_hashes()
    output=RESULT/'raw'/stage;output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()):raise RuntimeError('禁止覆盖已开始运行。')
    runner=control if stage=='controls' else rollout;rows=[runner(c,output/c['id']) for c in f['cases']]
    pairs=[]
    for seed in (80,81):
        same=[r for r in rows if r['case']['seed']==seed]
        assert all(physics_equal(r['checkpoint'],same[0]['checkpoint']) for r in same)
        assert len({r['canonical_initial_prefix']['canonical_physical_sha256'] for r in same})==1
        if stage=='controls':
            a=next(r for r in same if r['case']['kind']=='ready_accept');b=next(r for r in same if r['case']['kind']=='ready_duplicate')
            pairs.append(dict(seed=seed,ready_accept_duplicate_full_physical_exact=a['canonical_full_trace']==b['canonical_full_trace']))
        else:
            ready=[r for r in same if r['case']['initial_availability']=='ready' and r['case']['policy'] in ('availability_greedy','eager','wait_ready')];busy=[r for r in same if r['case']['initial_availability']=='temporarily_busy' and r['case']['policy']!='wait_ready']
            pairs.append(dict(seed=seed,ready_greedy_eager_wait_ready_full_physical_exact=all(r['canonical_full_trace']==ready[0]['canonical_full_trace'] for r in ready),busy_greedy_serial_eager_full_physical_exact=len({r['canonical_full_trace']['canonical_physical_sha256'] for r in busy})==1))
    summary=dict(stage=stage,total=len(rows),passed=sum(r['passed'] for r in rows),all_passed=all(r['passed'] for r in rows) and all(all(v for k,v in p.items() if k!='seed') for p in pairs),
        success=sum(r['success'] for r in rows),total_ticks=sum(r['independent_contact_delivery_audit']['total_ticks'] for r in rows),pairs=pairs,
        episodes=[dict(id=r['case']['id'],passed=r['passed'],closed_makespan_ticks=r['closed_task_makespan_ticks'],delivery_start_tick=r['delivery_start_tick'],delivery_event_tick=r['delivery_event']['first_tick'] if r['delivery_event'] else None,
            overlap_ticks=r['red_skill_transport_overlap_ticks'],cost=r['cost'],availability_events=r['availability_events']) for r in rows],
        freeze_sha256=sha(freeze_path),source_sha256=hashes())
    save(RESULT/('control_summary.json' if stage=='controls' else 'reference_summary.json'),summary)
    print(stage,'汇总',summary['passed'],'/',summary['total'],'ticks',summary['total_ticks'],flush=True);assert summary['all_passed']


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('freeze','run'));p.add_argument('stage',choices=('controls','reference'));a=p.parse_args()
    freeze(a.stage) if a.action=='freeze' else run(a.stage)
