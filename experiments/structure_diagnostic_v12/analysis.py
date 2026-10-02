"""全条件阶段/视图分层、timing和回应配对；无独立样本或显著性声明。"""
from collections import Counter
from experiments.structure_diagnostic_v9.analysis import metrics as base_metrics


def metrics(rows):
    result=base_metrics(rows)
    result.update(illegal_choices=sum(r['score']['illegal_choice'] for r in rows),
        duplicate_finish=sum(r['score']['duplicate_finish'] for r in rows),
        blue_placement_attempts=sum(r['score']['blue_placement_attempted'] for r in rows),
        blue_direction_correct=sum(r['score']['blue_direction_correct'] is True for r in rows),
        blue_direction_wrong=sum(r['score']['blue_direction_correct'] is False for r in rows))
    result['help_authorization_errors']=sum(r['score']['help_authorization_error'] for r in rows)
    return result


def summarize(rows):
    keys=('stage','view','timing','acceptance','initial_blue','effective_blue','reverse_menu')
    detailed=[]
    groups=sorted({tuple(r['record'][k] for k in keys) for r in rows})
    for group in groups:
        subset=[r for r in rows if tuple(r['record'][k] for k in keys)==group]
        detailed.append(dict(group=dict(zip(keys,group)),metrics=metrics(subset)))
    stage_view={f'd{stage:02d}_{view}':metrics([r for r in rows if r['record']['stage']==stage and r['record']['view']==view])
        for stage in (4,5) for view in ('full_history','public_scope_aid')}
    pairs=[]
    for dimension in ('timing','acceptance'):
        other=[k for k in ('stage','view','seed','timing','acceptance','initial_blue','reverse_menu') if k!=dimension]
        for group in sorted({tuple(r['record'][k] for k in other) for r in rows}):
            pair=sorted([r for r in rows if tuple(r['record'][k] for k in other)==group],key=lambda r:r['record'][dimension])
            assert len(pair)==2
            count=sum(r['score']['protocol_progress'] for r in pair)
            pairs.append(dict(dimension=dimension,group=dict(zip(other,group)),levels=[r['record'][dimension] for r in pair],
                ids=[r['record']['id'] for r in pair],choices=[r['choice'] for r in pair],effective_blue=[r['record']['effective_blue'] for r in pair],
                progress=[r['score']['protocol_progress'] for r in pair],outcome=('none_correct','one_correct','two_correct')[count]))
    changes=[]
    for full in [r for r in rows if r['record']['view']=='full_history']:
        f=full['record'];aid=next(a for a in rows if a['record']['source_case_id']==f['source_case_id'] and a['record']['stage']==f['stage'] and a['record']['reverse_menu']==f['reverse_menu'] and a['record']['view']=='public_scope_aid')
        changes.append(dict(source_case_id=f['source_case_id'],stage=f['stage'],reverse_menu=f['reverse_menu'],full_choice=full['choice'],aid_choice=aid['choice'],
            outcome=('correct' if full['score']['protocol_progress'] else 'incorrect')+'_to_'+('correct' if aid['score']['protocol_progress'] else 'incorrect')))
    return dict(total=len(rows),by_stage_view=stage_view,by_condition=detailed,pairs=pairs,
        pair_outcomes={dim:dict(Counter(p['outcome'] for p in pairs if p['dimension']==dim)) for dim in ('timing','acceptance')},
        full_to_aid=changes,full_to_aid_outcomes=dict(Counter(c['outcome'] for c in changes)),
        physical_actions_executed=0,no_new_gate=True,
        interpretation_note='独立参考检查点，不是模型闭环；timing位置亦改变新近程度，同seed/模板非独立结构样本，无显著性推断。')
