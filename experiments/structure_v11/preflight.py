"""冻结前只读匹配设计核验：旧真实checkpoint承载拟议公开事件，不称新rollout。"""
import copy
import json
from collections import Counter

from experiments.physical.run import ROOT,sha
from experiments.structure_v11.protocol import cases,update_events,SYSTEM


def history_design(source_history,case):
    history=copy.deepcopy(source_history)
    for event in history:
        if 'content' in event:event['content']=event['content'].replace('此前外层blue约定','当时有效外层blue约定')
    at=3 if case['timing']=='before_child' else 9
    history[at:at]=update_events(case['proposed_blue'],case['reply'])
    return history


def design_audit():
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(ROOT/'models/Qwen2.5-14B-Instruct',local_files_only=True)
    rows=[];sources={}
    for case in cases():
        path=ROOT/f"results/structure_v7/raw/reference/B_neutral_{case['initial_blue']}_{case['seed']}_normal/decisions.json"
        source=json.loads(path.read_text())[4];sources[str(path.relative_to(ROOT))]=sha(path)
        obs=copy.deepcopy(source['observation']);obs['history']=history_design(obs['history'],case)
        messages=[dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(obs,ensure_ascii=False))]
        rows.append(dict(case=case,history=obs['history'],without_history={k:v for k,v in obs.items() if k!='history'},
            input_tokens=len(tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=True)),
            characters=sum(len(m['content']) for m in messages),remaining_decisions=obs['remaining_decisions']))
    pairs=[]
    for seed in (60,61):
        for reply in ('accepted','rejected'):
            for initial in ('left','right'):
                pair=[r for r in rows if r['case']['seed']==seed and r['case']['reply']==reply and r['case']['initial_blue']==initial]
                unblocked=[[e for e in r['history'] if e['kind'] not in ('update_proposed','proposal_reply')] for r in pair]
                blocks=[[e for e in r['history'] if e['kind'] in ('update_proposed','proposal_reply')] for r in pair]
                checks=dict(nonupdate_history_exact=unblocked[0]==unblocked[1],update_block_exact=blocks[0]==blocks[1],
                    event_multiset_exact=Counter(json.dumps(e,sort_keys=True,ensure_ascii=False) for e in pair[0]['history'])==Counter(json.dumps(e,sort_keys=True,ensure_ascii=False) for e in pair[1]['history']),
                    without_history_exact=pair[0]['without_history']==pair[1]['without_history'],
                    tokens_equal=pair[0]['input_tokens']==pair[1]['input_tokens'],characters_equal=pair[0]['characters']==pair[1]['characters'],
                    both_fifteen_events=all(len(r['history'])==15 for r in pair),both_budget_eight=all(r['remaining_decisions']==8 for r in pair))
                pairs.append(dict(seed=seed,reply=reply,initial_blue=initial,ids=[r['case']['id'] for r in pair],checks=checks,passed=all(checks.values())))
    return dict(all_passed=all(p['passed'] for p in pairs),pairs=pairs,source_files_sha256=sources,
        token_lengths=[dict(id=r['case']['id'],input_tokens=r['input_tokens'],characters=r['characters']) for r in rows],
        scope='旧实际D5观察承载拟议15事件的冻结前设计核验；不是新v11真实输入/轨迹。最终真实输入仍独立审计。')
