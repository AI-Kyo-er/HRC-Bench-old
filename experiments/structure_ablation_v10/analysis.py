"""只描述输出字段干预，不对两seed做显著性检验或内部机制归因。"""
from collections import Counter
from itertools import combinations

from experiments.structure_diagnostic_v9.analysis import metrics as base_metrics
from experiments.structure_ablation_v10.dataset import ARMS


def metrics(rows):
    result=base_metrics(rows)
    result.update(illegal_choices=sum(r['score']['illegal_choice'] for r in rows),
        duplicate_finish=sum(r['score']['duplicate_finish'] for r in rows),
        blue_placement_attempts=sum(r['score']['blue_placement_attempted'] for r in rows),
        blue_direction_correct=sum(r['score']['blue_direction_correct'] is True for r in rows),
        blue_direction_wrong=sum(r['score']['blue_direction_correct'] is False for r in rows))
    return result


def summarize(rows):
    groups={f'd{stage:02d}_{arm}':metrics([r for r in rows if r['record']['stage']==stage and r['record']['arm']==arm])
        for stage in (4,5) for arm in ARMS}
    detailed={f'd{stage:02d}_{arm}_{target}_{menu}':metrics([r for r in rows if r['record']['stage']==stage and r['record']['arm']==arm and
        r['record']['outer_blue']==target and r['record']['reverse_menu']==(menu=='reverse')])
        for stage in (4,5) for arm in ARMS for target in ('left','right') for menu in ('normal','reverse')}
    pairs=[]
    for arm in ARMS:
        for seed in (60,61):
            for reverse in (False,True):
                pair=[r for r in rows if r['record']['stage']==5 and r['record']['arm']==arm and r['record']['seed']==seed and r['record']['reverse_menu']==reverse]
                count=sum(r['score']['protocol_progress'] for r in pair)
                pairs.append(dict(arm=arm,seed=seed,reverse_menu=reverse,choices=[r['choice'] for r in pair],
                    outcome=('none_correct','one_correct','two_correct')[count]))
    factors={}
    factorial=ARMS[:8]
    for stage in (4,5):
        rates={arm:groups[f'd{stage:02d}_{arm}']['protocol_progress']/8 for arm in factorial}
        main={f:sum(v for a,v in rates.items() if f in a and a!='raw_full')/4-sum(v for a,v in rates.items() if f not in a or a=='raw_full')/4 for f in 'SGP'}
        interactions={}
        def rate(selected):return rates[''.join(f for f in 'SGP' if f in selected) or 'raw_full']
        for pair in combinations('SGP',2):
            other=next(f for f in 'SGP' if f not in pair)
            interactions[''.join(pair)]=sum(rate(set(pair)|rest)-rate({pair[0]}|rest)-rate({pair[1]}|rest)+rate(rest) for rest in (set(),{other}))/2
        triple=rates['SGP']-rates['SG']-rates['SP']-rates['GP']+rates['S']+rates['G']+rates['P']-rates['raw_full']
        factors[f'd{stage:02d}']=dict(cell_rates=rates,main_difference=main,pair_difference_of_differences=interactions,triple_difference=triple,
            source_only_rate=groups[f'd{stage:02d}_source_only']['protocol_progress']/8,
            source_only_minus_raw=(groups[f'd{stage:02d}_source_only']['protocol_progress']-groups[f'd{stage:02d}_raw_full']['protocol_progress'])/8)
    return dict(total=len(rows),by_stage_arm=groups,by_stage_arm_target_menu=detailed,d5_pairs=pairs,
        pair_outcomes=dict(Counter(p['outcome'] for p in pairs)),descriptive_factorial=factors,
        physical_actions_executed=0,no_new_gate=True,
        interpretation='仅公开summary字段干预的描述性结果；raw与非空cell还差source包装/长度，不分离模型内部机制，不做显著性检验。')
