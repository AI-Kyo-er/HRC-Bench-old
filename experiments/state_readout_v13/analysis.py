"""独立状态报告×同次新action配对，不将状态答案提供给action。"""
from collections import Counter
from experiments.structure_diagnostic_v12.analysis import metrics as action_metrics
from experiments.state_readout_v13.scoring import FIELDS


def state_metrics(rows):
    return dict(total=len(rows),schema_valid=sum(r['score']['schema_valid'] for r in rows),
        field_correct={key:sum(r['score']['field_correct'][key] for r in rows) for key in FIELDS},
        joint_state_correct=sum(r['score']['joint_state_correct'] for r in rows),
        format_errors=dict(Counter(r['parse_error'] for r in rows if r['parse_error'])),truncated=sum(r['truncated'] for r in rows))


def summarize(rows):
    action=[r for r in rows if r['record']['query']=='action_replay'];states=[r for r in rows if r['record']['query']=='state_readout']
    pairs=[]
    for a in action:
        s=next(s for s in states if s['record']['source_v12_id']==a['record']['source_v12_id'])
        ac=a['score']['protocol_progress'];sc=s['score']['joint_state_correct'];r=a['record']
        pairs.append(dict(source_v12_id=r['source_v12_id'],stage=r['stage'],timing=r['timing'],acceptance=r['acceptance'],
            initial_blue=r['initial_blue'],reverse_menu=r['reverse_menu'],action_choice=a['choice'],state_value=s['state_value'],
            state_truth=r['public_state_truth'],state_correct=sc,action_correct=ac,
            outcome=('state_correct' if sc else 'state_incorrect')+'_'+('action_correct' if ac else 'action_incorrect')))
    keys=('stage','timing','acceptance','initial_blue','reverse_menu')
    groups=sorted({tuple(r['record'][key] for key in keys) for r in action});detailed=[]
    for group in groups:
        aa=[r for r in action if tuple(r['record'][key] for key in keys)==group]
        ss=[r for r in states if tuple(r['record'][key] for key in keys)==group]
        detailed.append(dict(group=dict(zip(keys,group)),action=action_metrics(aa),state=state_metrics(ss)))
    return dict(total=len(rows),action=action_metrics(action),state=state_metrics(states),by_condition=detailed,
        by_stage={f'd{stage:02d}':dict(action=action_metrics([r for r in action if r['record']['stage']==stage]),
            state=state_metrics([r for r in states if r['record']['stage']==stage])) for stage in (4,5)},
        paired_results=pairs,pair_outcomes=dict(Counter(p['outcome'] for p in pairs)),physical_actions_executed=0,no_new_gate=True,
        interpretation_note='状态和动作是独立query，状态未送入action；并非内在知识测量/模型闭环/独立结构泛化。')
