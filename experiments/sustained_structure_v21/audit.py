"""独立全tick物理/服务重建；预期负面任务不能掩盖附带碰撞。"""
import argparse
import copy
import gzip
import json
import math
from experiments.physical.run import ROOT,save,sha
from experiments.structure_foundation_v20.audit_v2 import GROUPS,support,stable_region,CONFIG as GEOMETRY,TRANSPORT
from experiments.structure_foundation_v20.canonical import equal,digest
from experiments.sustained_structure_v21.run import RESULT,freeze_path,hashes
from experiments.sustained_structure_v21.service import InspectionService,CONFIG
from experiments.sustained_structure_v21.protocol import public_ledger,SYSTEM,candidates

SERVICE_EVENTS={'check_request_reply','check_commitment_suspended','check_commitment_withdrawn',
    'presence_far_observed','presence_return_started','presence_near_observed','partner_check_handoff'}


def classify(state,ids):
    found={name:[] for name in GROUPS};robot=ids['robot'];carrier=ids['carrier']
    inspection=ids['inspection'];presence=ids['presence'];objects=set(ids['objects'].values())
    for c in state['contacts']:
        pair={c['body_a'],c['body_b']}
        if pair=={ids['objects']['blue'],carrier}:found['expected_blue_carrier'].append(c)
        if pair=={ids['objects']['blue'],inspection}:found['expected_blue_inspection'].append(c)
        if pair=={robot,carrier}:found['forbidden_robot_carrier'].append(c)
        if carrier in pair and bool((pair-{carrier})&objects) and ids['objects']['blue'] not in pair:found['forbidden_other_object_carrier'].append(c)
        if carrier in pair and (pair-{carrier}).isdisjoint({robot,*objects}):found['forbidden_carrier_static'].append(c)
        if pair=={robot,inspection} or (robot in pair and bool(pair&set(ids['inspection_walls']))):found['forbidden_robot_inspection'].append(c)
        if inspection in pair and bool(pair&objects) and ids['objects']['blue'] not in pair:found['forbidden_other_object_inspection'].append(c)
        if presence in pair:found['forbidden_presence_contacts'].append(c)
        if len(pair&objects)==2:found['forbidden_object_object'].append(c)
        for item,body in ids['objects'].items():
            if pair=={robot,body}:found['expected_target_robot' if item==state['robot_target_item'] else 'forbidden_non_target_robot'].append(c)
            if body in pair and (pair-{body}).isdisjoint({robot,carrier,inspection,presence,*objects}):found['expected_objects_static_support'].append(c)
        if robot in pair and (pair-{robot}).isdisjoint({carrier,inspection,presence,*objects,*ids['inspection_walls']}):found['forbidden_robot_static'].append(c)
    return found


def independent_sample(state,ids):
    r,bs,rs,supported=support(state,ids,ids['inspection'],GEOMETRY['inspection_center'],[0,0,0])
    satisfied=math.hypot(*r[:2])<GEOMETRY['inspection_xy_tolerance_m'] and GEOMETRY['inspection_z_range_m'][0]<r[2]+GEOMETRY['inspection_center'][2]<GEOMETRY['inspection_z_range_m'][1] and bs<GEOMETRY['inspection_speed_m_s'] and supported
    contacts=[c for c in state['contacts'] if {c['body_a'],c['body_b']}=={ids['robot'],ids['objects']['blue']}]
    return dict(tick=state['tick'],inspection=dict(state['inspection_facts'],satisfied=bool(satisfied)),
        presence=state['presence'],presence_moving=state['presence_motion'] is not None,
        robot_blue_contact=bool(contacts),robot_blue_contacts=contacts)


