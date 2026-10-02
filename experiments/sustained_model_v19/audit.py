"""冻结后独立审计：精确重建每次实际模型输入、全tick及结束评分。"""
import argparse
import copy
import gzip
import json
import tempfile
from pathlib import Path
from experiments.physical.run import ROOT,save,sha
from experiments.structure_v8.audit import audit_trace
from experiments.transport_goal_v17.audit import actual_regions
from experiments.responsive_transport_v16.world import CONFIG
from experiments.responsive_transport_v16.canonical import physics_equal,trace_digest
from experiments.sustained_activity_v18.protocol import public_ledger
from experiments.sustained_model_v19.inputs import messages,parse_output,recognition_records
from experiments.sustained_model_v19.run import RESULT,FREEZE,hashes

FORBIDDEN=('forbidden_robot_carrier','forbidden_other_object_carrier','carrier_static','non_target_robot')

def results_passed(episodes,identification,expected):
    return len(episodes)==expected and all(r['passed'] for r in episodes) and len(identification)==12 and all(r['passed'] for r in identification)

def prediction_checks(prediction,expected_messages,seed,tokenizer):
    generated=prediction['generated_ids'];response=tokenizer.decode(generated,skip_special_tokens=True);parsed=parse_output(response)
    ids=tokenizer.apply_chat_template(expected_messages,tokenize=True,add_generation_prompt=True,enable_thinking=True)
    # 解析helper按最后字符串边界；同时独立核对官方最后151668 token边界。
    positions=[i for i,v in enumerate(generated) if v==151668]
    official_final=tokenizer.decode(generated[positions[-1]+1:],skip_special_tokens=True).strip() if positions else None
    return dict(messages_exact=prediction['messages']==expected_messages,input_ids_exact=prediction['input_ids']==ids,
        response_decode_exact=response==prediction['response'],special_decode_exact=prediction['response_with_special_tokens']==tokenizer.decode(generated,skip_special_tokens=False),
        seed_exact=prediction['seed']==seed,strict_parse_recomputed=all(prediction[k]==v for k,v in parsed.items()),
        official_last_token_boundary_exact=prediction['final_response']==official_final,input_output_count_exact=prediction['input_tokens']==len(ids) and prediction['output_tokens']==len(generated),
        marker_count_exact=prediction['think_end_marker_count']==len(positions))

