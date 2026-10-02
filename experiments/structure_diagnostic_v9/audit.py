"""冻结/原始输入/追加aid/模型单次输出的独立只读后审计。"""
import copy
import json
from collections import Counter

from experiments.physical.run import ROOT,save,sha
from experiments.physical.protocol import parse
from experiments.structure_diagnostic_v9.dataset import build_records,public_aid
from experiments.structure_diagnostic_v9.scoring import score
from experiments.structure_diagnostic_v9.analysis import summarize
from experiments.structure_diagnostic_v9.run import FREEZE,INPUTS,RESULT,source_hashes


def main():
    frozen=json.loads(FREEZE.read_text());inputs=json.loads(INPUTS.read_text())
    assert frozen['source_sha256']==source_hashes()
    assert frozen['frozen_inputs_sha256']==sha(INPUTS)
    expected,sources=build_records();assert sources==frozen['source_files_sha256']
    original_match=[]
    for r,e in zip(inputs,expected):
        without_tokens={k:v for k,v in r.items() if k!='frozen_input_tokens'}
        original_match.append(without_tokens==e)
    pairs=[]
    for full,aid in zip(inputs[::2],inputs[1::2]):
        f=json.loads(full['messages'][1]['content']);a=json.loads(aid['messages'][1]['content']);summary=a.pop('external_public_scope_aid')
        pairs.append(dict(source_case_id=full['source_case_id'],stage=full['stage'],
            original_source_messages_exact=full['messages']==expected[inputs.index(full)]['messages'],
            system_exact=full['messages'][0]==aid['messages'][0],only_aid_field_added=f==a,
            aid_derived_only_public=summary==public_aid(f)))
    calls=json.loads((RESULT/'raw/model/calls.json').read_text())
    checks=[]
    for r,row in zip(inputs,calls):
        choice,error=parse(row['prediction']['response'],r['menu'])
        rescore=score(choice,error,json.loads(r['messages'][1]['content']),r['reference_action'])
        checks.append(dict(id=r['id'],record_exact=row['record']==r,token_count_exact=row['prediction']['input_tokens']==r['frozen_input_tokens'],
            parse_exact=choice==row['choice'] and error==row['parse_error'],score_exact=rescore==row['score'],
            no_physical_success_claim=row['score']['physical_execution'] is False and row['score']['physical_success'] is None,
            truncation_exact=row['truncated']==row['prediction']['generation_hit_limit']))
    saved=json.loads((RESULT/'summary.json').read_text());recomputed=summarize(calls)
    summary_exact=all(saved[k]==v for k,v in recomputed.items())
    full_d5=[r for r in inputs if r['stage']==5 and r['view']=='full_history']
    restored_pairs=[]
    for seed in (60,61):
        for reverse in (False,True):
            pair=[r for r in full_d5 if r['seed']==seed and r['reverse_menu']==reverse]
            obs=[json.loads(r['messages'][1]['content']) for r in pair]
            nohistory=[{k:v for k,v in o.items() if k!='history'} for o in obs]
            from transformers import AutoTokenizer
            tokenizer=AutoTokenizer.from_pretrained(ROOT/'models/Qwen2.5-14B-Instruct',local_files_only=True)
            tokens=[tokenizer.apply_chat_template(r['messages'],tokenize=True,add_generation_prompt=True) for r in pair]
            difference=[i for i,(a,b) in enumerate(zip(*tokens)) if a!=b]
            restored_pairs.append(dict(seed=seed,reverse_menu=reverse,without_history_input_exact=nohistory[0]==nohistory[1],
                tokens_per_target=[len(t) for t in tokens],token_lengths_equal=len(tokens[0])==len(tokens[1]),token_replacements=len(difference),
                only_one_token_replacement=len(difference)==1))
    report=dict(input_records=len(inputs),actual_model_calls=len(calls),original_source_checkpoints=40,
        all_passed=len(inputs)==len(calls)==80 and all(original_match) and
            all(all(v for k,v in p.items() if k not in ('source_case_id','stage')) for p in pairs) and
            all(all(v for k,v in c.items() if k!='id') for c in checks) and summary_exact and
            all(p['without_history_input_exact'] and p['token_lengths_equal'] and p['only_one_token_replacement'] for p in restored_pairs),
        source_inputs_exact=all(original_match),aid_pairs=pairs,call_checks=checks,summary_exact=summary_exact,restore_pairs=restored_pairs,
        freeze_sha256=sha(FREEZE),inputs_sha256=sha(INPUTS),calls_sha256=sha(RESULT/'raw/model/calls.json'),
        postfreeze_auditor_sha256=sha(ROOT/'experiments/structure_diagnostic_v9/audit.py'),
        physical_actions_executed=0,interpretation='每点原参考历史独立提供；不是模型自主闭环，不改变旧gate或冻结。')
    save(RESULT/'audit.json',report);assert report['all_passed']
    print('v9后审计',len(inputs),len(calls),'all_passed',report['all_passed'],flush=True)


if __name__=='__main__':main()
