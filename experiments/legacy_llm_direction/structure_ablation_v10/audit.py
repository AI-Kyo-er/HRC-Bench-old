"""执行后只读复算：规范来源、字段干预、单次预测及v9重复锚点。"""
import json
from collections import Counter

from experiments.physical.run import ROOT,save,sha
from experiments.physical.protocol import parse
from experiments.structure_ablation_v10.run import RESULT,FREEZE,INPUTS,source_hashes
from experiments.structure_ablation_v10.dataset import build_records,subset_aid
from experiments.structure_ablation_v10.scoring import score
from experiments.structure_ablation_v10.analysis import summarize
from experiments.structure_diagnostic_v9.dataset import public_aid


def summary_matches(saved,recomputed,frozen):
    # runner保留全部派生指标，但用冻结解释字段覆盖analysis简述；二者分别核验。
    return all(saved[k]==v for k,v in recomputed.items() if k!='interpretation') and saved['interpretation']==frozen['interpretation']


def main():
    frozen=json.loads(FREEZE.read_text());inputs=json.loads(INPUTS.read_text())
    assert frozen['source_sha256']==source_hashes() and frozen['frozen_inputs_sha256']==sha(INPUTS)
    expected,sources=build_records();assert sources==frozen['source_files_sha256']
    assert all(sha(ROOT/n)==h for n,h in sources.items())
    assert len(inputs)==len(expected)==160
    assert all({k:v for k,v in r.items() if k!='frozen_input_tokens'}==e for r,e in zip(inputs,expected))
    input_checks=[]
    for r in inputs:
        raw=next(v for v in inputs if v['source_v9_id']==r['source_v9_id'] and v['arm']=='raw_full')
        original=json.loads(raw['messages'][1]['content']);obs=json.loads(r['messages'][1]['content'])
        added=obs.pop('external_public_scope_aid',None)
        exact=obs==original and r['messages'][0]==raw['messages'][0]
        expected_aid=None if r['arm']=='raw_full' else (public_aid(original) if r['arm']=='v9_full_aid' else subset_aid(original,r['arm']))
        input_checks.append(dict(id=r['id'],unchanged_original_fields=exact,added_fields_exact=added==expected_aid))
    calls_path=RESULT/'raw/model/calls.json';calls=json.loads(calls_path.read_text());assert len(calls)==160
    call_checks=[]
    for r,row in zip(inputs,calls):
        choice,error=parse(row['prediction']['response'],r['menu'])
        rescored=score(choice,error,json.loads(r['messages'][1]['content']),r['reference_action'])
        call_checks.append(dict(id=r['id'],input_exact=row['record']==r,
            token_exact=row['prediction']['input_tokens']==r['frozen_input_tokens'],
            parse_exact=choice==row['choice'] and error==row['parse_error'],score_exact=rescored==row['score'],
            truncation_exact=row['truncated']==row['prediction']['generation_hit_limit'],
            no_physical_success=row['score']['physical_execution'] is False and row['score']['physical_success'] is None))
    recomputed=summarize(calls);saved=json.loads((RESULT/'summary.json').read_text())
    summary_exact=summary_matches(saved,recomputed,frozen)
    v9_calls_path=ROOT/'results/structure_diagnostic_v9/raw/model/calls.json'
    v9_calls=json.loads(v9_calls_path.read_text());anchors=[]
    for row in calls:
        r=row['record']
        if r['arm'] not in ('raw_full','v9_full_aid'):continue
        view='full_history' if r['arm']=='raw_full' else 'public_scope_aid'
        old=next(o for o in v9_calls if o['record']['source_case_id']==r['source_case_id'] and o['record']['stage']==r['stage'] and o['record']['view']==view)
        anchors.append(dict(id=r['id'],stage=r['stage'],arm=r['arm'],messages_exact=r['messages']==old['record']['messages'],
            previous_choice=old['choice'],current_choice=row['choice'],choice_equal=old['choice']==row['choice'],
            response_equal=old['prediction']['response']==row['prediction']['response'],
            token_equal=old['prediction']['input_tokens']==row['prediction']['input_tokens'],
            progress_equal=old['score']['protocol_progress']==row['score']['protocol_progress']))
    anchor_summary={arm:dict(total=len(group),same_choice=sum(r['choice_equal'] for r in group),same_response=sum(r['response_equal'] for r in group),
        same_progress=sum(r['progress_equal'] for r in group)) for arm in ('raw_full','v9_full_aid')
        for group in ([r for r in anchors if r['arm']==arm],)}
    arm_comparisons=[]
    for left,right in (('S','source_only'),('GP','SGP')):
        for row in [c for c in calls if c['record']['arm']==left]:
            r=row['record'];other=next(c for c in calls if c['record']['source_v9_id']==r['source_v9_id'] and c['record']['arm']==right)
            arm_comparisons.append(dict(source_v9_id=r['source_v9_id'],stage=r['stage'],seed=r['seed'],outer_blue=r['outer_blue'],reverse_menu=r['reverse_menu'],
                arms=[left,right],choices=[row['choice'],other['choice']],scores=[row['score'],other['score']],
                responses=[row['prediction']['response'],other['prediction']['response']],
                same_choice=row['choice']==other['choice'],same_score=row['score']==other['score'],same_response=row['prediction']['response']==other['prediction']['response']))
    comparison_summary={f'd{stage:02d}_{left}_vs_{right}':dict(total=len(group),same_choice=sum(r['same_choice'] for r in group),
        same_score=sum(r['same_score'] for r in group),same_response=sum(r['same_response'] for r in group))
        for stage in (4,5) for left,right in (('S','source_only'),('GP','SGP'))
        for group in ([r for r in arm_comparisons if r['stage']==stage and r['arms']==[left,right]],)}
    failures=[row for row in calls if not row['score']['protocol_progress']]
    failed_path=RESULT/'raw/nonprogress_calls.json';save(failed_path,failures)
    save(RESULT/'failure_audit.json',dict(total_nonprogress=len(failures),by_stage_arm=dict(Counter(f"d{r['record']['stage']:02d}_{r['record']['arm']}" for r in failures)),
        errors=dict(Counter(e for r in failures for e in r['score']['errors'])),
        original_messages_outputs_path=str(failed_path.relative_to(ROOT)),original_messages_outputs_sha256=sha(failed_path),
        no_physical_execution=True,
        explanation='重复finish表示已结束scope后未推进；非blue放置尝试不能称方向错误或忘目标。所有非推进输出完整保存，包括合法no-op。'))
    report=dict(all_passed=all(all(v for k,v in r.items() if k!='id') for r in input_checks+call_checks) and summary_exact and
        len(anchors)==32 and all(r['messages_exact'] and r['token_equal'] for r in anchors),
        original_source_checkpoints=16,input_records=160,actual_calls=160,input_checks=input_checks,call_checks=call_checks,summary_exact=summary_exact,
        repeated_anchor_checks=anchors,repeated_anchor_summary=anchor_summary,
        paired_arm_comparisons=arm_comparisons,paired_arm_comparison_summary=comparison_summary,
        anchor_consistency_note='输出一致性是实测诊断，不将一致当通过审计的必要条件；无额外调用。',
        freeze_sha256=sha(FREEZE),inputs_sha256=sha(INPUTS),calls_sha256=sha(calls_path),v9_calls_sha256=sha(v9_calls_path),
        source_sha256=source_hashes(),postfreeze_auditor_sha256=sha(ROOT/'experiments/structure_ablation_v10/audit.py'),
        physical_actions_executed=0,no_new_gate=True)
    save(RESULT/'audit.json',report);assert report['all_passed']
    print('160输入/输出审计通过；重复锚点',json.dumps(anchor_summary,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