def episode_audit(folder):
    summary=json.loads((folder/'summary.json').read_text());rows=json.loads((folder/'decisions.json').read_text());ids=summary['body_ids']
    groups={name:dict(records=0,ticks=0,max_normal_force=0.,negative_records=0) for name in GROUPS}
    evidence={};samples={tick:None for r in rows for tick in (r['before_tick'],r['after_tick'])}
    service_records=[]
    with gzip.open(folder/'service_ticks.jsonl.gz','rt') as stream:
        service_records=iter([json.loads(line) for line in stream])
    emitted=[];state_holder=[None]
    def replay_motion(destination):
        state=state_holder[0]
        return dict(start_tick=state['tick'],origin=state['presence']['joint'],
                    target=GEOMETRY['presence_'+destination+'_joint'],destination=destination)
    clause=next(e['clause'] for e in summary['public_history'] if e['kind']=='accepted_presence_clause')
    replay=InspectionService(clause,emitted.append,replay_motion)
    requests=[r for r in rows if r['choice']=='request_check'];request_index=0
    sample_checks=[];request_checks=[];total=missing=0;facts_match=True;event_match=True
    first_delivery=first_return=first_payload=None;forward_ticks=forward_supported=0;carrier_fk=presence_fk=0.
    previous=None;preserve_refs={};max_non_target_displacement=0.

    def apply_request(row):
        state_holder[0]=row['before_state'];reply=replay.request(independent_sample(row['before_state'],ids))
        request_checks.append(reply==row['result']['check_reply'])

    with gzip.open(folder/'ticks.jsonl.gz','rt') as stream:
        for line in stream:
            state=json.loads(line);total+=1;state_holder[0]=state
            if state['tick'] in samples:samples[state['tick']]=state
            found=classify(state,ids)
            missing+=sum('contact_distance' not in c or 'position_a' not in c or 'position_b' not in c for c in state['contacts'])
            for name,contacts in found.items():
                group=groups[name];group['records']+=len(contacts);group['ticks']+=int(bool(contacts))
                group['max_normal_force']=max([group['max_normal_force']]+[c['normal_force'] for c in contacts])
                group['negative_records']+=sum(c['contact_distance']<-1e-6 for c in contacts)
                if name.startswith('forbidden') and contacts:
                    ev=evidence.setdefault(name,{})
                    if 'first' not in ev:ev['first']=dict(tick=state['tick'],contacts=copy.deepcopy(contacts),state=copy.deepcopy(state))
                    if any(c['contact_distance']<-1e-6 for c in contacts) and 'first_negative' not in ev:
                        ev['first_negative']=dict(tick=state['tick'],contacts=copy.deepcopy(contacts),state=copy.deepcopy(state))
                    peak=max(contacts,key=lambda c:c['normal_force'])
                    if 'peak' not in ev or peak['normal_force']>ev['peak']['contact']['normal_force']:
                        ev['peak']=dict(tick=state['tick'],contact=copy.deepcopy(peak),state=copy.deepcopy(state))
            carrier_fk=max(carrier_fk,abs(state['partner_position'][1]-state['partner_joint']))
            if state['presence'] is not None:presence_fk=max(presence_fk,abs(state['presence']['position'][1]-state['presence']['joint']))
            r,bs,rs,supported=support(state,ids,ids['carrier'],[.65,state['partner_joint'],TRANSPORT['carrier_center_start'][2]],[0,state['partner_velocity'],0])
            delivered=state['delivery_start_tick'] is not None and abs(state['partner_joint'])<TRANSPORT['carrier_goal_joint_tolerance'] and abs(state['partner_velocity'])<TRANSPORT['carrier_speed_limit'] and math.hypot(*r[:2])<TRANSPORT['blue_relative_xy_tolerance'] and TRANSPORT['blue_relative_z_range'][0]<r[2]<TRANSPORT['blue_relative_z_range'][1] and bs<TRANSPORT['blue_world_speed_limit'] and rs<TRANSPORT['blue_relative_speed_limit'] and supported
            facts_match&=bool(delivered)==state['delivery_facts']['satisfied']
            if state['delivery_start_tick'] is not None and first_delivery is None:forward_ticks+=1;forward_supported+=int(supported)
            if delivered and first_delivery is None:first_delivery=state['tick']
            event_match&=(state['delivery_event'] is None if first_delivery is None else state['delivery_event']['first_tick']==first_delivery)
            if state['return_start_tick'] is not None:
                returned=abs(state['partner_joint']-TRANSPORT['travel_m'])<GEOMETRY['position_tolerance_m'] and abs(state['partner_velocity'])<GEOMETRY['stable_speed_m_s']
                payload=returned and supported and math.hypot(*r[:2])<TRANSPORT['blue_relative_xy_tolerance'] and TRANSPORT['blue_relative_z_range'][0]<r[2]<TRANSPORT['blue_relative_z_range'][1] and rs<TRANSPORT['blue_relative_speed_limit'] and bs<TRANSPORT['blue_world_speed_limit']
                facts_match&=bool(returned)==state['return_facts']['carrier_returned'] and bool(payload)==state['return_facts']['payload_returned']
                if returned and first_return is None:first_return=state['tick']
                if payload and first_payload is None:first_payload=state['tick']
                event_match&=(state['return_event'] is None if first_return is None else state['return_event']['first_tick']==first_return)
                event_match&=(state['payload_return_event'] is None if first_payload is None else state['payload_return_event']['first_tick']==first_payload)
            if state['tick']>summary['common_start_tick']:
                while request_index<len(requests) and requests[request_index]['before_tick']<state['tick']:
                    apply_request(requests[request_index]);request_index+=1
                state_holder[0]=state;actual=independent_sample(state,ids)
                recorded=next(service_records)
                rebuilt=replay.step(actual)
                sample_checks.append(recorded['facts']==actual and recorded['sample_qualified']==rebuilt['sample_qualified'] and recorded['service']==rebuilt['service'])
                facts_match&=actual['inspection']['satisfied']==state['inspection_facts']['satisfied']
                for item in ids['objects']:
                    autonomous_blue=item=='blue' and (first_delivery is None or state['return_start_tick'] is not None)
                    if previous is not None and item!=state['robot_target_item'] and not autonomous_blue:
                        if item not in preserve_refs:preserve_refs[item]=previous['objects'][item]['position']
                        max_non_target_displacement=max(max_non_target_displacement,math.dist(state['objects'][item]['position'],preserve_refs[item]))
                    else:preserve_refs.pop(item,None)
            previous=state;final=state
    while request_index<len(requests):apply_request(requests[request_index]);request_index+=1
    try:next(service_records);service_exhausted=False
    except StopIteration:service_exhausted=True
    recorded_service_events=[{k:v for k,v in e.items() if k not in ('event_sequence','observed_tick')}
                             for e in summary['public_history'] if e['kind'] in SERVICE_EVENTS]
    message_checks=[];previous_history=None
    for row in rows:
        observation=row['observation'];actual=samples[row['before_tick']]
        check=dict(before_actual=equal(row['before_state'],actual),after_actual=equal(row['after_state'],samples[row['after_tick']]),
            history_exact=observation['history']==row['history_before'],previous_history_immutable=previous_history is None or row['history_before']==previous_history,
            messages_exact=row['messages']==[dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(observation,ensure_ascii=False))],
            menu_same_11=observation['candidates']==candidates(),budget=observation['remaining_decisions']==32-row['sequence'],
            actual_objects=observation['physical']['objects']==actual['objects'],
            no_private_goal_or_score=not any(k in observation for k in ('case','score','current_goals','child_active','future_schedule')),
            events_not_future=all(e['actual_tick']<=e['observed_tick']<=row['before_tick'] for e in observation['history']),
            event_sequence=all(e['event_sequence']==i for i,e in enumerate(observation['history'])),
            no_goal_feedback=not any(text in row['result']['feedback'] for text in ('应到','正确目标','遗漏')))
        previous_history=row['history_after'];message_checks.append(dict(sequence=row['sequence'],passed=all(check.values()),checks=check))
    ledger=public_ledger(summary['public_history']);role=ledger['blue_role']
    facts=dict(red_actual_left=stable_region(final,'red','left'),green_actual_right=stable_region(final,'green','right'),
        check_contribution_completed=not ledger['inspection_required'] or replay.completed,no_active_child=not ledger['child_active'],
        carrier_return_completed=not ledger['carrier_return_required'] or first_return is not None,
        blue_role_completed=(first_payload is not None and final['return_facts']['payload_returned']) if role=='partner_return' else stable_region(final,'blue',ledger['goals']['blue']))
    actual_success=all(facts.values()) and summary['termination_reason']=='declared_done'
    safe=all(group['records']==0 for name,group in groups.items() if name.startswith('forbidden'))
    checks=dict(physical_snapshots_messages_all=all(r['passed'] for r in message_checks),contact_fields_complete=missing==0,
        full_physics_canonical=digest(folder/'ticks.jsonl.gz')==summary['canonical_physics'],final_physics_exact=equal(final,summary['final_state']),
        service_samples_all=all(sample_checks),service_trace_count=len(sample_checks)==summary['end_tick']-summary['common_start_tick'] and service_exhausted,
        service_requests_all=all(request_checks),service_events_exact=recorded_service_events==emitted,service_final_exact=summary['service']==replay.snapshot(),
        facts_recomputed=facts_match,event_actual_times=event_match,forward_support=forward_ticks==forward_supported,
        carrier_same_tick_FK=carrier_fk<1e-6,presence_same_tick_FK=presence_fk<1e-6,
        terminal_score_exact=summary['terminal_score']==dict(facts=facts,task_compliant=all(facts.values()),declared_task_success=actual_success),
        after_terminal_immutable=summary['after_terminal_immutable'],no_infrastructure_failure=summary['infrastructure_failure'] is None,
        expected_task_outcome=actual_success==summary['expected_task_success'],all_forbidden_contacts_zero=safe,
        non_target_interval_preserved=max_non_target_displacement<CONFIG['non_target_interval_displacement_limit_m'])
    control=summary['case'].get('control');cp=summary['checkpoints']
    if control==0:
        p=cp['early_no_queue'];checks['early_reject_no_queue']=p['reply']['decision']=='rejected' and p['service']['qualified_ticks']==p['service']['acceptances']==0 and p['transport_start_tick'] is None
    elif control==1:
        p=cp['duplicate'];checks['duplicate_no_restart']=p['reply']['decision']=='already_committed' and p['before']['qualified_ticks']==p['after']['qualified_ticks'] and p['before']['acceptances']==p['after']['acceptances'] and p['tick_before']==p['tick_after']
    elif control==2:
        p=cp['off_table_after_return'];checks['off_table_pauses_after_return']=p['before']['qualified_ticks']==p['after']['qualified_ticks']==60 and not p['physical']['inspection_facts']['satisfied'] and p['physical']['presence']['near'] and replay.completed
    elif control==3:
        p=cp['withdraw_no_restart'];checks['withdraw_no_auto_restart']=p['before']['qualified_ticks']==p['after']['qualified_ticks']==60 and not p['after']['committed'] and p['physical']['presence']['near'] and replay.acceptances==2 and replay.completed
    elif control in (6,7):
        checks['isolated_blue_role_failure']=facts['red_actual_left'] and facts['green_actual_right'] and not facts['blue_role_completed'] and first_return is not None
        checks['payload_role_counterexample']=first_payload is None if control==6 else first_payload is not None
    return dict(id=summary['case']['id'],case=summary['case'],checks=checks,passed=all(checks.values()),
        task_success=actual_success,physically_safe=safe,actual_facts=facts,input_checks=message_checks,
        groups=groups,total_ticks=total,service_ticks=len(sample_checks),qualified_ticks=replay.qualified_ticks,
        forward_ticks=forward_ticks,forward_supported_ticks=forward_supported,first_delivery=first_delivery,first_return=first_return,first_payload_return=first_payload,
        max_non_target_interval_displacement_m=max_non_target_displacement,makespan_ticks=summary['makespan_ticks'],cost=summary['cost'],
        actual_contribution_events=dict(check_completed=replay.completed,carrier_returned=first_return is not None,payload_returned=first_payload is not None),
        obligation_flags=dict(inspection_required=ledger['inspection_required'],carrier_return_required=ledger['carrier_return_required'],blue_role=role),
        vacuous_obligation_satisfaction=dict(check=not ledger['inspection_required'],carrier_return=not ledger['carrier_return_required']),
        first_peak_contact_evidence=evidence)


def audit(stage):
    f=json.loads(freeze_path(stage).read_text());assert f['source_sha256']==hashes()
    reports=[]
    for case in f['cases']:
        report=episode_audit(RESULT/'raw'/stage/case['id']);reports.append(report)
        print(case['id'],report['passed'],report['task_success'],[k for k,v in report['checks'].items() if not v],flush=True)
    result=dict(stage=stage,total=len(reports),passed=sum(r['passed'] for r in reports),
        task_success=sum(r['task_success'] for r in reports),physically_safe=sum(r['physically_safe'] for r in reports),
        all_controls_evidence_and_safety_pass=all(r['passed'] for r in reports),total_ticks=sum(r['total_ticks'] for r in reports),
        episodes=reports,freeze_sha256=sha(freeze_path(stage)),runtime_source_sha256=hashes(),
        audit_source_sha256=sha(ROOT/'experiments/sustained_structure_v21/audit.py'))
    save(RESULT/f'{stage}_audit_dev0.json',result)
    assert result['all_controls_evidence_and_safety_pass'];print('独立审计完成',stage,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('C','N','H'));audit(parser.parse_args().stage)
