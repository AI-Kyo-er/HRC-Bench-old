"""4arm推进、锚点与预算/提醒配对；意图评分不冒充物理成功。"""
import json
from collections import Counter
from experiments.physical.run import ROOT
from experiments.structure_diagnostic_v12.analysis import metrics
from experiments.structure_handoff_v15.model_dataset import ARMS


def summarize(rows):
    arms={arm:metrics([r for r in rows if r['record']['arm']==arm]) for arm in ARMS}
    keys=('arm','timing','acceptance','initial_blue','reverse_menu')
    groups=sorted({tuple(r['record'][k] for k in keys) for r in rows});detailed=[]
    for g in groups:detailed.append(dict(group=dict(zip(keys,g)),metrics=metrics([r for r in rows if tuple(r['record'][k] for k in keys)==g])))
    pairs=[]
    for a,b in (('old_anchor','manual_reminder'),('handoff_budget9','handoff_counterfactual8')):
        left=[r for r in rows if r['record']['arm']==a]
        for x in left:
            y=next(r for r in rows if r['record']['arm']==b and r['record']['source_id']==x['record']['source_id'])
            pairs.append(dict(arms=[a,b],source_id=x['record']['source_id'],choices=[x['choice'],y['choice']],progress=[x['score']['protocol_progress'],y['score']['protocol_progress']],
                response_equal=x['prediction']['response']==y['prediction']['response'],score_equal=x['score']==y['score']))
    old_calls={}
    old_paths={'qwen2_5_14b':ROOT/'results/state_readout_v13/raw/model/calls.json','qwen3_vl_8b':ROOT/'results/state_calibration_v14/raw/model_qwen3_vl_8b/calls.json'}
    anchors=[]
    for x in (r for r in rows if r['record']['arm']=='old_anchor'):
        model=x['record']['model']
        if model not in old_calls:old_calls[model]=json.loads(old_paths[model].read_text())
        previous=next(r for r in old_calls[model] if (r['record']['id'] if model=='qwen2_5_14b' else r['record'].get('source_id'))==x['record']['source_id'])
        anchors.append(dict(source_id=x['record']['source_id'],model=model,messages_exact=x['record']['messages']==previous['record']['messages'],
            previous_response=previous['prediction']['response'],current_response=x['prediction']['response'],response_exact=x['prediction']['response']==previous['prediction']['response'],
            previous_choice=previous['choice'],current_choice=x['choice'],choice_exact=x['choice']==previous['choice'],score_exact=x['score']==previous['score']))
    return dict(total=len(rows),arms=arms,by_condition=detailed,pairs=pairs,anchors=anchors,anchor_counts=dict(total=len(anchors),response_exact=sum(a['response_exact'] for a in anchors),choice_exact=sum(a['choice_exact'] for a in anchors),score_exact=sum(a['score_exact'] for a in anchors)),
        physical_actions_executed=0,no_new_gate=True,interpretation='脚本交还/一般防重复提醒/预算字段的离线接口对照；非闭环、无状态query、非自然人或单因素主体因果。')
