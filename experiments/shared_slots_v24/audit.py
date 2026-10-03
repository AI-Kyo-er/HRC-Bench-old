"""全tick独立载台/来源目的支撑/非目标/共盘恢复审计；不重跑物理。"""
import copy
import gzip
import hashlib
import json
import math
from experiments.physical.run import ROOT,save,sha
from experiments.shared_slots_v24.run import RESULT,FREEZE,CONFIG,PREFIX,MENU,SYSTEM,WORKSPACE,hashes,waiting_satisfied
from experiments.transport_cycle_v22.cycle import CycleLedger
from experiments.transport_cycle_v22.audit import independent_facts,command
from experiments.transport_cycle_v22.canonical import physics,equal,content_equal
from experiments.sustained_structure_v21.audit import classify,independent_sample
from experiments.structure_foundation_v20.audit_v2 import GROUPS,stable_region


def supported_by(state,body,support_body):
    contacts=[c for c in state['contacts'] if {c['body_a'],c['body_b']}=={body,support_body}]
    return any(c['contact_distance']<=CONFIG['support_contact_max_distance_m'] and c['normal_force']>CONFIG['support_contact_min_force_n'] for c in contacts)


def destination_facts(state,item,target,ids):
    if target=='inspection':
        return dict(stable=independent_sample(state,ids)['inspection']['satisfied'],supported=supported_by(state,ids['objects'][item],ids['inspection']))
    return dict(stable=stable_region(state,item,target),supported=supported_by(state,ids['objects'][item],ids['trays'][target]))


def recovery_exposed(case,placements):
    tail=[r for r in placements if r['sequence']>=len(PREFIX)]
    commands=CONFIG['sequences'][case['sequence']]
    if [r['choice'] for r in tail]!=commands or not all(r['actual_destination'] for r in tail):return False
    if case['sequence'] in ('C','D'):
        item='green' if case['sequence']=='C' else 'blue'
        selected=[r for r in tail if r['item']==item]
        return [r['target'] for r in selected]==['left','right','left'] and all(r['physical_attempt'] and r['source_displacement_m']>.35 for r in selected[1:])
    return True


def preserved_within(displacements):
    return all(d<CONFIG['non_target_interval_limit_m'] for d in displacements.values())


