"""冻结后逐调用审计；不生成、不执行动作、不改冻结评分。"""
import json
import importlib.metadata
from transformers import AutoTokenizer
from experiments.physical.run import ROOT,save,sha
from experiments.reasoning_baseline_v17.run import RESULT,FREEZE,SOURCE,SPEC,hashes,digest
from experiments.reasoning_baseline_v17.adapter import PARAMETERS,MAX_NEW_TOKENS,score
from experiments.model_scale_v4.run import classify


def audit():
    f=json.loads(FREEZE.read_text());source=json.loads(SOURCE.read_text())['records'];tokenizer=AutoTokenizer.from_pretrained(f['model_spec']['path'],local_files_only=True)
    assert f['source_sha256']==hashes() and f['source_freeze_sha256']==sha(SOURCE) and f['model_spec_sha256']==sha(SPEC)
    reports={};failures=[]
    for mode in PARAMETERS:
        folder=RESULT/'raw'/mode;rows=json.loads((folder/'calls.json').read_text());summary=json.loads((folder/'summary.json').read_text());assert len(rows)==40
        checks=[];groups={}
        for i,row in enumerate(rows):
            r=row['record'];p=row['prediction'];expected=next(x for x in f['records'] if x['mode']==mode and x['case_index']==i)
            judged=score(source[i],p['response'],mode);judged['errors']=classify(source[i],judged['choice'],judged['parse_error'])
            tokens=p['generated_ids'];marker=151668
            # 字符最终边界与官方token最后边界独立交叉验证，不能从reasoning取JSON。
            if mode=='thinking' and marker in tokens:
                boundary=len(tokens)-1-tokens[::-1].index(marker);final=tokenizer.decode(tokens[boundary+1:],skip_special_tokens=True).strip()
                token_boundary_matches=final==judged['final_response']
            else:token_boundary_matches=marker not in tokens if mode=='thinking' else True
            cs=dict(frozen_record_exact=r==expected,original_messages_labels_menu_exact=r['record']==source[i],original_messages_hash=r['messages_sha256']==digest(source[i]['messages']),
                rendered_and_ids_exact=tokenizer.apply_chat_template(source[i]['messages'],tokenize=False,add_generation_prompt=True,enable_thinking=mode=='thinking')==r['rendered_template'] and tokenizer.apply_chat_template(source[i]['messages'],tokenize=True,add_generation_prompt=True,enable_thinking=mode=='thinking')==r['input_ids'],
                raw_decodes_exact=tokenizer.decode(tokens,skip_special_tokens=True)==p['response'] and tokenizer.decode(tokens,skip_special_tokens=False)==p['response_with_special_tokens'],
                final_token_boundary_matches=token_boundary_matches,score_exact=all(row[k]==v for k,v in judged.items()),seed_exact=r['seed']==17000+i,
                token_count_budget=p['input_tokens']==len(r['input_ids']) and p['output_tokens']==len(tokens)<=MAX_NEW_TOKENS)
            checks.append(dict(id=r['id'],checks=cs,passed=all(cs.values())))
            if not row['acceptable']:
                failures.append(dict(id=r['id'],mode=mode,original_id=source[i]['id'],view=source[i]['view'],messages=source[i]['messages'],allowed=source[i]['allowed'],response=p['response'],final_response=row['final_response'],
                    choice=row['choice'],parse_error=row['parse_error'],boundary_error=row['boundary_error'],errors=row['errors'],generation_hit_limit=p['generation_hit_limit'],output_tokens=p['output_tokens']))
        for view in ('single','full_history','public_progress_aid'):
            subset=[r for r in rows if r['record']['record']['view']==view];errors={}
            for row in subset:
                for error in row['errors']:errors[error]=errors.get(error,0)+1
            groups[view]=dict(total=len(subset),acceptable=sum(r['acceptable'] for r in subset),parse_errors=sum(r['parse_error'] is not None for r in subset),truncated=sum(r['prediction']['generation_hit_limit'] for r in subset),errors=errors)
        assert groups==summary['groups'] and summary['gate_passed']==(groups['single']['acceptable']==16 and groups['full_history']['acceptable']==12)
        assert all(r['passed'] for r in checks)
        reports[mode]=dict(total=len(rows),passed=sum(c['passed'] for c in checks),checks=checks,groups=groups,gate_passed=summary['gate_passed'],metadata=summary['metadata'],
            calls_sha256=sha(folder/'calls.json'),summary_sha256=sha(folder/'summary.json'))
    report=dict(total=80,passed=sum(r['passed'] for r in reports.values()),modes=reports,source_freeze_sha256=sha(SOURCE),freeze_sha256=sha(FREEZE),
        frozen_run_source_unchanged=True,audit_source_sha256={'experiments/reasoning_baseline_v17/audit.py':sha(ROOT/'experiments/reasoning_baseline_v17/audit.py')},
        interpretation='固定旧40输入的两模式采样工程门槛；非纯thinking/规模因果，不执行物理，不以aid替代full gate。')
    save(RESULT/'model_audit.json',report);save(RESULT/'failure_audit.json',dict(total=len(failures),failures=failures))
    print('审计80条原输入/原评分/官方最后token边界全部一致',flush=True)

if __name__=='__main__':audit()
