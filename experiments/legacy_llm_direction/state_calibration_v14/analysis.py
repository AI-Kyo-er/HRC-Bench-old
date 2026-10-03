"""三组基础字段/原v13配对/原v4门槛分开报告，不合并为新gate。"""
from collections import Counter
from experiments.state_readout_v13.analysis import state_metrics,summarize as v13_summary
from experiments.physical.run import ROOT
import json


def summarize(rows):
    controls=[r for r in rows if r['record']['suite']=='control']
    groups=[]
    for model in sorted({r['record']['model'] for r in controls}):
        subset=[r for r in controls if r['record']['model']==model]
        groups.append(dict(model=model,total=state_metrics(subset),by_group={g:state_metrics([r for r in subset if r['record']['group']==g]) for g in ('direct','scope','update')},
            key_order_compliant=sum(r['key_order_compliant'] for r in subset)))
    result=dict(total=len(rows),controls=groups,physics_actions_executed=0,controls_not_new_gate=True)
    v13=[r for r in rows if r['record']['suite']=='v13']
    if v13:
        result['v13']=v13_summary(v13)
        old=json.loads((ROOT/'results/state_readout_v13/raw/semantic_rows.json').read_text())
        pairs=[]
        for r in v13:
            prev=next(x for x in old if x['record']['id']==r['record']['source_id'])
            pairs.append(dict(source_id=r['record']['source_id'],query=r['record']['query'],response_equal=prev['prediction']['response']==r['prediction']['response'],
                previous_score=prev['score'],current_score=r['score']))
        result['v13_cross_model_descriptive_pairs']=pairs
    v4=[r for r in rows if r['record']['suite']=='v4']
    if v4:
        groups={}
        for label,subset in [('single',[r for r in v4 if r['record']['original_suite']=='single'])]+[(v,[r for r in v4 if r['record']['original_suite']=='multi' and r['record']['view']==v]) for v in ('full_history','public_progress_aid')]:
            groups[label]=dict(total=len(subset),acceptable=sum(r['score']['acceptable'] for r in subset),
                errors=dict(Counter(e for r in subset for e in r['score']['errors'])),actions=dict(Counter(r['choice'] for r in subset)))
        result['v4']=dict(groups=groups,old_interface_engineering_gate_passed=groups['single']['acceptable']==16 and groups['full_history']['acceptable']==12,
            note='原40小集工程门槛，仅新模型独立结果，不代表复杂状态/组合能力；不替代旧14B未通过结果。')
    return result