def audit_episode(folder):
    summary=json.loads((folder/'summary.json').read_text());rows=json.loads((folder/'decisions.json').read_text());ids=summary['body_ids'];cycle=CycleLedger()
    requests=[r for r in rows if r['choice'] in ('request_forward','request_return')];ri=0
    boundaries={t:None for r in rows for t in (r['before_tick'],r['after_tick'])}
    groups={g:dict(records=0,ticks=0,max_normal_force=0,negative_distance_records=0,near_zero_distance_records=0,positive_distance_records=0) for g in GROUPS}
    evidence={};leg_support={};requests_ok=events_ok=facts_ok=True;total=missing=0;prev_command=.6;command_err=fk_err=presence_fk_err=0.
    h=hashlib.sha256();prefix_h=hashlib.sha256();prefix_count=0;refs={};non_target_max=0.;final=None;presence_ok=True;post_far=True
    prefix_tick=summary['prefix_checkpoint']['tick'] if summary['prefix_checkpoint'] else None
    skill_rows=[r for r in rows if r['result'].get('physical_attempt')]
    segments={r['sequence']:{i:0. for i in ids['objects'] if i!=r['choice'].split('_')[1]} for r in skill_rows}
    with gzip.open(folder/'ticks.jsonl.gz','rt') as stream:
        for line in stream:
            state=json.loads(line);total+=1;encoded=json.dumps(physics(state),sort_keys=True,separators=(',',':')).encode();h.update(encoded)
            if prefix_tick is not None and state['tick']<=prefix_tick:prefix_h.update(encoded);prefix_count+=1
            if state['tick'] in boundaries:boundaries[state['tick']]=state
            while ri<len(requests) and requests[ri]['before_tick']<state['tick']:
                row=requests[ri];response=cycle.request(row['choice'].split('_')[-1],independent_facts(row['before_state'],ids,cycle));requests_ok&=content_equal(response,row['result']);ri+=1
            leg=cycle.legs[cycle.active-1] if cycle.active is not None else None
            expected=command(leg,state['tick'],prev_command);command_err=max(command_err,abs(expected-state['partner_command']));prev_command=expected
            cf=independent_facts(state,ids,cycle)
            if leg:
                counts=leg_support.setdefault(str(leg['id']),dict(ticks=0,supported_ticks=0,loaded=leg['loaded_at_start']))
                counts['ticks']+=1;counts['supported_ticks']+=int(cf['supported'])
            cycle.sample(cf);events_ok&=content_equal(cycle.snapshot(),state['cycle'])
            rebuilt=independent_facts(state,ids,cycle);stored=state['current_carrier_facts']
            facts_ok&=all(math.isclose(rebuilt[k],stored[k],rel_tol=0,abs_tol=1e-12) if isinstance(rebuilt[k],float) else content_equal(rebuilt[k],stored[k]) for k in rebuilt)
            fk_err=max(fk_err,abs(state['partner_position'][1]-state['partner_joint']))
            pf=state['presence']
            if pf is not None:
                presence_fk_err=max(presence_fk_err,abs(pf['position'][1]-pf['joint']))
                presence_ok&=state['presence_motion'] is None and not state['presence_events'] and pf['target']==.45 and pf['near']==(abs(pf['joint']-.45)<.005 and abs(pf['velocity'])<.005)
            found=classify(state,ids);missing+=sum(any(k not in c for k in ('position_a','position_b','contact_distance','normal_force')) for c in state['contacts'])
            for g,contacts in found.items():
                stat=groups[g];stat['records']+=len(contacts);stat['ticks']+=int(bool(contacts))
                for c in contacts:
                    d=c['contact_distance'];stat['negative_distance_records' if d<-1e-6 else 'positive_distance_records' if d>1e-6 else 'near_zero_distance_records']+=1
                    if g.startswith('forbidden'):
                        ev=evidence.setdefault(g,{})
                        if 'first' not in ev:ev['first']=dict(tick=state['tick'],contact=c,state=state)
                        if c['normal_force']>stat['max_normal_force']:ev['peak']=dict(tick=state['tick'],contact=c,state=state)
                    stat['max_normal_force']=max(stat['max_normal_force'],c['normal_force'])
            if state['tick']>summary['common_start_tick']:
                for item in ids['objects']:
                    autonomous=item=='blue' and leg is not None and leg['loaded_at_start']
                    if item==state['robot_target_item'] or autonomous:refs.pop(item,None)
                    else:
                        refs.setdefault(item,state['objects'][item]['position']);non_target_max=max(non_target_max,math.dist(refs[item],state['objects'][item]['position']))
                for row in skill_rows:
                    if row['before_tick']<state['tick']<=row['after_tick']:
                        for item in segments[row['sequence']]:
                            if item=='blue' and leg is not None and leg['loaded_at_start']:continue
                            segments[row['sequence']][item]=max(segments[row['sequence']][item],math.dist(row['before_state']['objects'][item]['position'],state['objects'][item]['position']))
            if prefix_tick is not None and state['tick']>=prefix_tick:
                post_far&=cf['far'] and cycle.active is None
            final=state
    placements=[];inputs=[];sequence_checks=[]
    for row in rows:
        obs=row['observation'];before=row['before_state'];after=row['after_state'];result=row['result']
        checks=dict(before_physics=equal(before,boundaries[row['before_tick']]),after_physics=equal(after,boundaries[row['after_tick']]),
            observation_physics=content_equal(obs['physical'],before),history=content_equal(obs['history'],before['cycle']),menu=obs['menu']==MENU,workspace=obs['workspace']==WORKSPACE,
            messages=row['messages']==[dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(obs,ensure_ascii=False))],
            no_private_task=not any(k in obs for k in ('score','goals','case','completed','current_goal')))
        inputs.append(dict(sequence=row['sequence'],checks=checks,passed=all(checks.values())))
        if row['choice'].startswith('wait_'):
            sequence_checks.append(bool(result['success'] and waiting_satisfied(after,row['choice']) and 0<=result['wait_ticks']<=CONFIG['wait_limit_ticks']))
        if result.get('physical_attempt'):
            _,item,target=row['choice'].split('_');dest=destination_facts(after,item,target,ids)
            item_displacement=math.dist(before['objects'][item]['position'],after['objects'][item]['position'])
            preserved=preserved_within(segments[row['sequence']])
            placements.append(dict(sequence=row['sequence'],choice=row['choice'],item=item,target=target,physical_attempt=True,
                destination=dest,actual_destination=all(dest.values()),finger_contacts=result.get('finger_contacts',0),lifted_z=result.get('lifted_z'),
                source_displacement_m=item_displacement,non_target_displacements_m=segments[row['sequence']],non_target_preserved=preserved,
                passed=bool(all(dest.values()) and result['success'] and result.get('finger_contacts',0)>0 and result.get('lifted_z',0)>.12 and preserved)))
    safe=all(v['records']==0 for k,v in groups.items() if k.startswith('forbidden'))
    final_dest={item:destination_facts(final,item,'left',ids) for item in ids['objects']}
    checks=dict(source_unchanged=json.loads(FREEZE.read_text())['source_sha256']==hashes(),no_runtime_failure=summary['failure'] is None,
        sequence_exact=[r['choice'] for r in rows]==summary['case']['commands'],sequence_completed=summary['control_sequence_completed'],
        all_inputs=all(x['passed'] for x in inputs),all_actual_grasps=all(x['passed'] for x in placements),actual_wait_conditions=all(sequence_checks),
        requests_exact=requests_ok and ri==len(requests),events_recomputed=events_ok,current_facts_recomputed=facts_ok,
        legs_forward_loaded_return_empty=[l['direction'] for l in cycle.legs]==['forward','return'] and [l['loaded_at_start'] for l in cycle.legs]==[True,False],
        payload_events_separate=[l['payload_event'] is not None for l in cycle.legs]==[True,False],all_carrier_arrivals=all(l['completed_tick'] is not None and l['carrier_event'] is not None for l in cycle.legs),
        final_cycle_exact=content_equal(cycle.snapshot(),summary['cycle']),carrier_profile=command_err<1e-12,carrier_FK=fk_err<1e-6,presence_stays_near=presence_ok,presence_FK=presence_fk_err<1e-6,
        prefix_current_far_empty=prefix_tick is not None and waiting_satisfied(summary['prefix_checkpoint'],'wait_far_empty') and not summary['prefix_checkpoint']['current_carrier_facts']['payload_stable'],
        carrier_remains_far=post_far,recovery_actual=recovery_exposed(summary['case'],placements),final_all_left_supported=all(all(v.values()) for v in final_dest.values()),
        contact_fields_complete=missing==0,forbidden_zero=safe,non_target_continuous=non_target_max<CONFIG['non_target_interval_limit_m'],
        loaded_support_all=all(v['ticks']==v['supported_ticks'] for v in leg_support.values() if v['loaded']),
        canonical_exact=dict(sha256=h.hexdigest(),ticks=total)==summary['canonical_physics'],final_physics_exact=equal(final,summary['final_state']),no_check_service=summary['no_check_service'])
    return dict(id=summary['case']['id'],passed=all(checks.values()),physically_safe=safe,checks=checks,total_ticks=total,makespan_ticks=summary['makespan_ticks'],cost=summary['cost'],
        groups=groups,contact_evidence=evidence,leg_support=leg_support,legs=cycle.legs,events=cycle.events,placements=placements,input_checks=inputs,
        prefix_physics=dict(tick=prefix_tick,ticks=prefix_count,sha256=prefix_h.hexdigest()),final_destinations=final_dest,
        max_non_target_interval_displacement_m=non_target_max,profile_error=command_err,FK_errors=dict(carrier=fk_err,presence=presence_fk_err),no_task_success_claim=True)


def audit():
    assert json.loads(FREEZE.read_text())['source_sha256']==hashes();reports=[]
    copies=RESULT/'raw'/'audit_sources';copies.mkdir(parents=True,exist_ok=True)
    (copies/'audit.py').write_bytes(Path(__file__).read_bytes())
    for case in json.loads(FREEZE.read_text())['cases']:
        report=audit_episode(RESULT/'raw'/'dev0'/case['id']);reports.append(report);print(report['id'],report['passed'],[k for k,v in report['checks'].items() if not v],flush=True)
    result=dict(total=len(reports),passed=sum(r['passed'] for r in reports),physically_safe=sum(r['physically_safe'] for r in reports),total_ticks=sum(r['total_ticks'] for r in reports),
        episodes=reports,freeze_sha256=sha(FREEZE),runtime_source_sha256=hashes(),audit_source_sha256=sha(ROOT/'experiments/shared_slots_v24/audit.py'))
    save(RESULT/'control_audit_dev0.json',result);print('独立审计',result['passed'],'/8',flush=True);assert result['passed']==8


from pathlib import Path
if __name__=='__main__':audit()
