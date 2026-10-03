"""执行后的独立配对/事件队列派生；不改冻结运行、评分或物理。"""
import gzip
import json
from pathlib import Path
from experiments.physical.run import save,sha
from experiments.dual_goal_v25.run import RESULT,freeze_path,hashes
from experiments.transport_cycle_v22.canonical import content_equal,equal


def episode_folder(stage,ident):return RESULT/'raw'/'dev0'/stage/ident


def queue_audit(stage,episode):
    folder=episode_folder(stage,episode['id']);summary=json.loads((folder/'summary.json').read_text())
    history=summary['public_history'];public=[e for e in history if e['kind'] in ('proposal','proposal_reply')]
    clean=[{k:v for k,v in e.items() if k not in ('observed_tick','event_sequence')} for e in public]
    first=None;earlier=0;first_completed=None
    with gzip.open(folder/'service_ticks.jsonl.gz','rt') as stream:
        for line in stream:
            row=json.loads(line);tick=row['facts']['tick']
            if row['service']['completed'] and first_completed is None:first_completed=tick
            queued=[e for e in row['events_so_far'] if e['kind'] in ('proposal','proposal_reply')]
            if queued and first is None:first=dict(tick=tick,queued=queued,service=row['service'])
            if queued and first_completed is None:earlier+=1
    if summary['case']['timing']=='after_handoff':
        passed=first is not None and first['tick']==first_completed==public[0]['actual_tick'] and content_equal(first['queued'],clean) and earlier==0
    else:
        first_input=json.loads((folder/'decisions.json').read_text())[0]['observation']['history']
        passed=first is None and all(e in first_input for e in public) and all(e['actual_tick']==summary['common_start_tick'] for e in public)
    return dict(id=episode['id'],passed=passed,first_queue=first,first_actual_service_completed_tick=first_completed,
        public_update=public,queued_before_completed_ticks=earlier,kind='事后只读队列生成核验，补充已冻结audit的时间戳/公开历史核验')


def paired(stage,episodes,field):
    pairs=[];left,right=('direct','relation') if field=='expression' else ('before_check','after_handoff')
    index={tuple(sorted((k,v) for k,v in e['case'].items() if k not in ('id',field))):{} for e in episodes}
    for e in episodes:index[tuple(sorted((k,v) for k,v in e['case'].items() if k not in ('id',field)))][e['case'][field]]=e
    for arms in index.values():
        a,b=arms[left],arms[right];fa,fb=episode_folder(stage,a['id']),episode_folder(stage,b['id'])
        sa,sb=[json.loads((p/'summary.json').read_text()) for p in (fa,fb)]
        ra,rb=[json.loads((p/'decisions.json').read_text()) for p in (fa,fb)]
        checks=dict(full_physics=content_equal(sa['canonical_physics'],sb['canonical_physics']),
            initial_physics=equal(sa['initial_state'],sb['initial_state']),final_physics=equal(sa['final_state'],sb['final_state']),
            actions=[r['choice'] for r in ra]==[r['choice'] for r in rb],
            decision_ticks=[(r['before_tick'],r['after_tick']) for r in ra]==[(r['before_tick'],r['after_tick']) for r in rb],
            cost=content_equal(sa['cost'],sb['cost']),final_public_goals=a['public_goals']==b['public_goals'])
        if stage=='local':
            ca,cb=sa['checkpoints']['local_start'],sb['checkpoints']['local_start']
            checks.update(local_checkpoint=equal(ca['state'],cb['state']),prefix_cost=content_equal(sa['prefix_cost'],sb['prefix_cost']),local_cost=content_equal(sa['local_cost'],sb['local_cost']))
        pairs.append(dict(ids=[a['id'],b['id']],checks=checks,passed=all(checks.values()),canonical_physics=sa['canonical_physics']))
    return pairs


def report():
    audits={s:json.loads((RESULT/f'{s}_audit_dev0.json').read_text()) for s in ('control','reference','local')}
    assert all(a['passed']==a['total'] for a in audits.values())
    assert all(json.loads(freeze_path(s).read_text())['source_sha256']==hashes() for s in audits)
    episodes=[e for a in audits.values() for e in a['episodes']]
    queues=[queue_audit(s,e) for s,a in audits.items() for e in a['episodes']]
    pairs=dict(reference_expression=paired('reference',audits['reference']['episodes'],'expression'),
        reference_timing=paired('reference',audits['reference']['episodes'],'timing'),
        local_expression=paired('local',audits['local']['episodes'],'expression'))
    groups={g:dict(records=sum(e['groups'][g]['records'] for e in episodes),ticks=sum(e['groups'][g]['ticks'] for e in episodes),
        max_normal_force=max(e['groups'][g]['max_normal_force'] for e in episodes)) for g in episodes[0]['groups']}
    support=[v for e in episodes for v in e['leg_support'].values() if v['loaded']]
    costs=[]
    for s,a in audits.items():
        for e in a['episodes']:
            summary=json.loads((episode_folder(s,e['id'])/'summary.json').read_text())
            costs.append(dict(id=e['id'],stage=s,task_success=e['task_success'],makespan_ticks=e['makespan_ticks'],cost=e['cost'],
                prefix_cost=summary['prefix_cost'],local_cost=summary['local_cost'],local_makespan_ticks=summary['local_makespan_ticks']))
    checks=dict(all_stages_strict=all(a['passed']==a['total'] for a in audits.values()),
        all_queue_generation=all(q['passed'] for q in queues),all_pairs_exact=all(p['passed'] for v in pairs.values() for p in v),
        runtime_sources_unchanged=all(json.loads(freeze_path(s).read_text())['source_sha256']==hashes() for s in audits))
    result=dict(total=len(episodes),strict_passed=sum(a['passed'] for a in audits.values()),task_success=sum(a['task_success'] for a in audits.values()),
        physically_safe=sum(a['physically_safe'] for a in audits.values()),total_ticks=sum(a['total_ticks'] for a in audits.values()),
        total_decisions=sum(e['cost']['decisions'] for e in episodes),physical_attempts=sum(e['cost']['physical_attempts'] for e in episodes),
        stages={s:{k:a[k] for k in ('total','passed','task_success','physically_safe','total_ticks','freeze_sha256','audit_source_sha256')} for s,a in audits.items()},
        groups=groups,loaded_motion_ticks=sum(v['ticks'] for v in support),loaded_supported_ticks=sum(v['supported_ticks'] for v in support),
        max_non_target_interval_displacement_m=max(e['max_non_target_interval_displacement_m'] for e in episodes),
        costs=costs,pairs=pairs,queue_generation=queues,checks=checks,report_source_sha256=sha(Path(__file__)),
        limitations='单seed指定公开账本规则参考；直接目标/关系计算帮助不同，时机也改变新近程度与pending持续。局部前缀由参考真实执行，非模型自主。无神经、纯结构因果或泛化主张。')
    save(RESULT/'final_summary.json',result);assert all(checks.values());print('派生配对/队列审计通过',result['total'],result['total_ticks'],flush=True)


if __name__=='__main__':report()
