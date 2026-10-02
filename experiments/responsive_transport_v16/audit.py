"""独立只读全tick/启动因果/公开时间/零tick事件与成本审计。"""
import argparse
import copy
import gzip
import json
import math
from experiments.physical.run import ROOT,save,sha
from experiments.structure_v8.audit import audit_trace
from experiments.structure_v8.reference_audit import regions
from experiments.responsive_transport_v16.run import RESULT,CONTROL_FREEZE,REFERENCE_FREEZE,hashes
from experiments.responsive_transport_v16.protocol import SYSTEM,candidates,public_ledger,reference
from experiments.responsive_transport_v16.world import DT,CONFIG,profile_distance
from experiments.responsive_transport_v16.canonical import physics_equal,trace_digest


def episode_audit(case,stage):
    folder=RESULT/'raw'/stage/case['id'];s=json.loads((folder/'summary.json').read_text());rows=json.loads((folder/('steps.json' if stage=='controls' else 'decisions.json')).read_text())
    t0=s['common_start_tick'];ready_tick=t0+(1920 if case['initial_availability']=='temporarily_busy' else 0)
    requests=[r for r in rows if r.get('result',{}).get('choice')=='request_transport'];accepted=[r for r in requests if r['result']['request_decision']=='accepted']
    assert len(accepted)<=1;start=accepted[0]['before_tick'] if accepted else None;assert s['delivery_start_tick']==start
    snapshots={};needed={r['before_tick'] for r in rows}|{r['after_tick'] for r in rows};pre_start_ticks=pre_start_supported=0;max_pre_start_joint_error=0;max_pre_start_slip=0
    clock_ok=profile_ok=not_autostart=True;actual_ready_ticks=[];red_moving_ticks=0
    red=next((i for i in s['robot_intervals'] if i['item']=='red'),None)
    with gzip.open(folder/'ticks.jsonl.gz','rt') as f:
        for line in f:
            state=json.loads(line);tick=state['tick']
            if tick in needed:snapshots[tick]=state
            if tick>t0:
                a=state['availability'];status='ready' if tick>=ready_tick else 'temporarily_busy'
                expected_event=dict(kind='partner_ready',availability_actual_tick=ready_tick,content='伙伴资源现在可接受新的运输请求；不会自动执行此前拒绝的请求。') if status=='ready' else None
                clock_ok=clock_ok and a==dict(status=status,common_start_tick=t0,physics_tick=tick,elapsed_seconds=(tick-t0)*DT,ready_event=expected_event)
                if tick==ready_tick:actual_ready_ticks.append(tick)
            expected_start=start if start is not None and tick>start else None
            not_autostart=not_autostart and state['delivery_start_tick']==expected_start
            target=CONFIG['travel_m']-profile_distance((tick-start)*DT) if start is not None and tick>start else .6
            profile_ok=profile_ok and state['partner_command']==target
            if tick>t0 and (start is None or tick<=start):
                pre_start_ticks+=1;pre_start_supported+=int(state['delivery_facts']['supported']);max_pre_start_joint_error=max(max_pre_start_joint_error,abs(state['partner_joint']-.6))
                max_pre_start_slip=max(max_pre_start_slip,math.hypot(*state['delivery_facts']['relative_position'][:2]))
            if red and start is not None and s['delivery_event'] is not None and red['start']<tick<=red['end'] and start<tick<=s['delivery_event']['first_tick'] and abs(state['partner_velocity'])>1e-6:red_moving_ticks+=1
    assert clock_ok and profile_ok and not_autostart
    checked=[]
    for i,r in enumerate(rows):
        obs=r['observation'];history=obs['history'];snap=snapshots[r['before_tick']];next_history=rows[i+1]['observation']['history'] if i+1<len(rows) else s['public_final_history'];delta=next_history[len(history):]
        expected_ready_event=dict(kind='partner_ready',availability_actual_tick=ready_tick,content='伙伴资源现在可接受新的运输请求；不会自动执行此前拒绝的请求。') if r['before_tick']>=ready_tick else None
        check=dict(sequence=i,messages_exact=r['messages']==[dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(obs,ensure_ascii=False))],
            full_21_menu=obs['candidates']==candidates(),only_public_keys=set(obs)=={'history','physical','physical_placements','partner_availability','delivery_event','transport_started','remaining_decisions','candidates'},
            actual_objects_exact=obs['physical']['objects']==snap['objects'],actual_carrier_pose_exact=obs['physical']['carrier_position']==snap['partner_position'],
            actual_carrier_joint_exact=obs['physical']['carrier_joint']==snap['partner_joint'],actual_carrier_velocity_exact=obs['physical']['carrier_velocity']==snap['partner_velocity'],
            actual_carrier_command_exact=obs['physical']['carrier_command']==snap['partner_command'],regions_actual=obs['physical_placements']==regions(snap),
            current_availability_exact=obs['partner_availability']==dict(status='ready' if r['before_tick']>=ready_tick else 'temporarily_busy',common_start_tick=t0,physics_tick=r['before_tick'],elapsed_seconds=(r['before_tick']-t0)*DT,ready_event=expected_ready_event),
            no_future_availability=expected_ready_event==obs['partner_availability']['ready_event'],history_immutable_prefix=next_history[:len(history)]==history,
            transport_started_public_consistent=obs['transport_started']==public_ledger(history)['started'],actual_delivery_event_exact=obs['delivery_event']==snap['delivery_event'])
        if r.get('kind')!='physical_wait':
            result=r['result'];check['feedback_exact_once']=delta.count(next(e for e in delta if e['kind']=='action_feedback'))==1 and next(e for e in delta if e['kind']=='action_feedback')['choice']==result['choice']
            if result['choice']=='request_transport':
                expected='already_started' if obs['transport_started'] else ('accepted' if obs['partner_availability']['status']=='ready' else 'rejected')
                check.update(request_decision_independent_of_policy=result['request_decision']==expected,request_zero_tick=r['after_tick']==r['before_tick'],request_no_physical_change=physics_equal(result['before_request'],result['after_request']),
                    request_event_exact=delta.count(result['request_event'])==1,not_silent_restart=result['after_request']['delivery_start_tick']==(r['before_tick'] if expected=='accepted' else result['before_request']['delivery_start_tick']))
            if stage=='reference':check['policy_public_only_choice']=reference(obs,case['policy'])==result['choice']
        else:check['real_wait_window_exact']=r['after_tick']-r['before_tick']==r['requested_ticks']
        assert all(v for k,v in check.items() if k!='sequence'),check;checked.append(check)
    # event_sequence区分同tick多个零时长事件；不能用tick覆盖history。
    events=s['public_final_history'];assert [e['event_sequence'] for e in events]==list(range(len(events)))
    assert all(e['observed_tick']>=e.get('availability_actual_tick',e['observed_tick']) for e in events)
    ready_events=[e for e in events if e['kind']=='partner_ready'];assert len(ready_events)==1 and ready_events[0]['availability_actual_tick']==ready_tick
    for r in rows:
        for e in r['observation']['history']:assert e['observed_tick']<=r['before_tick'] and e.get('availability_actual_tick',r['before_tick'])<=r['before_tick']
    assert s['cost']['accepted_requests']==len(accepted) and s['cost']['requests']==len(requests)
    a=audit_trace(folder,CONFIG);assert a==s['independent_contact_delivery_audit'] and a['safety_pass'] and a['groups']['non_target_robot']['records']==0
    assert trace_digest(folder/'ticks.jsonl.gz')==s['canonical_full_trace']
    assert pre_start_supported==pre_start_ticks and max_pre_start_joint_error<1e-5 and max_pre_start_slip<CONFIG['blue_relative_xy_tolerance']
    assert s['green_preserved'] and a['max_green_displacement_m']<.01
    waits=sum(r['after_tick']-r['before_tick'] for r in rows if r.get('kind')=='physical_wait' or r.get('result',{}).get('choice')=='yield');assert waits==s['wait_ticks']
    if stage=='reference':
        assert s['success'] and s['closed_task_makespan_ticks']==rows[-1]['after_tick']-t0
        blue=next(i for i in s['robot_intervals'] if i['item']=='blue');assert blue['start']>=s['delivery_event']['first_tick']
        expected_overlap=max(0,min(red['end'],s['delivery_event']['first_tick'])-max(red['start'],start));assert expected_overlap==s['red_skill_transport_overlap_ticks']
        assert s['cost']['decisions']==len(rows) and s['cost']['wait_ticks']==s['cost']['wait_ready_ticks']+s['cost']['wait_delivery_ticks']
    return dict(id=case['id'],passed=True,decisions=checked,contact_delivery=a,availability_actual_tick=ready_tick,availability_observed_tick=ready_events[0]['observed_tick'],
        all_tick_clock_exact=clock_ok,all_tick_motor_profile_exact=profile_ok,started_only_after_accepted_request=not_autostart,pre_start_ticks=pre_start_ticks,pre_start_support_ticks=pre_start_supported,max_pre_start_carrier_joint_error_m=max_pre_start_joint_error,
        max_pre_start_relative_xy_slip_m=max_pre_start_slip,red_transport_moving_ticks=red_moving_ticks,wait_ticks=waits,
        canonical_full_trace=s['canonical_full_trace'],source_rows_sha256=sha(folder/('steps.json' if stage=='controls' else 'decisions.json')))


