"""216调用完成后的独立来源、评分、物品字段及错误原输出审计。"""
import json
from collections import Counter
from experiments.physical.run import ROOT,save,sha
from experiments.state_calibration_v14.run import FREEZE,INPUTS,SOURCES,SOURCE_INPUTS,hashes
from experiments.state_calibration_v14.dataset import RESULT,build_records
from experiments.state_calibration_v14.scoring import score_record
from experiments.state_calibration_v14.analysis import summarize


def main():
    f=json.loads(FREEZE.read_text());inputs=json.loads(INPUTS.read_text());expected=build_records()
    assert f['source_sha256']==hashes(SOURCES) and f['source_inputs_sha256']==hashes(SOURCE_INPUTS) and f['inputs_sha256']==sha(INPUTS)
    checks=[];rows=[];finished={}
    for model in ('qwen2_5_14b','qwen3_vl_8b'):
        base=RESULT/f'raw/model_{model}';calls=json.loads((base/'calls.json').read_text());end=json.loads((base/'finished.json').read_text())
        assert len(calls)==f['models'][model]['records']==end['calls']
        assert summarize(calls)=={k:v for k,v in json.loads((base/'summary.json').read_text()).items() if k!='model'}
        finished[model]=end;rows.extend(calls)
    assert len(rows)==len(inputs)==len(expected)==216
    for r,row,e in zip(inputs,rows,expected):
        rescored=score_record(r,row['prediction']['response'])
        checks.append(dict(id=r['id'],record_exact=r==row['record'],source_exact={k:v for k,v in r.items() if k!='frozen_input_tokens'}==e,
            token_exact=r['frozen_input_tokens']==row['prediction']['input_tokens'],score_parse_exact=all(row[k]==v for k,v in rescored.items()),
            truncation_exact=row['truncated']==row['prediction']['generation_hit_limit'],physical_not_executed=row['score']['physical_execution'] is False and row['score']['physical_success'] is None))
    summary=summarize(rows);summary.update(freeze_sha256=sha(FREEZE),model_metadata={m:e['model'] for m,e in finished.items()})
    save(RESULT/'summary.json',summary)
    incorrect=[]
    for row in rows:
        s=row['score'];ok=s.get('joint_state_correct',s.get('protocol_progress',s.get('acceptable')))
        if not ok:incorrect.append(row)
    save(RESULT/'raw/incorrect_calls.json',incorrect)
    save(RESULT/'failure_audit.json',dict(total_incorrect=len(incorrect),by_model_suite_query=dict(Counter('__'.join(row['record'][k] for k in ('model','suite','query')) for row in incorrect)),
        incorrect_ids=[r['record']['id'] for r in incorrect],original_messages_outputs_path=str((RESULT/'raw/incorrect_calls.json').relative_to(ROOT)),original_messages_outputs_sha256=sha(RESULT/'raw/incorrect_calls.json'),
        no_model_actions_executed=True))
    state_rows=[r for r in rows if r['record']['query']=='state_readout']
    field_tables=[]
    for model,suite in sorted({(r['record']['model'],r['record']['suite']) for r in state_rows}):
        selected=[r for r in state_rows if r['record']['model']==model and r['record']['suite']==suite]
        field_tables.append(dict(model=model,suite=suite,total=len(selected),distributions={k:dict(Counter(json.dumps(r['state_value'][k]) if r['state_value'] else '<parse_error>' for r in selected)) for k in ('outer_blue_destination','guidance_active','current_blue_destination')}))
    save(RESULT/'field_distributions.json',field_tables)
    calibration=[]
    for row in (r for r in rows if r['record']['suite']=='control'):
        r=row['record'];obs=json.loads(r['messages'][1]['content']);truth=r['public_state_truth'];value=row['state_value']
        calibration.append(dict(id=r['id'],model=r['model'],group=r['group'],public_history=obs['history'],blue_actual_regions=obs['physical_placements']['blue'],
            truth=truth,response=row['prediction']['response'],value=value,field_correct=row['score']['field_correct'],joint_correct=row['score']['joint_state_correct'],
            current_output_matches_actual_region=value is not None and value['current_blue_destination'] in obs['physical_placements']['blue']))
    directions=[]
    for row in (r for r in rows if r['record']['suite']=='v13' and r['record']['query']=='action_replay' and r['score']['blue_direction_correct'] is False):
        r=row['record'];obs=json.loads(r['messages'][1]['content']);proposal=next(e['destination'] for e in obs['history'] if e['kind']=='update_proposed')
        directions.append(dict(id=r['id'],stage=r['stage'],timing=r['timing'],acceptance=r['acceptance'],initial_blue=r['initial_blue'],proposed_blue=proposal,
            effective_outer_blue=r['effective_blue'],current_blue_goal=r['public_state_truth']['current_blue_destination'],choice=row['choice'],
            matches_initial=row['choice'].rsplit('_',1)[-1]==r['initial_blue'],matches_proposal=row['choice'].rsplit('_',1)[-1]==proposal,
            no_physical_action_executed=True))
    save(RESULT/'control_and_direction_audit.json',dict(control_rows=calibration,current_only_control_errors=sum(not r['joint_correct'] and all(r['field_correct'][k] for k in ('outer_blue_destination','guidance_active')) for r in calibration),
        v13_wrong_blue_rows=directions,all_control_truth_from_public_input=True,position_match_is_descriptive_not_causal=True))
    control_pairs=[]
    for model in ('qwen2_5_14b','qwen3_vl_8b'):
        selected=[r for r in calibration if r['model']==model];groups={}
        for r in selected:
            h=r['public_history']
            initial=next((e['goals']['blue'] for e in h if e['kind']=='accepted_outer'),r['truth']['outer_blue_destination'])
            reply=next((e['decision'] for e in h if e['kind']=='proposal_reply'),None)
            key=(r['group'],initial,r['truth']['guidance_active'],reply)
            groups.setdefault(key,[]).append(r)
        for key,pair in sorted(groups.items()):
            assert len(pair)==2 and pair[0]['truth']==pair[1]['truth']
            control_pairs.append(dict(model=model,group=key[0],initial_or_outer=key[1],active=key[2],reply=key[3],
                ids=[r['id'] for r in pair],actual_regions=[r['blue_actual_regions'] for r in pair],values=[r['value'] for r in pair],
                joint_correct=[r['joint_correct'] for r in pair],response_changed=pair[0]['response']!=pair[1]['response'],
                semantic_value_changed=pair[0]['value']!=pair[1]['value'],correctness_changed=pair[0]['joint_correct']!=pair[1]['joint_correct'],
                public_history_equal=pair[0]['public_history']==pair[1]['public_history'],
                scope_ended_outer_has_added_delivery_feedback=key[0]=='scope' and not key[2]))
    cross_rows=[]
    v13=[r for r in rows if r['record']['suite']=='v13']
    for a in (r for r in v13 if r['record']['query']=='action_replay'):
        s=next(r for r in v13 if r['record']['query']=='state_readout' and r['record']['source_v12_id']==a['record']['source_v12_id'])
        r=a['record'];cross_rows.append(dict(source_v12_id=r['source_v12_id'],stage=r['stage'],timing=r['timing'],acceptance=r['acceptance'],reverse_menu=r['reverse_menu'],initial_blue=r['initial_blue'],
            action_correct=a['score']['protocol_progress'],outer_correct=s['score']['field_correct']['outer_blue_destination'],
            current_correct=s['score']['field_correct']['current_blue_destination'],joint_correct=s['score']['joint_state_correct']))
    def cross_table(selected):
        return {field:dict(Counter(('state_correct' if r[field] else 'state_incorrect')+'_'+('action_correct' if r['action_correct'] else 'action_incorrect') for r in selected)) for field in ('outer_correct','current_correct','joint_correct')}
    grouped={factor:{str(value):cross_table([r for r in cross_rows if r[factor]==value]) for value in sorted({r[factor] for r in cross_rows})} for factor in ('stage','timing','acceptance','reverse_menu','initial_blue')}
    save(RESULT/'paired_field_audit.json',dict(control_region_pairs=control_pairs,control_pair_counts={m:{g:dict(pairs=sum(p['model']==m and p['group']==g for p in control_pairs),
        correctness_changes=sum(p['model']==m and p['group']==g and p['correctness_changed'] for p in control_pairs)) for g in ('direct','scope','update')} for m in ('qwen2_5_14b','qwen3_vl_8b')},
        v13_cross_rows=cross_rows,v13_all_cross=cross_table(cross_rows),v13_cross_by_group=grouped,
        scope_feedback_difference_is_confound=True,independent_queries_not_internal_knowledge=True))
    report=dict(all_passed=all(all(v for k,v in c.items() if k!='id') for c in checks),total_calls=216,checks=checks,
        v13_source_exact=128,v4_source_exact=40,controls=48,physics_actions_executed=0,source_sha256_unchanged=True,
        freeze_sha256=sha(FREEZE),inputs_sha256=sha(INPUTS),calls_sha256={m:sha(RESULT/f'raw/model_{m}/calls.json') for m in finished},
        postfreeze_audit_source_sha256=sha(ROOT/'experiments/state_calibration_v14/audit.py'),json_order_separate_from_semantics=True)
    save(RESULT/'audit.json',report);assert report['all_passed']
    print('216来源/解析/分组评分审计通过。',flush=True)


if __name__=='__main__':main()
