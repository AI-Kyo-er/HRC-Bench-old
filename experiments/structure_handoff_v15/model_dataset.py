"""每模型4arm×32；真实handoff及只改预算的counterfactual严格区分。"""
import copy
import json
from experiments.physical.run import ROOT,sha
from experiments.structure_v11.protocol import SYSTEM as OLD_SYSTEM
from experiments.structure_diagnostic_v12.dataset import menu_messages
from experiments.structure_handoff_v15.protocol import reduce_history,SYSTEM
from experiments.structure_handoff_v15.reference_run import RESULT,FREEZE as REF_FREEZE

REMINDER='已终止后重复finish_guidance无效。'
OLD_RULE=next(line for line in OLD_SYSTEM.splitlines() if line.startswith('stage_blue_neutral执行'))
ARMS=('old_anchor','manual_reminder','handoff_budget9','handoff_counterfactual8')


def reminder_messages(messages):
    result=copy.deepcopy(messages);assert result[0]['content']==OLD_SYSTEM
    assert OLD_SYSTEM.count(OLD_RULE)==1 and REMINDER in SYSTEM
    result[0]['content']=OLD_SYSTEM.replace(OLD_RULE,OLD_RULE+REMINDER,1)
    return result


def budget8_messages(messages):
    result=copy.deepcopy(messages);text=result[1]['content'];old='"remaining_decisions": 9'
    assert text.count(old)==1
    result[1]['content']=text.replace(old,'"remaining_decisions": 8',1)
    return result


def build_records():
    audit=RESULT/'reference_audit.json';assert json.loads(audit.read_text())['all_passed']
    old_path=ROOT/'results/state_readout_v13/raw/frozen_inputs.json';source_old=json.loads(old_path.read_text())
    selected=[r for r in source_old if r['query']=='action_replay' and r['stage']==5];assert len(selected)==32
    sources={str(p.relative_to(ROOT)):sha(p) for p in (old_path,REF_FREEZE,audit)}
    new=[]
    for c in json.loads(REF_FREEZE.read_text())['cases']:
        path=RESULT/'raw/reference'/c['id']/'decisions.json';rows=json.loads(path.read_text());assert len(rows)==4;sources[str(path.relative_to(ROOT))]=sha(path)
        row=rows[3];obs=json.loads(row['messages'][1]['content']);state=reduce_history(obs['history'])
        assert obs['remaining_decisions']==9 and not state['active'] and state['ended']
        initial=next(e['goals']['blue'] for e in obs['history'] if e['kind']=='accepted_outer')
        reply=next(e['decision'] for e in obs['history'] if e['kind']=='proposal_reply')
        for reverse in (False,True):
            messages=menu_messages(row['messages'],reverse)
            new.append(dict(source_case_id=c['id'],source_id=c['id']+'__'+('reverse' if reverse else 'normal'),source_path=str(path.relative_to(ROOT)),
                source_row_index=3,seed=c['seed'],timing=c['timing'],acceptance='accepted' if reply=='accept' else 'rejected',
                initial_blue=initial,effective_blue=state['outer']['blue'],reverse_menu=reverse,messages=messages,reference_action=row['result']['choice']))
    records=[]
    for model in ('qwen2_5_14b','qwen3_vl_8b'):
        for arm in ARMS:
            for source in (selected if arm in ('old_anchor','manual_reminder') else new):
                if arm in ('old_anchor','manual_reminder'):
                    r={k:copy.deepcopy(source[k]) for k in ('source_case_id','seed','timing','acceptance','initial_blue','effective_blue','reverse_menu','reference_action')}
                    r.update(source_id=source['id'],messages=copy.deepcopy(source['messages']))
                    if arm=='manual_reminder':r['messages']=reminder_messages(r['messages'])
                else:
                    r=copy.deepcopy(source)
                    if arm=='handoff_counterfactual8':r['messages']=budget8_messages(r['messages'])
                r.update(id=f'{model}__{arm}__{r["source_id"]}',model=model,arm=arm,query='action',
                    menu=json.loads(r['messages'][1]['content'])['candidates'],physical_execution=False,
                    counterfactual_budget_only=arm=='handoff_counterfactual8')
                records.append(r)
    assert len(records)==256
    return records,sources
