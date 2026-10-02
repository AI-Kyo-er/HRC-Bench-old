"""冻结后只读来源/变体/规范输出/评分复算，不更改执行版本或调用模型。"""
import json
from collections import Counter

from experiments.physical.run import ROOT,save,sha
from experiments.physical.protocol import parse
from experiments.structure_diagnostic_v12.run import RESULT,FREEZE,INPUTS,source_hashes
from experiments.structure_diagnostic_v12.dataset import build_records,public_aid
from experiments.structure_diagnostic_v12.scoring import score
from experiments.structure_diagnostic_v12.analysis import summarize
from experiments.structure_v11.protocol import reduce_history


def main():
    frozen=json.loads(FREEZE.read_text());inputs=json.loads(INPUTS.read_text());calls_path=RESULT/'raw/model/calls.json'
    calls=json.loads(calls_path.read_text());expected,sources=build_records()
    assert frozen['source_sha256']==source_hashes() and frozen['frozen_inputs_sha256']==sha(INPUTS)
    assert sources==frozen['source_files_sha256'] and all(sha(ROOT/n)==h for n,h in sources.items())
    assert len(inputs)==len(calls)==len(expected)==128
    input_checks=[]
    for r,e in zip(inputs,expected):
        raw=next(v for v in inputs if v['source_case_id']==r['source_case_id'] and v['stage']==r['stage'] and not v['reverse_menu'] and v['view']=='full_history')
        obs=json.loads(r['messages'][1]['content']);original=json.loads(raw['messages'][1]['content'])
        added=obs.pop('external_public_scope_aid',None);actual_menu=obs.pop('candidates');original_menu=original.pop('candidates')
        input_checks.append(dict(id=r['id'],source_record_exact={k:v for k,v in r.items() if k!='frozen_input_tokens'}==e,
            system_exact=r['messages'][0]==raw['messages'][0],only_menu_and_aid_changed=obs==original,
            candidate_permutation_exact=actual_menu==(list(reversed(original_menu)) if r['reverse_menu'] else original_menu),
            aid_exact=added==(public_aid(original) if r['view']=='public_scope_aid' else None)))
    call_checks=[]
    for r,row in zip(inputs,calls):
        choice,error=parse(row['prediction']['response'],r['menu']);rescored=score(choice,error,json.loads(r['messages'][1]['content']),r['reference_action'])
        call_checks.append(dict(id=r['id'],record_exact=r==row['record'],token_exact=row['prediction']['input_tokens']==r['frozen_input_tokens'],
            parse_exact=choice==row['choice'] and error==row['parse_error'],score_exact=row['score']==rescored,
            truncation_exact=row['truncated']==row['prediction']['generation_hit_limit'],
            no_physical_success=row['score']['physical_execution'] is False and row['score']['physical_success'] is None))
    recomputed=summarize(calls);saved=json.loads((RESULT/'summary.json').read_text())
    summary_exact=all(saved[k]==v for k,v in recomputed.items())
    bad=[r for r in calls if not r['score']['protocol_progress']];path=RESULT/'raw/nonprogress_calls.json';save(path,bad)
    save(RESULT/'failure_audit.json',dict(total_nonprogress=len(bad),
        ids=[r['record']['id'] for r in bad],errors=dict(Counter(e for r in bad for e in r['score']['errors'])),
        by_stage_view_timing=dict(Counter(f"d{r['record']['stage']:02d}_{r['record']['view']}_{r['record']['timing']}" for r in bad)),
        blue_attempts=sum(r['score']['blue_placement_attempted'] for r in bad),wrong_blue_directions=sum(r['score']['blue_direction_correct'] is False for r in bad),
        no_physical_execution=True,canonical_original_messages_outputs_path=str(path.relative_to(ROOT)),canonical_original_messages_outputs_sha256=sha(path),
        note='独立参考输入；不把无blue尝试的重复finish归因为目标记忆错误，不能按旧v9错误归因解释新输入。'))
    pairs=[]
    for p in recomputed['pairs']:
        pair=[next(r for r in calls if r['record']['id']==ident) for ident in p['ids']]
        obs=[json.loads(r['record']['messages'][1]['content']) for r in pair]
        if p['dimension']=='timing':
            public=[{k:v for k,v in o.items() if k!='history'} for o in obs]
            matched=public[0]==public[1]
        else:
            # aid按不同接受/拒绝结果可不同；比较原物理字段和预算/菜单。
            public=[{k:v for k,v in o.items() if k not in ('history','external_public_scope_aid')} for o in obs]
            matched=public[0]==public[1]
        pairs.append(dict(dimension=p['dimension'],group=p['group'],ids=p['ids'],physical_budget_menu_exact=matched,
            input_tokens=[r['prediction']['input_tokens'] for r in pair],choices=p['choices'],scores=[r['score'] for r in pair],
            token_lengths_equal=pair[0]['prediction']['input_tokens']==pair[1]['prediction']['input_tokens']))
    d4_blue=[]
    for row in calls:
        r=row['record']
        if r['stage']!=4 or not row['score']['blue_placement_attempted']:continue
        state=reduce_history(json.loads(r['messages'][1]['content'])['history']);target=row['choice'].rsplit('_',1)[1]
        d4_blue.append(dict(id=r['id'],view=r['view'],timing=r['timing'],acceptance=r['acceptance'],initial_blue=r['initial_blue'],
            effective_outer_blue=state['outer']['blue'],current_blue_goal=state['goals']['blue'],choice=row['choice'],
            matches_outer_but_violates_active_child=target==state['outer']['blue'] and state['active'] and target!=state['goals']['blue'],
            matches_current_goal=target==state['goals']['blue'],physical_execution=False))
    d5_wrong=[]
    for row in calls:
        r=row['record']
        if r['stage']!=5 or row['score']['blue_direction_correct'] is not False:continue
        history=json.loads(r['messages'][1]['content'])['history'];state=reduce_history(history)
        proposal=next(e['destination'] for e in history if e['kind']=='update_proposed')
        decision=next(e['decision'] for e in history if e['kind']=='proposal_reply')
        initial=next(e['goals']['blue'] for e in history if e['kind']=='accepted_outer')
        chosen=row['choice'].rsplit('_',1)[1]
        d5_wrong.append(dict(id=r['id'],view=r['view'],timing=r['timing'],seed=r['seed'],reverse_menu=r['reverse_menu'],
            initial_blue=initial,proposed_blue=proposal,response_decision=decision,effective_blue=state['outer']['blue'],
            choice=row['choice'],chosen_target=chosen,follows_unaccepted_proposal=decision=='reject' and chosen==proposal,
            matches_initial_outer=chosen==initial,physical_execution=False))
    save(RESULT/'direction_error_audit.json',dict(d4_blue_placement_errors=d4_blue,d5_wrong_directions=d5_wrong,
        d5_counts_by_view_reply=dict(Counter(f"{r['view']}_{r['response_decision']}" for r in d5_wrong)),
        d5_unaccepted_proposal_matches=sum(r['follows_unaccepted_proposal'] for r in d5_wrong),
        definitions='D4所有left/right违背活动child的neutral目标；D5按最新有效outer评分。未尝试blue的重复finish不纳入方向错误。',
        calls_sha256=sha(calls_path),postfreeze_auditor_sha256=sha(ROOT/'experiments/structure_diagnostic_v12/audit.py')))
    report=dict(all_passed=all(all(v for k,v in r.items() if k!='id') for r in input_checks+call_checks) and summary_exact and
        all(p['physical_budget_menu_exact'] and p['token_lengths_equal'] for p in pairs),
        input_records=128,source_checkpoints=32,normal_full_exact_count=32,actual_model_calls=128,
        input_checks=input_checks,call_checks=call_checks,pair_checks=pairs,summary_exact=summary_exact,
        blue_direction_definition='冻结score对D4按当前活动child目标neutral、D5按有效outer目标评分；外层匹配不等于D4方向正确或推进。',
        d4_blue_placement_diagnostic=d4_blue,
        d4_outer_match_but_child_violation=sum(r['matches_outer_but_violates_active_child'] for r in d4_blue),
        freeze_sha256=sha(FREEZE),inputs_sha256=sha(INPUTS),calls_sha256=sha(calls_path),runtime_source_sha256=source_hashes(),
        postfreeze_auditor_sha256=sha(ROOT/'experiments/structure_diagnostic_v12/audit.py'),physical_actions_executed=0)
    save(RESULT/'audit.json',report);assert report['all_passed']
    print('v12全128来源/变体/输出/配对审计通过。',flush=True)


if __name__=='__main__':main()
