"""D4/D5全部真实来源，十视图仅追加公开归约字段；不筛模型失败。"""
import copy
import json

from experiments.physical.run import ROOT,sha
from experiments.structure_diagnostic_v9.dataset import public_aid

V9_INPUTS=ROOT/'results/structure_diagnostic_v9/raw/frozen_inputs.json'
V9_FREEZE=ROOT/'experiments/structure_diagnostic_v9/cases/freeze.json'
ARMS=('raw_full','S','G','P','SG','SP','GP','SGP','source_only','v9_full_aid')
FIELDS={'S':('scope',),'G':('current_goals_from_public_history',),'P':('done_under_current_goals','remaining_items')}


def subset_aid(observation,arm):
    public=public_aid(observation)
    keys={key for factor in arm if factor in FIELDS for key in FIELDS[factor]}
    return {key:copy.deepcopy(value) for key,value in public.items() if key in keys or key=='source'}


def build_records():
    inputs=json.loads(V9_INPUTS.read_text())
    full=[r for r in inputs if r['stage'] in (4,5) and r['view']=='full_history']
    assert len(full)==16
    records=[]
    for original in full:
        aid=next(r for r in inputs if r['source_case_id']==original['source_case_id'] and r['stage']==original['stage'] and r['view']=='public_scope_aid')
        for arm in ARMS:
            r=copy.deepcopy(original)
            r.pop('frozen_input_tokens')
            r['source_v9_id']=original['id'];r['arm']=arm;r.pop('view')
            r['id']=f"{r['source_case_id']}__d{r['stage']:02d}__{arm}"
            if arm=='v9_full_aid':r['messages']=copy.deepcopy(aid['messages'])
            elif arm!='raw_full':
                observation=json.loads(r['messages'][1]['content'])
                r['messages'][1]['content']=r['messages'][1]['content'][:-1]+', "external_public_scope_aid": '+json.dumps(subset_aid(observation,arm),ensure_ascii=False)+'}'
            records.append(r)
    assert len(records)==160
    sources={str(V9_INPUTS.relative_to(ROOT)):sha(V9_INPUTS),str(V9_FREEZE.relative_to(ROOT)):sha(V9_FREEZE)}
    frozen=json.loads(V9_FREEZE.read_text());sources.update(frozen['source_files_sha256'])
    return records,sources
