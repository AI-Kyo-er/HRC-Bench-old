"""冻结后澄清：键顺序仅写作合规，不改变JSON状态语义；不新增调用。"""
import copy
import json

from experiments.physical.run import ROOT,save,sha
from experiments.state_readout_v13.run import RESULT
from experiments.state_readout_v13.scoring import FIELDS,unique_object,forbidden_constant,score_state
from experiments.state_readout_v13.dataset import public_truth
from experiments.state_readout_v13.analysis import summarize


def parse_semantic(response):
    try:value=json.loads(response,object_pairs_hook=unique_object,parse_constant=forbidden_constant)
    except (ValueError,TypeError):return None,'invalid_json_or_duplicate_keys',False
    if type(value) is not dict:return None,'object_required',False
    ordered=tuple(value)==FIELDS
    if set(value)!=set(FIELDS):return None,'exact_schema_required',ordered
    if type(value['guidance_active']) is not bool:return None,'boolean_type_required',ordered
    for key,allowed in (('outer_blue_destination',('left','right')),('current_blue_destination',('left','right','neutral'))):
        if type(value[key]) is not str or value[key] not in allowed:return None,f'{key}_enum_required',ordered
    return value,None,ordered


def semantic_rows(calls):
    rows=copy.deepcopy(calls)
    for row in rows:
        if row['record']['query']!='state_readout':continue
        value,error,ordered=parse_semantic(row['prediction']['response'])
        row['frozen_score']=copy.deepcopy(row['score']);row['frozen_parse_error']=row['parse_error']
        row.update(state_value=value,parse_error=error,key_order_compliant=ordered,
            score=score_state(value,error,public_truth(json.loads(row['record']['messages'][1]['content']))))
    return rows


def main():
    calls_path=RESULT/'raw/model/calls.json';calls=json.loads(calls_path.read_text());assert len(calls)==128
    rows=semantic_rows(calls);summary=summarize(rows)
    states=[r for r in rows if r['record']['query']=='state_readout']
    summary.update(key_order_compliant=sum(r['key_order_compliant'] for r in states),
        key_order_difference_changes_score=sum(r['score']!=r['frozen_score'] for r in states),
        original_calls_sha256=sha(calls_path),postfreeze_semantic_source_sha256=sha(ROOT/'experiments/state_readout_v13/semantic.py'),
        scoring_clarification='原评分先冻结，之后收到键顺序不是状态语义的澄清。此处只派生语义评分，key_order_compliant单列，原freeze/calls/summary不改；不强转/修复/重试。')
    save(RESULT/'raw/semantic_rows.json',rows);save(RESULT/'semantic_state_summary.json',summary)
    print('语义评分派生完成；键序合规',summary['key_order_compliant'],'/64，改变分数',summary['key_order_difference_changes_score'],flush=True)


if __name__=='__main__':main()
