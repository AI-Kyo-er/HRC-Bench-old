"""事后完整80条件分项与共同成功配对；不挑条件/修改原始分数。"""
import json
from collections import Counter,defaultdict
from pathlib import Path
from experiments.physical.run import save,sha
from experiments.dual_goal_model_v26.run import RESULT,FREEZE

PHYSICAL=('all_forbidden_zero','loaded_support_all','non_target_preserved','successful_grasp_places_verified','contact_fields_complete')


def costs_for_summary(summary):
    local=summary['stage']=='local'
    return dict(measured_makespan_ticks=summary['local_makespan_ticks'] if local else summary['makespan_ticks'],
        measured_cost=summary['local_cost'] if local else summary['cost'],total_episode_cost=summary['cost'],
        total_episode_makespan_ticks=summary['makespan_ticks'],prefix_cost=summary['prefix_cost'],
        prefix_makespan_ticks=summary['makespan_ticks']-summary['local_makespan_ticks'] if local else None)


def summary_group(rows):
    successes=[r for r in rows if r['safe_task_success']];failures=[r for r in rows if not r['safe_task_success']]
    def mean_cost(rs):
        if not rs:return None
        return dict(makespan_ticks=sum(r['costs']['measured_makespan_ticks'] for r in rs)/len(rs),
            **{k:sum(r['costs']['measured_cost'][k] for r in rs)/len(rs) for k in ('decisions','physical_attempts','yields','wait_ticks')})
    return dict(total=len(rows),task_success=sum(r['task_success'] for r in rows),physical_contract_ok=sum(r['physical_contract_ok'] for r in rows),
        safe_task_success=len(successes),trace_integrity=sum(r['trace_integrity_passed'] for r in rows),
        success_mean_cost=mean_cost(successes),failure_termination_costs=[dict(id=r['id'],termination_reason=r['termination_reason'],costs=r['costs']) for r in failures],
        parse_failures=sum(r['parse_failures'] for r in rows),generation_hit_limit=sum(r['generation_hit_limit'] for r in rows),
        precondition_rejections=sum(len(r['behavior']['precondition_rejections']) for r in rows),
        all_measured_cost_sums={k:sum(r['costs']['measured_cost'][k] for r in rows) for k in rows[0]['costs']['measured_cost']} if rows else {},
        termination_counts=dict(Counter(r['termination_reason'] for r in rows)),ids=[r['id'] for r in rows])


def pairs(rows,field,values,keys):
    table=defaultdict(dict)
    for r in rows:table[tuple(r[k] for k in keys)][r[field]]=r
    out=[]
    for key,arms in table.items():
        assert set(arms)==set(values)
        a,b=(arms[v] for v in values);ok=[r['safe_task_success'] for r in (a,b)]
        outcome='both' if all(ok) else 'first_only' if ok[0] else 'second_only' if ok[1] else 'neither'
        common=None
        if all(ok):
            ca,cb=a['costs'],b['costs'];common=dict(first=ca,second=cb,
                second_minus_first_makespan_ticks=cb['measured_makespan_ticks']-ca['measured_makespan_ticks'],
                second_minus_first_cost={k:cb['measured_cost'][k]-ca['measured_cost'][k] for k in ca['measured_cost']})
        out.append(dict(key=dict(zip(keys,key)),arms=list(values),ids=[a['id'],b['id']],safe_task_outcome=outcome,
            task_success_only=[a['task_success'],b['task_success']],common_success_costs=common))
    return dict(total=len(out),outcomes=dict(Counter(p['safe_task_outcome'] for p in out)),pairs=out,
        common_success_ids=[p['ids'] for p in out if p['safe_task_outcome']=='both'])


def behavior(rows):
    moves=[];noncurrent=[];rework=[];skill_updates=[];refusals=[];no_ops=[]
    for r in rows:
        ex=r['result'].get('execution',{})
        if r['actual_updates_during_skill']:skill_updates.append(dict(sequence=r['sequence'],phase=r['phase'],choice=r['choice'],updates=r['actual_updates_during_skill'],known_at_start=r['known_at_start']))
        if r['phase']!='model':continue
        if r['result']['no_op']:no_ops.append(dict(sequence=r['sequence'],choice=r['choice'],result=r['result']))
        if not r['result']['valid'] and r['prediction']['parse_error'] is None and not ex.get('physical_attempt'):
            refusals.append(dict(sequence=r['sequence'],choice=r['choice'],before_tick=r['before_tick'],after_tick=r['after_tick'],result=r['result'],kind='当前公开物理/服务前提拒绝，未执行；不是已发生碰撞或任务自动失败。'))
        if not ex.get('physical_attempt'):continue
        choice=r['choice']
        if choice=='reload_blue':item,target='blue','carrier'
        else:_,item,target=choice.split('_')
        move=dict(sequence=r['sequence'],choice=choice,item=item,target=target,actual_success=ex['success'],source_regions=r['observation']['physical_placements'][item])
        moves.append(move)
        if target in ('left','right') and target!=r['known_at_start']['goals'][item]:noncurrent.append(move)
        if target in ('left','right') and any(s in ('left','right') and s!=target for s in move['source_regions']):rework.append(move)
    return dict(model_action_counts=dict(Counter(str(r['choice']) for r in rows if r['phase']=='model')),
        actual_model_grasp_places=moves,attempted_cross_tray_rework=rework,noncurrent_goal_at_action_start=noncurrent,precondition_rejections=refusals,legal_no_ops=no_ops,
        updates_during_skills=skill_updates,interpretation='非当前目标盘暂存不自动违规；执行中发生更新不追溯动作开始时判断。返工是实际盘来源到另一盘的尝试，成功/失败保留。')