def main(stage):
    freeze=CONTROL_FREEZE if stage=='controls' else REFERENCE_FREEZE;f=json.loads(freeze.read_text());assert f['source_sha256']==hashes()
    results=[episode_audit(c,stage) for c in f['cases']];summary=json.loads((RESULT/('control_summary.json' if stage=='controls' else 'reference_summary.json')).read_text())
    pairs=summary['pairs'];assert all(all(v for k,v in p.items() if k!='seed') for p in pairs)
    costs={};input_pairs=[]
    if stage=='reference':
        for seed in (80,81):
            for status in ('ready','temporarily_busy'):
                chosen=[c for c in f['cases'] if c['seed']==seed and c['initial_availability']==status]
                folders=[RESULT/'raw/reference'/c['id'] for c in chosen]
                raw_rows=[json.loads((folder/'decisions.json').read_text()) for folder in folders]
                sums=[json.loads((folder/'summary.json').read_text()) for folder in folders]
                messages_equal=all(r[0]['messages']==raw_rows[0][0]['messages'] for r in raw_rows)
                assert messages_equal
                input_pairs.append(dict(seed=seed,current_initial_status=status,ids=[c['id'] for c in chosen],initial_messages_exact_all_policies=messages_equal))
                table={c['policy']:dict(closed_task_makespan_ticks=s['closed_task_makespan_ticks'],closed_task_makespan_seconds=s['closed_task_makespan_seconds'],first_goal_satisfaction_from_t0_ticks=s['first_goal_satisfaction_from_t0_ticks'],delivery_start_tick=s['delivery_start_tick'],delivery_tick=s['delivery_event']['first_tick'],delivery_elapsed_ticks=s['delivery_elapsed_ticks'],red_skill_transport_overlap_ticks=s['red_skill_transport_overlap_ticks'],cost=s['cost']) for c,s in zip(chosen,sums)}
                table['actual_comparisons']=dict(greedy_minus_wait_ready_makespan_ticks=table['availability_greedy']['closed_task_makespan_ticks']-table['wait_ready']['closed_task_makespan_ticks'],serial_minus_greedy_makespan_ticks=table['serial']['closed_task_makespan_ticks']-table['availability_greedy']['closed_task_makespan_ticks'],eager_minus_greedy_decisions=table['eager']['cost']['decisions']-table['availability_greedy']['cost']['decisions'])
                costs[f'{status}_{seed}']=table
    report=dict(costs_by_condition=costs,initial_input_pairs=input_pairs,stage=stage,total=len(results),all_passed=all(r['passed'] for r in results),episodes=results,pairs=pairs,total_ticks=sum(r['contact_delivery']['total_ticks'] for r in results),
        freeze_sha256=sha(freeze),auditor_source_sha256=sha(ROOT/'experiments/responsive_transport_v16/audit.py'),canonical_physics_preserves_all_contact_fields=True,
        interpretation='规则/请求响应与真实机械贡献、成本核验；busy抽象资源状态，无人体离开/返回、神经或六结构覆盖声称。')
    save(RESULT/('control_audit.json' if stage=='controls' else 'reference_audit.json'),report);print(stage,'独立审计',len(results),report['all_passed'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('controls','reference'));main(p.parse_args().stage)
