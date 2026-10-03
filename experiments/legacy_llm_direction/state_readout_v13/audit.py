"""原冻结与独立语义报告、64action锚点及旧八错例观察关联的只读审计。"""
import json
from collections import Counter

from experiments.physical.run import ROOT,save,sha
from experiments.physical.protocol import parse
from experiments.state_readout_v13.run import RESULT,FREEZE,INPUTS,source_hashes
from experiments.state_readout_v13.dataset import build_records,public_truth,REPLACEMENTS
from experiments.state_readout_v13.scoring import parse_state,score_state
from experiments.state_readout_v13.analysis import summarize
from experiments.state_readout_v13.semantic import semantic_rows,parse_semantic
from experiments.structure_diagnostic_v12.scoring import score as action_score


def main():
    frozen=json.loads(FREEZE.read_text());inputs=json.loads(INPUTS.read_text());calls_path=RESULT/'raw/model/calls.json'
    calls=json.loads(calls_path.read_text());expected,sources=build_records()
    assert len(inputs)==len(calls)==len(expected)==128
    assert frozen['source_sha256']==source_hashes() and frozen['frozen_inputs_sha256']==sha(INPUTS)
    assert sources==frozen['source_files_sha256'] and all(sha(ROOT/n)==h for n,h in sources.items())
    checks=[]
    for r,row,e in zip(inputs,calls,expected):
        obs=json.loads(r['messages'][1]['content'])
        if r['query']=='action_replay':
            choice,error=parse(row['prediction']['response'],r['menu']);value=None
            rescored=action_score(choice,error,obs,r['reference_action'])
        else:
            choice=None;value,error=parse_state(row['prediction']['response']);rescored=score_state(value,error,public_truth(obs))
        checks.append(dict(id=r['id'],source_exact={k:v for k,v in r.items() if k!='frozen_input_tokens'}==e,
            record_exact=row['record']==r,truth_public=r['public_state_truth']==public_truth(obs),
            token_exact=row['prediction']['input_tokens']==r['frozen_input_tokens'],
            parse_exact=choice==row['choice'] and error==row['parse_error'] and value==row['state_value'],
            score_exact=rescored==row['score'],truncation_exact=row['truncated']==row['prediction']['generation_hit_limit'],
            no_physical_success=row['score']['physical_execution'] is False and row['score']['physical_success'] is None))
    recomputed=summarize(calls);saved=json.loads((RESULT/'summary.json').read_text());frozen_summary_exact=all(saved[k]==v for k,v in recomputed.items())
    sem=semantic_rows(calls);stored_sem=json.loads((RESULT/'raw/semantic_rows.json').read_text());assert sem==stored_sem
    sem_summary=summarize(sem);stored_summary=json.loads((RESULT/'semantic_state_summary.json').read_text());semantic_summary_exact=all(stored_summary[k]==v for k,v in sem_summary.items())
    states=[r for r in sem if r['record']['query']=='state_readout']
    cross=Counter();outer_errors=[]
    for s in states:
        r=s['record'];a=next(a for a in sem if a['record']['query']=='action_replay' and a['record']['source_v12_id']==r['source_v12_id'])
        outer_ok=s['score']['field_correct']['outer_blue_destination'];action_ok=a['score']['protocol_progress']
        cross[('outer_correct' if outer_ok else 'outer_incorrect')+'_'+('action_correct' if action_ok else 'action_incorrect')]+=1
        if not outer_ok:
            outer_errors.append(dict(source_v12_id=r['source_v12_id'],stage=r['stage'],timing=r['timing'],acceptance=r['acceptance'],
                initial_blue=r['initial_blue'],effective_blue=r['effective_blue'],seed=r['seed'],reverse_menu=r['reverse_menu'],
                state_truth=r['public_state_truth'],state_response=s['prediction']['response'],action_choice=a['choice'],action_score=a['score']))
    save(RESULT/'state_field_audit.json',dict(state_queries=64,
        field_output_distributions={key:dict(Counter(json.dumps(s['state_value'][key],ensure_ascii=False) for s in states)) for key in states[0]['record']['public_state_truth']},
        outer_correct_action_cross=dict(cross),joint_state_action_cross=sem_summary['pair_outcomes'],outer_errors=outer_errors,
        frozen_vs_semantic_score_differences=sum(s['score']!=s['frozen_score'] for s in states),
        independent_queries=True,state_answer_not_supplied_to_action=True,
        note='外层目标字段正确不代表联合状态正确；独立报告任务不等价于模型内在知识，字段理解尚未校准成功。'))
    v12_path=ROOT/'results/structure_diagnostic_v12/raw/model/calls.json';old_calls=json.loads(v12_path.read_text());anchors=[]
    for row in [r for r in calls if r['record']['query']=='action_replay']:
        old=next(o for o in old_calls if o['record']['id']==row['record']['source_v12_id'])
        anchors.append(dict(source_v12_id=old['record']['id'],messages_exact=row['record']['messages']==old['record']['messages'],
            previous_response=old['prediction']['response'],current_response=row['prediction']['response'],response_exact=old['prediction']['response']==row['prediction']['response'],
            previous_choice=old['choice'],current_choice=row['choice'],choice_exact=old['choice']==row['choice'],
            score_exact=old['score']==row['score'],token_exact=old['prediction']['input_tokens']==row['prediction']['input_tokens']))
    links=[]
    old_errors=[o for o in old_calls if o['record']['stage']==5 and o['score']['blue_direction_correct'] is False];assert len(old_errors)==8
    for old in old_errors:
        r=old['record'];actions=[a for a in sem if a['record']['query']=='action_replay' and a['record']['source_case_id']==r['source_case_id'] and a['record']['stage']==5 and a['record']['reverse_menu']==r['reverse_menu']]
        assert len(actions)==1;action=actions[0];state=next(s for s in sem if s['record']['query']=='state_readout' and s['record']['source_v12_id']==action['record']['source_v12_id'])
        links.append(dict(old_v12_id=r['id'],old_view=r['view'],old_wrong_choice=old['choice'],
            v13_action_source_id=action['record']['source_v12_id'],new_action_choice=action['choice'],new_action_score=action['score'],
            state_response=state['prediction']['response'],state_value=state['state_value'],state_truth=state['record']['public_state_truth'],state_score=state['score'],
            note='只关联原full观察；旧aid错误不当作本轮action重放错误，aid旧query不重跑。'))
    save(RESULT/'old_error_observation_links.json',dict(total_old_rows=8,old_full=4,old_aid=4,links=links,
        old_calls_sha256=sha(v12_path),current_calls_sha256=sha(calls_path),main_scoring_covers_all_64=True))
    bad=[row for row in sem if not row['score'].get('protocol_progress',row['score'].get('joint_state_correct'))]
    path=RESULT/'raw/incorrect_calls.json';save(path,bad)
    save(RESULT/'failure_audit.json',dict(total_incorrect=len(bad),action_incorrect=sum(r['record']['query']=='action_replay' for r in bad),
        state_semantic_incorrect=sum(r['record']['query']=='state_readout' for r in bad),ids=[r['record']['id'] for r in bad],
        raw_original_messages_outputs_path=str(path.relative_to(ROOT)),raw_original_messages_outputs_sha256=sha(path),
        no_model_action_executed=True))
    report=dict(all_passed=all(all(v for k,v in c.items() if k!='id') for c in checks) and frozen_summary_exact and semantic_summary_exact and
        len(anchors)==64 and all(a['messages_exact'] and a['token_exact'] for a in anchors),
        actual_model_calls=128,original_full_observations=64,checks=checks,frozen_summary_exact=frozen_summary_exact,semantic_summary_exact=semantic_summary_exact,
        action_anchor_checks=anchors,action_anchor_counts=dict(total=64,response_exact=sum(a['response_exact'] for a in anchors),choice_exact=sum(a['choice_exact'] for a in anchors),score_exact=sum(a['score_exact'] for a in anchors)),
        anchor_output_difference_is_result_not_audit_failure=True,system_replacements=[dict(old=old,new=new) for old,new in REPLACEMENTS],
        freeze_sha256=sha(FREEZE),calls_sha256=sha(calls_path),inputs_sha256=sha(INPUTS),
        postfreeze_auditor_sha256=sha(ROOT/'experiments/state_readout_v13/audit.py'),postfreeze_semantic_source_sha256=sha(ROOT/'experiments/state_readout_v13/semantic.py'),
        state_answer_not_provided_to_action=True,physics_actions_executed=0)
    save(RESULT/'audit.json',report);assert report['all_passed']
    print('128原冻结/语义/锚点审计通过；锚点',json.dumps(report['action_anchor_counts']),flush=True)


if __name__=='__main__':main()