def audit(view=None):
    from transformers import AutoTokenizer
    f=json.loads(FREEZE.read_text());assert f['source_sha256']==hashes()
    tokenizer=AutoTokenizer.from_pretrained(f['model_spec']['path'],local_files_only=True)
    identification=json.loads((RESULT/'raw/identification_calls.json').read_text());source=recognition_records(ROOT);id_checks=[]
    for record,row in zip(f['identification'],identification):
        check=prediction_checks(row['prediction'],record['messages'],record['seed'],tokenizer)
        check.update(source_recomputed=all(record[k]==v for k,v in source[len(id_checks)].items()),record_exact=row['record']==record,
            correct_recomputed=row['correct']==(row['prediction']['choice']==record['expected']))
        id_checks.append(dict(id=record['id'],checks=check,passed=all(check.values()),correct=row['correct'],choice=row['prediction']['choice'],parse_error=row['prediction']['parse_error']))
    reports=[];all_calls=list(r['prediction'] for r in identification)
    selected=[r for r in f['episodes'] if view is None or r['view']==view]
    for record in selected:
        folder=RESULT/'raw/episodes'/record['id'];summary=json.loads((folder/'summary.json').read_text());rows=json.loads((folder/'decisions.json').read_text())
        with tempfile.TemporaryDirectory(dir=RESULT/'raw') as name:
            tmp=Path(name);save(tmp/'summary.json',dict(summary,goal_first_ticks=summary['legacy_left_only_goal_first_ticks']));(tmp/'ticks.jsonl.gz').symlink_to((folder/'ticks.jsonl.gz').resolve());contacts=audit_trace(tmp,CONFIG)
        samples={tick:None for r in rows for tick in (r['before_tick'],r['after_tick'])};first_joint=None
        target=public_ledger(rows[0]['observation']['history'])['goals']['blue']
        with gzip.open(folder/'ticks.jsonl.gz','rt') as stream:
            for line in stream:
                state=json.loads(line)
                if state['tick'] in samples:samples[state['tick']]=state
                if first_joint is None and target in actual_regions(state['objects'],'blue') and 'left' in actual_regions(state['objects'],'red') and state['delivery_event'] is not None:first_joint=state['tick']
                final=state
        regions={i:actual_regions(final['objects'],i) for i in ('red','blue','green')}
        facts=dict(delivery_occurred=final['delivery_event'] is not None,red_left='left' in regions['red'],blue_effective_goal=target in regions['blue'],green_preserved=contacts['max_green_displacement_m']<.01)
        checks=[];previous=None;wrong_choices=[];wrong_placements=[];first_blue=None;types={}
        for r in rows:
            p=r['prediction'];o=r['observation'];m=messages(o,record['view']);s=samples[r['before_tick']]
            a=summary['initial_state'] if r['before_tick']==summary['common_start_tick'] else s
            check=prediction_checks(p,m,190000+record['case']['index']*100+r['sequence'],tokenizer)
            check.update(messages_builder_exact=m==r['messages'],raw_observation_no_summary='external_public_ledger_aid' not in o,
                initial_exact=not(r['sequence']==0) or o==record['initial_observation'],six_menu_exact=o['candidates']==f['candidates'],
                no_private_input=not any(k in o for k in ('case','seed','view','score','success','current_goal','done_under_goals')),
                actual_objects_exact=o['physical']['objects']==s['objects'],actual_regions_exact=o['physical_placements']=={i:actual_regions(s['objects'],i) for i in ('red','blue','green')},
                current_carrier_exact=o['physical']['carrier_position']==s['partner_position'] and o['physical']['carrier_joint']==s['partner_joint'] and o['physical']['carrier_velocity']==s['partner_velocity'] and o['physical']['carrier_command']==s['partner_command'],
                availability_same_tick=o['partner_availability']==a['availability'],delivery_same_tick=o['delivery_event']==a['delivery_event'],
                physical_snapshots_exact=physics_equal(r['before_state'],s) and physics_equal(r['after_state'],samples[r['after_tick']]),history_exact=o['history']==r['history_before'],
                previous_history_immutable=previous is None or r['history_before']==previous,
                no_future_events=all(e['observed_tick']<=r['before_tick'] for e in o['history']),event_sequence_exact=all(e['event_sequence']==i for i,e in enumerate(o['history'])),
                budget_exact=o['remaining_decisions']==12-r['sequence'],action_matches_parse=r['choice']==p['choice'],
                feedback_not_oracle='success' not in r['result'] and not any(v in r['result']['feedback'] for v in ('公开目标','应到','约定区域','遗漏')),
                invalid_parser_consumes_one_without_execution=p['parse_error'] is None or (r['choice'] is None and not r['result']['valid'] and r['before_tick']==r['after_tick'] and 'execution' not in r['result']))
            previous=r['history_after'];checks.append(dict(sequence=r['sequence'],checks=check,passed=all(check.values())))
            choice=r['choice'];types[str(choice)]=types.get(str(choice),0)+1;all_calls.append(p)
            if choice in ('place_blue_left','place_blue_right'):
                selected_destination=choice.rsplit('_',1)[1];entry=dict(sequence=r['sequence'],selected=selected_destination,effective=target,direction_correct=selected_destination==target,protocol_valid=r['result']['valid'],
                    executed='execution' in r['result'],before_tick=r['before_tick'],after_tick=r['after_tick'],actual_after_regions=actual_regions(r['after_state']['objects'],'blue'))
                if first_blue is None:first_blue=entry
                if selected_destination!=target:wrong_choices.append(entry)
                if selected_destination!=target and entry['executed'] and selected_destination in entry['actual_after_regions']:wrong_placements.append(entry)
        safe=all(contacts['groups'][g]['records']==0 for g in FORBIDDEN)
        cs=dict(inputs_all=all(c['passed'] for c in checks),source_unchanged=True,canonical_trace_exact=trace_digest(folder/'ticks.jsonl.gz')==summary['canonical_full_trace'],
            final_physical_exact=physics_equal(final,summary['final_state']),score_facts_exact=facts==summary['terminal_score']['facts'],cost_decisions_exact=len(rows)==summary['cost']['decisions'],
            invalid_decisions_exact=summary['cost']['invalid']==sum(not r['result']['valid'] for r in rows),after_terminal_no_mutation=summary['after_terminal_rejected_no_mutation'],
            actually_terminated=rows[-1]['result']['terminated'] and summary['termination_reason']==rows[-1]['result']['termination_reason'],
            declared_event_exact=summary['termination_reason']!='declared_done' or (rows[-1]['choice']=='declare_done' and rows[-1]['before_state']==rows[-1]['after_state'] and rows[-1]['result']['feedback']=='收到完成声明，活动已结束。'),
            complete_contact_evidence=contacts['missing_distance_or_position_pair_records']==0,delivery_recomputed=contacts['all_delivery_facts_match_independent_recomputation'] and contacts['event_history_consistent'],
            same_tick_FK=contacts['same_tick_current_FK_joint_max_y_error_m']<1e-6,online_contact_matches=contacts['online_match'])
        reports.append(dict(id=record['id'],record=record['case'],view=record['view'],checks=cs,passed=all(cs.values()),input_checks=checks,contacts=contacts,
            goal_compliant=all(facts.values()),declared_task_goal_success=all(facts.values()) and summary['termination_reason']=='declared_done',safety_qualified_task_success=all(facts.values()) and safe and summary['termination_reason']=='declared_done',
            physically_safe=safe,termination_reason=summary['termination_reason'],first_blue_attempt=first_blue,wrong_blue_direction_choices=wrong_choices,real_wrong_blue_placements=wrong_placements,
            recovered_after_real_wrong_placement=bool(wrong_placements) and all(facts.values()),early_or_wrong_declaration=summary['termination_reason']=='declared_done' and not all(facts.values()),
            action_distribution=types,cost=summary['cost'],makespan_ticks=summary['closed_activity_makespan_ticks'],makespan_seconds=summary['closed_activity_makespan_seconds'],
            first_joint_physical_tick=first_joint,model_wall_seconds=summary['model_wall_seconds'],wall_seconds=summary['wall_seconds'],actual_final_regions=regions))
        print(record['id'],reports[-1]['passed'],reports[-1]['goal_compliant'],reports[-1]['termination_reason'],[k for k,v in cs.items() if not v],flush=True)
    grouped={}
    for group_view in ('full_history','public_ledger_aid'):
        subset=[r for r in reports if r['view']==group_view]
        if not subset:continue
        grouped[group_view]=dict(total=len(subset),goal_compliant=sum(r['goal_compliant'] for r in subset),declared_goal_success=sum(r['declared_task_goal_success'] for r in subset),safety_qualified_success=sum(r['safety_qualified_task_success'] for r in subset),
            budget_exhausted=sum(r['termination_reason']=='budget_exhausted' for r in subset),wrong_or_early_declaration=sum(r['early_or_wrong_declaration'] for r in subset),
            physical_failure=sum(r['termination_reason']=='physical_failure' for r in subset),wait_timeout=sum(r['termination_reason']=='wait_timeout' for r in subset),
            wrong_direction_choices=sum(len(r['wrong_blue_direction_choices']) for r in subset),real_wrong_placements=sum(len(r['real_wrong_blue_placements']) for r in subset),
            recovered=sum(r['recovered_after_real_wrong_placement'] for r in subset),costs={k:sum(r['cost'][k] for r in subset) for k in subset[0]['cost']})
    pairs=[] if view is not None else [dict(case=base,full=reports[i]['safety_qualified_task_success'],aid=reports[i+12]['safety_qualified_task_success'],
        complete_action_sequence_equal=[r['choice'] for r in json.loads((RESULT/'raw/episodes'/reports[i]['id']/'decisions.json').read_text())]==[r['choice'] for r in json.loads((RESULT/'raw/episodes'/reports[i+12]['id']/'decisions.json').read_text())]) for i,base in enumerate([r['record'] for r in reports[:12]])]
    reference=json.loads((ROOT/'results/sustained_activity_v18/final_summary.json').read_text())['reference_costs'];cost_matches=[]
    for r in reports:
        c=r['record'];family=[x for x in reference if x['case']['seed']==100 and x['case']['initial_blue']==c['initial_blue'] and x['case']['update']==c['update'] and x['case']['availability']==c['availability']]
        cost_matches.append(dict(id=r['id'],model=r['cost'],model_episode_until_termination_ticks=r['makespan_ticks'],goal_compliant=r['goal_compliant'],safety_qualified_task_success=r['safety_qualified_task_success'],
            success_completion_duration_ticks=r['makespan_ticks'] if r['safety_qualified_task_success'] else None,failure_until_termination_ticks=None if r['safety_qualified_task_success'] else r['makespan_ticks'],
            references=[dict(policy=x['case']['policy'],decisions=x['decisions'],makespan_ticks=x['makespan_ticks'],requests=x['requests'],rejected_requests=x['rejected_requests'],physical_attempts=x['physical_attempts'],wait_ready_ticks=x['wait_ready_ticks'],wait_delivery_ticks=x['wait_delivery_ticks']) for x in family]))
    errors=[]
    for r in reports:
        if not r['safety_qualified_task_success'] or r['wrong_blue_direction_choices'] or r['cost']['invalid']:
            errors.append(dict(id=r['id'],result={k:r[k] for k in ('termination_reason','goal_compliant','first_blue_attempt','wrong_blue_direction_choices','real_wrong_blue_placements','cost')},
                original_decisions=json.loads((RESULT/'raw/episodes'/r['id']/'decisions.json').read_text())))
    save(RESULT/('raw/failure_audit.json' if view is None else f'raw/{view}_failure_audit.json'),errors)
    artifact=dict(freeze_sha256=sha(FREEZE),source_sha256=hashes(),audit_source_sha256=sha(ROOT/'experiments/sustained_model_v19/audit.py'),identification=id_checks,episodes=reports,groups=grouped,pairs=pairs,reference_cost_comparison=cost_matches,
        total_physical_ticks=sum(r['contacts']['total_ticks'] for r in reports),contacts_records={g:sum(r['contacts']['groups'][g]['records'] for r in reports) for g in ('expected_blue_carrier',)+FORBIDDEN},
        all_inputs_and_scores_pass=results_passed(reports,id_checks,24 if view is None else 12),
        total_calls=len(all_calls),parse_errors=sum(p['parse_error'] is not None for p in all_calls),truncated=sum(p['generation_hit_limit'] for p in all_calls),max_input_tokens=max(p['input_tokens'] for p in all_calls),
        total_output_tokens=sum(p['output_tokens'] for p in all_calls),model_wall_seconds=sum(p['seconds'] for p in all_calls),note='识别不执行；自主输入逐步重建，无参考状态替换；不同view后续轨迹自然分叉。目标符合、声明成功及接触安全分列；合法慢动作成本不自动判错。')
    save(RESULT/('model_audit.json' if view is None else f'{view}_audit.json'),artifact);assert artifact['all_inputs_and_scores_pass']
    print('独立审计完成',grouped,artifact['total_calls'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--view',choices=('full_history','public_ledger_aid'));audit(p.parse_args().view)
