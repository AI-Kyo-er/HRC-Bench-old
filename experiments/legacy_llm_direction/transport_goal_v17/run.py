"""16个指定命令控制：物理可执行性与声明目标符合性分别评分。"""
import argparse
import json
from experiments.physical.run import ROOT,save,sha,versions,asset_hashes
from experiments.structure_v5.run import keyframe
from experiments.responsive_transport_v16.world import ResponsiveWorld,CONFIG,CONFIG_PATH
from experiments.responsive_transport_v16.measure import review
from experiments.responsive_transport_v16.canonical import physics_equal,trace_digest
from experiments.responsive_transport_v16.run import SOURCES as OLD_SOURCES
from experiments.structure_v8.audit import audit_trace
from experiments.transport_goal_v17.protocol import Episode,SYSTEM,candidates

RESULT=ROOT/'results/transport_goal_v17'
FREEZE=ROOT/'experiments/transport_goal_v17/cases/freeze.json'
SOURCES=OLD_SOURCES+['experiments/transport_goal_v17/'+n for n in ('protocol.py','run.py')]+['tests/test_transport_goal_v17.py']


def cases():
    return [dict(id=f'Control_declared_{declared}_command_{command}_{mode}_{seed}',declared_blue=declared,command_blue=command,mode=mode,seed=seed)
        for seed in (90,91) for declared in ('left','right') for command in ('left','right') for mode in ('direct','careful')]


def hashes():return {n:sha(ROOT/n) for n in SOURCES}


def freeze():
    if FREEZE.exists():raise RuntimeError('禁止覆盖。')
    old=json.loads((ROOT/'experiments/responsive_transport_v16/cases/reference_freeze.json').read_text());assert all(sha(ROOT/n)==v for n,v in old['source_sha256'].items())
    save(FREEZE,dict(version='transport-goal-v17.0',cases=cases(),source_sha256=hashes(),packages=versions(),assets_sha256=asset_hashes(),config=CONFIG,config_sha256=sha(CONFIG_PATH),system=SYSTEM,candidate_count=21,
        sequence=['request_transport','careful_red_left','yield','按预先指定command/mode抓放blue'],termination='固定四动作耗尽，绝不按声明目标提前截断。',
        objective='16物理执行目标，与8符合/8不符合声明目标严格分列，非自主策略成功率。',
        filters_retained=['blue真实交付前提','red目标语义过滤','green不分配','assisted未授权','所选实际区域已达到时不重复','低层实际几何/摩擦失败反馈'],blue_declared_target_gate=False))
    print('控制freeze',sha(FREEZE),flush=True)


def control(case,folder):
    folder.mkdir(parents=True);world=ResponsiveWorld(case['seed'],'ready',trace_path=folder/'ticks.jsonl.gz');ep=Episode(world,case['declared_blue'],8);rows=[]
    commands=['request_transport','careful_red_left','yield',f'{"place" if case["mode"]=="direct" else "careful"}_blue_{case["command_blue"]}']
    try:
        if case['seed']==90:keyframe(world,folder/'frames')
        for choice in commands:
            observation=ep.observation();messages=ep.messages();before=world.tick;result=ep.act(choice)
            rows.append(dict(sequence=len(rows),observation=observation,messages=messages,command=choice,result=result,before_tick=before,after_tick=world.tick))
            print(case['id'],len(rows),choice,result['feedback'],flush=True)
            if case['seed']==90:keyframe(world,folder/'frames')
        s=review(world,ep);s.update(case=case)
        # review的first_goal_satisfaction由继承world的left诊断产生，v17不用于通用评分。
        s['legacy_left_only_goal_first_ticks']=s.pop('goal_first_ticks');s.pop('first_goal_satisfaction_tick');s.pop('first_goal_satisfaction_from_t0_ticks')
        s['physical_command_success']=world.at_goal('red','left') and world.at_goal('blue',case['command_blue']) and all(e['success'] for e in ep.executions)
        s['declared_goal_compliant']=world.at_goal('red','left') and world.at_goal('blue',case['declared_blue'])
        save(folder/'decisions.json',rows);save(folder/'summary.json',s)
    finally:world.close()
    # 旧audit的left-only goal_first_ticks仅作自洽诊断，不作目标符合性的证据。
    legacy=dict(s,goal_first_ticks=s['legacy_left_only_goal_first_ticks']);save(folder/'summary.json',legacy)
    a=audit_trace(folder,CONFIG);s['contact_delivery_audit']=a;s['canonical_full_trace']=trace_digest(folder/'ticks.jsonl.gz');s['canonical_initial_prefix']=trace_digest(folder/'ticks.jsonl.gz',s['common_start_tick'])
    s['passed']=bool(s['physical_command_success'] and s['declared_goal_compliant']==(case['declared_blue']==case['command_blue']) and s['green_preserved'] and a['safety_pass'] and a['groups']['non_target_robot']['records']==0 and a['support_coverage']==1 and a['event_history_consistent'] and a['event_persists_after_pickup'] and a['online_match'] and a['missing_distance_or_position_pair_records']==0 and a['all_delivery_facts_match_independent_recomputation'] and a['same_tick_current_FK_joint_max_y_error_m']<1e-6)
    save(folder/'summary.json',s);return s


def run():
    f=json.loads(FREEZE.read_text());assert f['source_sha256']==hashes() and f['packages']==versions() and f['assets_sha256']==asset_hashes()
    out=RESULT/'raw/controls';out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise RuntimeError('禁止覆盖已有真实控制。')
    rows=[control(c,out/c['id']) for c in f['cases']];pairs=[]
    for seed in (90,91):
        for command in ('left','right'):
            for mode in ('direct','careful'):
                pair=[r for r in rows if r['case']['seed']==seed and r['case']['command_blue']==command and r['case']['mode']==mode]
                pairs.append(dict(seed=seed,command=command,mode=mode,ids=[r['case']['id'] for r in pair],initial_physical_equal=physics_equal(pair[0]['checkpoint'],pair[1]['checkpoint']),full_physical_equal=pair[0]['canonical_full_trace']==pair[1]['canonical_full_trace'],goal_compliance_opposite=pair[0]['declared_goal_compliant']!=pair[1]['declared_goal_compliant']))
    s=dict(total=16,passed=sum(r['passed'] for r in rows),physical_command_success=sum(r['physical_command_success'] for r in rows),declared_goal_compliant=sum(r['declared_goal_compliant'] for r in rows),total_ticks=sum(r['contact_delivery_audit']['total_ticks'] for r in rows),pairs=pairs,
        freeze_sha256=sha(FREEZE),episodes=[dict(id=r['case']['id'],passed=r['passed'],physical_command_success=r['physical_command_success'],declared_goal_compliant=r['declared_goal_compliant'],cost=r['cost'],end_tick=r['end_tick']) for r in rows])
    save(RESULT/'control_summary.json',s);print('控制完成',s['passed'],s['physical_command_success'],s['declared_goal_compliant'],flush=True)
    assert s['passed']==16 and s['physical_command_success']==16 and s['declared_goal_compliant']==8 and all(all(v for k,v in p.items() if k not in ('seed','command','mode','ids')) for p in pairs)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('freeze','run'));a=p.parse_args();freeze() if a.stage=='freeze' else run()
