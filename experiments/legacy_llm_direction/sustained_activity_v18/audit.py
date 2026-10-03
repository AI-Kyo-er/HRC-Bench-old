"""冻结后独立全tick/消息/声明审计；不执行动作，不更改原评分。"""
import argparse
import copy
import gzip
import json
import math
import tempfile
from pathlib import Path
from experiments.physical.run import ROOT,save,sha
from experiments.structure_v8.audit import audit_trace
from experiments.responsive_transport_v16.world import CONFIG
from experiments.responsive_transport_v16.canonical import trace_digest,physics_equal
from experiments.transport_goal_v17.audit import actual_regions
from experiments.sustained_activity_v18.protocol import public_ledger,reference,candidates
from experiments.sustained_activity_v18.run import RESULT,freeze_path,hashes


def audit(stage):
    freeze=json.loads(freeze_path(stage).read_text());assert freeze['source_sha256']==hashes();reports=[]
    for case in freeze['cases']:
        folder=RESULT/'raw'/stage/case['id'];s=json.loads((folder/'summary.json').read_text());rows=json.loads((folder/'decisions.json').read_text())
        with tempfile.TemporaryDirectory(dir=RESULT/'raw') as name:
            tmp=Path(name);save(tmp/'summary.json',dict(s,goal_first_ticks=s['legacy_left_only_goal_first_ticks']));(tmp/'ticks.jsonl.gz').symlink_to((folder/'ticks.jsonl.gz').resolve());contacts=audit_trace(tmp,CONFIG)
        samples={tick:None for r in rows for tick in (r['before_tick'],r['after_tick'])};first_joint=None;tick_count=0
        target=public_ledger(s['public_final_history'])['goals']['blue']
        with gzip.open(folder/'ticks.jsonl.gz','rt') as stream:
            for line in stream:
                state=json.loads(line);tick_count+=1
                if state['tick'] in samples:samples[state['tick']]=state
                if first_joint is None and 'left' in actual_regions(state['objects'],'red') and target in actual_regions(state['objects'],'blue') and state['delivery_event'] is not None:first_joint=state['tick']
                final=state
        final_regions={i:actual_regions(final['objects'],i) for i in ('red','blue','green')}
        public_goal=public_ledger(rows[0]['observation']['history'])['goals']['blue']
        independent_facts=dict(delivery_occurred=final['delivery_event'] is not None,red_left='left' in final_regions['red'],blue_effective_goal=public_goal in final_regions['blue'],green_preserved=contacts['max_green_displacement_m']<.01)
        input_checks=[];previous=[]
        for r in rows:
            o=r['observation'];state=samples[r['before_tick']];annotations=s['initial_state'] if r['before_tick']==s['common_start_tick'] else state
            cs=dict(messages_exact=json.loads(r['messages'][1]['content'])==o and r['messages'][0]['content']==freeze['system'],menu_exact=o['candidates']==candidates(),
                no_private_labels=not any(k in o for k in ('case','seed','policy','score','success','current_goal','done_under_goals')),
                current_objects_exact=o['physical']['objects']==state['objects'],actual_regions_exact=o['physical_placements']=={i:actual_regions(state['objects'],i) for i in ('red','blue','green')},
                physical_snapshots_exact=physics_equal(r['before_state'],state) and physics_equal(r['after_state'],samples[r['after_tick']]),
                availability_after_init_clock=o['partner_availability']==annotations['availability'],history_snapshot_exact=o['history']==r['history_before'],
                immutable_history_prefix=o['history'][:len(previous)]==previous and all(e['observed_tick']<=r['before_tick'] for e in o['history']),
                feedback_no_oracle='success' not in r['result'] and not any(word in r['result']['feedback'] for word in ('公开目标','应到','约定区域','遗漏')))
            if stage=='reference':cs['reference_only_public_recomputed']=r['choice']==reference(copy.deepcopy(o),case['policy'])
            input_checks.append(dict(sequence=r['sequence'],checks=cs,passed=all(cs.values())));previous=r['history_after']
        forbids=('forbidden_robot_carrier','forbidden_other_object_carrier','carrier_static','non_target_robot')
        physical_safe=all(contacts['groups'][g]['records']==0 for g in forbids)
        checks=dict(single_initialization_no_red_prefix='left' not in rows[0]['observation']['physical_placements']['red'] and rows[0]['before_tick']==s['common_start_tick'],
            source_unchanged=True,all_inputs=all(r['passed'] for r in input_checks),terminal_score_facts=independent_facts==s['terminal_score']['facts'],
            expected_compliance=all(independent_facts.values())==(stage!='negative'),declared_done_really_ended=s['termination_reason']=='declared_done' and rows[-1]['choice']=='declare_done' and rows[-1]['result']['terminated'],
            declare_zero_physical_change=rows[-1]['before_state']==rows[-1]['after_state'] and rows[-1]['before_tick']==rows[-1]['after_tick'],
            after_terminal_call_no_mutation=s['after_terminal_rejected_no_mutation'],no_hidden_goal_in_completion_feedback=rows[-1]['result']['feedback']=='收到完成声明，活动已结束。',
            cost_decisions_exact=s['cost']['decisions']==len(rows),one_accept_one_start=s['cost']['accepted_requests']==int(s['delivery_start_tick'] is not None),
            exact_transport_support=contacts['support_coverage']==1 if s['delivery_start_tick'] is not None else contacts['transport_ticks']==0,
            full_contacts_safe=physical_safe,green_preserved=contacts['max_green_displacement_m']<.01,complete_contact_fields=contacts['missing_distance_or_position_pair_records']==0,
            delivery_and_fk=contacts['all_delivery_facts_match_independent_recomputation'] and contacts['event_history_consistent'] and contacts['same_tick_current_FK_joint_max_y_error_m']<1e-6,
            online_matches=contacts['online_match'],canonical_full_exact=trace_digest(folder/'ticks.jsonl.gz')==s['canonical_full_trace'],actual_final_physical_exact=physics_equal(final,s['final_state']),
            all_executions_success=all(e['success'] for e in s['executions']))
        recovery={}
        if stage=='recovery':
            first,repeat,restored=rows[3:6];first_target=first['choice'].rsplit('_',1)[1];restored_target=restored['choice'].rsplit('_',1)[1]
            recovery=dict(first_wrong_real_placement=first_target in actual_regions(first['after_state']['objects'],'blue') and first_target!=target and first['after_tick']>first['before_tick'],
                duplicate_no_physical_change=repeat['before_state']==repeat['after_state'] and repeat['before_tick']==repeat['after_tick'] and repeat['result']['no_op'],
                recovery_actual_final_region=restored_target==target and target in actual_regions(restored['after_state']['objects'],'blue') and restored['after_tick']>restored['before_tick'],
                fixed_seven_commands=[r['choice'] for r in rows]==case['commands'])
            checks.update(recovery)
        elif stage=='negative':checks['fixed_negative_sequence']=[r['choice'] for r in rows]==case['commands']
        reports.append(dict(id=case['id'],case=case,checks=checks,passed=all(checks.values()),input_checks=input_checks,contacts=contacts,actual_final_regions=final_regions,
            actual_joint_goal_first_tick=first_joint,task_goal_compliant=all(independent_facts.values()),safety_qualified_task_success=all(independent_facts.values()) and physical_safe,
            makespan_ticks=s['closed_activity_makespan_ticks'],cost=s['cost'],recovery=recovery))
        print(case['id'],reports[-1]['passed'],[k for k,v in checks.items() if not v],flush=True)
    paired=[]
    if stage=='reference':
        # 同seed/availability/policy/有效目标仅history不同，完整机械应一致。
        for seed in (100,101):
            for availability in ('ready','temporarily_busy'):
                for policy in ('public_ledger_parallel','conservative_serial'):
                    for goal in ('left','right'):
                        family=[r for r in reports if r['case']['seed']==seed and r['case']['availability']==availability and r['case']['policy']==policy and public_ledger(json.loads((RESULT/'raw/reference'/r['id']/'summary.json').read_text())['public_final_history'])['goals']['blue']==goal]
                        digests=[trace_digest(RESULT/'raw/reference'/r['id']/'ticks.jsonl.gz') for r in family];paired.append(dict(seed=seed,availability=availability,policy=policy,goal=goal,ids=[r['id'] for r in family],full_physical_exact=all(x==digests[0] for x in digests)))
    result=dict(stage=stage,total=len(reports),passed=sum(r['passed'] for r in reports),goal_compliant=sum(r['task_goal_compliant'] for r in reports),total_ticks=sum(r['contacts']['total_ticks'] for r in reports),
        episodes=reports,physics_pairs=paired,freeze_sha256=sha(freeze_path(stage)),audit_source_sha256={n:sha(ROOT/n) for n in ('experiments/sustained_activity_v18/audit.py','experiments/transport_goal_v17/audit.py','experiments/structure_v8/audit.py','experiments/responsive_transport_v16/canonical.py')},
        zero_tick_events='依decision/event序列，不按tick合并；初始化availability注解用构造完成初始快照，其余来自同tick。')
    save(RESULT/f'{stage}_audit.json',result);assert result['passed']==len(reports) and all(p['full_physical_exact'] for p in paired)
    print('独立审计通过',stage,result['total_ticks'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('recovery','negative','reference'));audit(p.parse_args().stage)
