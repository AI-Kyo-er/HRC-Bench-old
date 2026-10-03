"""多解推进、参照命中、成对敏感性及动作暴露分开，不设新gate。"""
from collections import Counter


def action_class(choice):
    if choice in ('yield','request_clear','finish_guidance','stage_blue_neutral'):return choice
    if not choice:return 'parse_failure'
    parts=choice.split('_')
    return f'{parts[0]}_{parts[1]}' if len(parts)==3 else 'unknown'


def metrics(rows):
    return dict(total=len(rows),protocol_progress=sum(r['score']['protocol_progress'] for r in rows),
        protocol_admissible=sum(r['score']['protocol_admissible'] for r in rows),legal_no_op=sum(r['score']['legal_no_op'] for r in rows),
        reference_action_hit=sum(r['score']['reference_action_hit'] for r in rows),parse_errors=sum(r['parse_error'] is not None for r in rows),
        truncated=sum(r['truncated'] for r in rows),errors=dict(Counter(e for r in rows for e in r['score']['errors'])),
        actions=dict(Counter(r['choice'] or 'parse_failure' for r in rows)),action_classes=dict(Counter(action_class(r['choice']) for r in rows)))


def summarize(rows):
    by_stage_view={f'd{stage:02d}_{view}':metrics([r for r in rows if r['record']['stage']==stage and r['record']['view']==view])
        for stage in range(1,6) for view in ('full_history','public_scope_aid')}
    detailed={f'd{stage:02d}_{view}_{target}_{menu}':metrics([r for r in rows if r['record']['stage']==stage and
        r['record']['view']==view and r['record']['outer_blue']==target and r['record']['reverse_menu']==(menu=='reverse')])
        for stage in range(1,6) for view in ('full_history','public_scope_aid') for target in ('left','right') for menu in ('normal','reverse')}
    pairs=[]
    for stage in range(1,6):
        for view in ('full_history','public_scope_aid'):
            for seed in (60,61):
                for reverse in (False,True):
                    pair=[r for r in rows if r['record']['stage']==stage and r['record']['view']==view and r['record']['seed']==seed and r['record']['reverse_menu']==reverse]
                    count=sum(r['score']['protocol_progress'] for r in pair)
                    pairs.append(dict(stage=stage,view=view,seed=seed,reverse_menu=reverse,
                        source_ids=[r['record']['id'] for r in pair],choices=[r['choice'] for r in pair],
                        outcome='two_correct' if count==2 else ('one_correct' if count==1 else 'none_correct')))
    changes=[]
    for full in [r for r in rows if r['record']['view']=='full_history']:
        aid=next(r for r in rows if r['record']['source_case_id']==full['record']['source_case_id'] and
            r['record']['stage']==full['record']['stage'] and r['record']['view']=='public_scope_aid')
        a,b=full['score']['protocol_progress'],aid['score']['protocol_progress']
        changes.append(dict(source_case_id=full['record']['source_case_id'],stage=full['record']['stage'],full_choice=full['choice'],aid_choice=aid['choice'],
            outcome=('correct' if a else 'incorrect')+'_to_'+('correct' if b else 'incorrect')))
    return dict(total=len(rows),by_view={view:metrics([r for r in rows if r['record']['view']==view]) for view in ('full_history','public_scope_aid')},
        by_stage_view=by_stage_view,by_stage_view_target_menu=detailed,pairs=pairs,pair_outcomes=dict(Counter(p['outcome'] for p in pairs)),
        full_to_aid=changes,full_to_aid_outcomes=dict(Counter(c['outcome'] for c in changes)),
        physical_actions_executed=0,coverage_note='D1选green也是推进，但不代表stage已掌握；D3提前finish合法，非参考独占；全部独立checkpoint由规则轨迹提供。')
