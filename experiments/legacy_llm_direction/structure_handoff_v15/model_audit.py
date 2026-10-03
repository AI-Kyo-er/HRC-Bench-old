"""冻结后只读输入/输出/四arm配对审计；不改变运行源或评分。"""
import json
from collections import Counter
from experiments.physical.run import ROOT,save,sha
from experiments.structure_handoff_v15.model_dataset import build_records,ARMS,REMINDER
from experiments.structure_handoff_v15.model_run import RESULT,FREEZE,INPUTS,SOURCES,hashes,MODELS
from experiments.structure_handoff_v15.model_scoring import score_record
from experiments.structure_handoff_v15.model_analysis import summarize
from experiments.structure_diagnostic_v12.analysis import metrics


def pair_key(record):
    return tuple(record[k] for k in ('seed','timing','acceptance','initial_blue','reverse_menu'))


def model_audit(name,records):
    folder=RESULT/f'raw/model_{name}';rows=json.loads((folder/'calls.json').read_text());finished=json.loads((folder/'finished.json').read_text())
    expected=[r for r in records if r['model']==name]
    assert len(rows)==128 and finished['calls']==128 and [r['record'] for r in rows]==expected
    scored=[]
    for r in rows:
        obs=json.loads(r['record']['messages'][1]['content'])
        again=score_record(r['record'],r['prediction']['response'])
        check=dict(id=r['record']['id'],score_exact=r['score']==again['score'],choice_exact=r['choice']==again['choice'],parse_exact=r['parse_error']==again['parse_error'],
            actual_tokens_exact=r['prediction']['input_tokens']==r['record']['frozen_input_tokens'],all_22_candidates=len(obs['candidates'])==22,
            not_physical=r['score']['physical_execution'] is False and r['score']['physical_success'] is None)
        scored.append(check);assert all(v for k,v in check.items() if k!='id')
    summary=summarize(rows);assert {k:v for k,v in json.loads((folder/'summary.json').read_text()).items() if k!='model'}==summary
    paired=[]
    for key in sorted({pair_key(r['record']) for r in rows}):
        pair={a:next(r for r in rows if pair_key(r['record'])==key and r['record']['arm']==a) for a in ARMS}
        item=dict(condition=dict(zip(('seed','timing','acceptance','initial_blue','reverse_menu'),key)),
            ids={a:r['record']['id'] for a,r in pair.items()},choices={a:r['choice'] for a,r in pair.items()},
            progress={a:r['score']['protocol_progress'] for a,r in pair.items()},errors={a:r['score']['errors'] for a,r in pair.items()})
        comparisons={}
        for a,b in (('old_anchor','manual_reminder'),('old_anchor','handoff_budget9'),('old_anchor','handoff_counterfactual8'),('manual_reminder','handoff_counterfactual8'),('handoff_budget9','handoff_counterfactual8')):
            x,y=pair[a],pair[b]
            comparisons[a+'__'+b]=dict(response_equal=x['prediction']['response']==y['prediction']['response'],choice_equal=x['choice']==y['choice'],score_equal=x['score']==y['score'],
                transition=('correct' if x['score']['protocol_progress'] else 'incorrect')+'_to_'+('correct' if y['score']['protocol_progress'] else 'incorrect'))
        item['comparisons']=comparisons;paired.append(item)
    comparison_counts={key:dict(total=32,response_equal=sum(p['comparisons'][key]['response_equal'] for p in paired),choice_equal=sum(p['comparisons'][key]['choice_equal'] for p in paired),score_equal=sum(p['comparisons'][key]['score_equal'] for p in paired),
        transitions=dict(Counter(p['comparisons'][key]['transition'] for p in paired))) for key in paired[0]['comparisons']}
    dimensions={d:{str(value):{a:metrics([r for r in rows if r['record']['arm']==a and r['record'][d]==value]) for a in ARMS}
        for value in sorted({r['record'][d] for r in rows})} for d in ('timing','acceptance','initial_blue','effective_blue','reverse_menu','seed')}
    failures=[]
    for r in rows:
        if r['score']['protocol_progress']:continue
        rec=r['record'];obs=json.loads(rec['messages'][1]['content']);history=obs['history']
        proposal=next(e for e in history if e['kind']=='update_proposed')
        # 这里只展示公开提议/回应原文，不使用参考action选择或修复输出。
        failures.append(dict(id=rec['id'],arm=rec['arm'],seed=rec['seed'],timing=rec['timing'],acceptance=rec['acceptance'],initial_blue=rec['initial_blue'],effective_blue=rec['effective_blue'],reverse_menu=rec['reverse_menu'],
            chosen_target=(r['choice'].split('_')[-1] if r['score']['blue_placement_attempted'] else None),matches_initial_outer=(r['choice'].split('_')[-1]==rec['initial_blue'] if r['score']['blue_placement_attempted'] else None),matches_last_proposal=(r['choice'].split('_')[-1]==proposal['destination'] if r['score']['blue_placement_attempted'] else None),proposal_event=proposal,reply_event=next(e for e in history if e['kind']=='proposal_reply'),messages=rec['messages'],response=r['prediction']['response'],choice=r['choice'],parse_error=r['parse_error'],truncated=r['truncated'],score=r['score']))
    summary.update(by_dimension=dimensions,four_arm_pairs=paired,comparison_counts=comparison_counts)
    return summary,dict(model=name,calls=128,per_call_checks=scored,all_passed=True,model_metadata=finished['model']),failures


def main():
    frozen=json.loads(FREEZE.read_text());assert frozen['source_sha256']==hashes(SOURCES)
    assert all(sha(ROOT/n)==v for n,v in frozen['source_inputs_sha256'].items()) and frozen['inputs_sha256']==sha(INPUTS)
    records=json.loads(INPUTS.read_text());rebuilt,_=build_records()
    assert [{k:v for k,v in r.items() if k!='frozen_input_tokens'} for r in records]==rebuilt
    summaries={};audits={};failures={}
    for name in MODELS:summaries[name],audits[name],failures[name]=model_audit(name,records)
    input_stats={}
    for name in MODELS:
        input_stats[name]={}
        for arm in ARMS:
            subset=[r for r in records if r['model']==name and r['arm']==arm]
            tokens=[r['frozen_input_tokens'] for r in subset];characters=[sum(len(m['content']) for m in r['messages']) for r in subset]
            histories=[len(json.loads(r['messages'][1]['content'])['history']) for r in subset]
            budgets=[json.loads(r['messages'][1]['content'])['remaining_decisions'] for r in subset]
            input_stats[name][arm]=dict(n=len(subset),tokens_min=min(tokens),tokens_max=max(tokens),characters_min=min(characters),characters_max=max(characters),history_lengths=sorted(set(histories)),remaining_decisions=sorted(set(budgets)))
    report=dict(input_stats=input_stats,all_passed=all(a['all_passed'] for a in audits.values()),actual_calls=256,original_reference_run_exit=1,reference_postfreeze_audit_passed=True,
        freeze_sha256=sha(FREEZE),inputs_sha256=sha(INPUTS),frozen_sources_unchanged=True,all_256_inputs_exact_rebuilt=True,models=audits,
        postfreeze_audit_source_sha256=sha(ROOT/'experiments/structure_handoff_v15/model_audit.py'),physical_actions_executed_by_models=0)
    save(RESULT/'model_summary.json',summaries);save(RESULT/'model_audit.json',report);save(RESULT/'model_failure_audit.json',failures)
    print('256离线模型输入/评分/四arm配对审计通过；原物理exit1保留。',flush=True)


if __name__=='__main__':main()