def report():
    f=json.loads(FREEZE.read_text());audit=json.loads((RESULT/'model_audit.json').read_text());summaries=json.loads((RESULT/'episode_summaries.json').read_text())
    assert len(summaries)==audit['total']==80
    ai={r['id']:r for r in audit['episodes']};ss={s['record_id']:s for s in summaries};reports=[];failures=[]
    assert set(ai)==set(ss)=={r['id'] for r in f['episodes']}
    for record in f['episodes']:
        s=ss[record['id']];a=ai[record['id']];case=record['case'];folder=RESULT/'raw/episodes'/record['id'];rows=json.loads((folder/'decisions.json').read_text())
        physical=all(a['checks'][k] for k in PHYSICAL);integrity=all(v for k,v in a['checks'].items() if k not in PHYSICAL)
        r=dict(id=record['id'],stage=record['stage'],view=record['view'],expression=case['expression'],timing=case['timing'],
            initial_blue=case['initial_blue'],reply=case['reply'],q=case['q'],direct_green=case['direct_green'],
            actual_public_goals=a['public_goals'],confirmation_pending=a['confirmation_pending'],task_success=a['task_success'],
            physical_contract_ok=physical,trace_integrity_passed=integrity,safe_task_success=a['task_success'] and physical,
            termination_reason=s['termination_reason'],terminal_facts=a['actual_score']['facts'],costs=costs_for_summary(s),
            parse_failures=s['parse_failures'],generation_hit_limit=s['generation_hit_limit'],model_calls=s['model_calls'],model_wall_seconds=s['model_wall_seconds'],
            behavior=behavior(rows),source_paths=dict(summary=str((folder/'summary.json').relative_to(RESULT)),decisions=str((folder/'decisions.json').relative_to(RESULT))),
            source_sha256=dict(summary=sha(folder/'summary.json'),decisions=sha(folder/'decisions.json')))
        reports.append(r)
        if not r['safe_task_success'] or r['parse_failures'] or r['generation_hit_limit']:
            model=[x for x in rows if x['phase']=='model'];selected=[x for x in model if x['prediction']['parse_error'] or x['prediction']['generation_hit_limit'] or x['result'].get('execution',{}).get('physical_attempt') and not x['result']['execution']['success'] or x['choice']=='declare_done' and not r['task_success']]
            failures.append(dict(id=r['id'],termination_reason=r['termination_reason'],task_success=r['task_success'],physical_contract_ok=physical,
                terminal_facts=r['terminal_facts'],wrong_or_early_declaration=r['termination_reason']=='declared_done' and not r['task_success'],
                costs=r['costs'],failed_audit_checks=[k for k,v in a['checks'].items() if not v],source_paths=r['source_paths'],source_sha256=r['source_sha256'],
                calls=[dict(sequence=x['sequence'],choice=x['choice'],before_tick=x['before_tick'],after_tick=x['after_tick'],
                    messages=x['messages'],response=x['prediction']['response'],final_response=x['prediction']['final_response'],parse_error=x['prediction']['parse_error'],
                    generation_hit_limit=x['prediction']['generation_hit_limit'],result=x['result']) for x in selected]))
    full=[r for r in reports if r['stage']=='full'];local=[r for r in reports if r['stage']=='local']
    groups={}
    for stage,rs in (('full',full),('local',local)):
        keys=('view','expression','timing') if stage=='full' else ('view','expression')
        table=defaultdict(list)
        for r in rs:table[tuple(r[k] for k in keys)].append(r)
        groups[stage]=[dict(group=dict(zip(keys,key)),summary=summary_group(v)) for key,v in table.items()]
    paired=dict(full_expression=pairs(full,'expression',('direct','relation'),('view','initial_blue','reply','q','timing')),
        full_timing=pairs(full,'timing',('before_check','after_handoff'),('view','initial_blue','reply','q','expression')),
        full_view=pairs(full,'view',('full_history','public_ledger_aid'),('initial_blue','reply','q','expression','timing')),
        local_expression=pairs(local,'expression',('direct','relation'),('view','initial_blue','direct_green')),
        local_view=pairs(local,'view',('full_history','public_ledger_aid'),('initial_blue','direct_green','expression')))
    result=dict(total=80,overall=summary_group(reports),stages=dict(full=summary_group(full),local=summary_group(local)),groups=groups,pairs=paired,episodes=reports,
        freeze_sha256=sha(FREEZE),model_audit_sha256=sha(RESULT/'model_audit.json'),report_source_sha256=sha(Path(__file__)),
        limitations='全条件无挑选，单模板单seed非独立结构样本；直接目标/账本是额外信息，确认时机改变新近程度/提前工作机会。共同成功才比较完成成本，失败终止耗时分列；推理时物理暂停，不解释真人流畅度。')
    save(RESULT/'final_summary.json',result);save(RESULT/'failure_audit.json',dict(total_episodes=80,episodes=failures,report_source_sha256=sha(Path(__file__))))
    print('80完整报告',result['overall']['task_success'],result['overall']['safe_task_success'],flush=True)


if __name__=='__main__':report()
