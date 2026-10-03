"""独立实际事实/profile/循环请求事件/全接触与输入审计；不重跑物理。"""
import argparse
import copy
import gzip
import hashlib
import json
import math
from experiments.physical.run import ROOT,save,sha
from experiments.transport_cycle_v22.run import RESULT,FREEZE,hashes,WORKSPACE,MENU
from experiments.transport_cycle_v22.world import CONFIG,TRANSPORT,GEOMETRY,DT
from experiments.transport_cycle_v22.cycle import CycleLedger
from experiments.transport_cycle_v22.canonical import physics,equal,content_equal
from experiments.structure_foundation_v20.audit_v2 import support,stable_region,GROUPS
from experiments.sustained_structure_v21.audit import classify


def independent_facts(s,ids,ledger):
    q=s['partner_joint'];v=s['partner_velocity']
    r,bs,rs,supported=support(s,ids,ids['carrier'],[.65,q,.045],[0,v,0])
    contacts=[c for c in s['contacts'] if {c['body_a'],c['body_b']}=={ids['objects']['blue'],ids['carrier']}]
    leg=ledger.legs[ledger.active-1] if ledger.active is not None else None
    finished=leg is None or (s['tick']-leg['start_tick'])*DT>=abs(leg['target']-leg['origin'])/.04+.5
    return dict(tick=s['tick'],joint=q,velocity=v,profile_finished=finished,
        near=abs(q)<.005 and abs(v)<.005,far=abs(q-.6)<.005 and abs(v)<.005,
        payload_stable=bool(supported and math.hypot(*r[:2])<.025 and .025<r[2]<.035 and rs<.01 and bs<.01),
        relative_position=r,relative_speed=rs,blue_speed=bs,supported=supported,support_records=len(contacts),
        min_distance=min((c['contact_distance'] for c in contacts),default=None),support_force=sum(c['normal_force'] for c in contacts))


def command(leg,tick,previous):
    if leg is None:return previous
    travel=abs(leg['target']-leg['origin']);t=max(0,(tick-leg['start_tick'])*DT);duration=travel/.04+.5
    if t<.5:d=.04*t*t
    elif t<duration-.5:d=.04*(t-.25)
    elif t<duration:d=travel-.04*(duration-t)**2
    else:d=travel
    return leg['origin']+(1 if leg['target']>leg['origin'] else -1)*d


def audit_episode(folder):
    summary=json.loads((folder/'summary.json').read_text());rows=json.loads((folder/'decisions.json').read_text());ids=summary['body_ids']
    ledger=CycleLedger();request_rows=[r for r in rows if r['choice'] in ('request_forward','request_return')];ri=0
    boundaries={t:None for r in rows for t in (r['before_tick'],r['after_tick'])}
    groups={g:dict(records=0,ticks=0,max_normal_force=0,negative_distance_records=0) for g in GROUPS}
    first_peak={};missing=total=0;events_match=facts_match=requests_match=legacy_match=True
    legs_support={};command_max=fk_max=0.;previous_command=.6;refs={};non_target_max=0.;initial_green=summary['initial_state']['objects']['green']['position'];green_max=0.
    h=hashlib.sha256();final=None
    with gzip.open(folder/'ticks.jsonl.gz','rt') as stream:
        for line in stream:
            s=json.loads(line);total+=1
            h.update(json.dumps(physics(s),sort_keys=True,separators=(',',':')).encode())
            if s['tick'] in boundaries:boundaries[s['tick']]=s
            while ri<len(request_rows) and request_rows[ri]['before_tick']<s['tick']:
                row=request_rows[ri];f=independent_facts(row['before_state'],ids,ledger)
                reply=ledger.request(row['choice'].split('_')[1],f);requests_match&=content_equal(reply,row['result']);ri+=1
            leg=ledger.legs[ledger.active-1] if ledger.active is not None else None
            expected_command=command(leg,s['tick'],previous_command);command_max=max(command_max,abs(expected_command-s['partner_command']));previous_command=expected_command
            facts=independent_facts(s,ids,ledger)
            if leg is not None:
                counts=legs_support.setdefault(str(leg['id']),dict(ticks=0,supported_ticks=0,loaded=leg['loaded_at_start']))
                counts['ticks']+=1;counts['supported_ticks']+=int(facts['supported'])
            ledger.sample(facts);events_match&=content_equal(ledger.snapshot(),s['cycle'])
            recomputed=independent_facts(s,ids,ledger);stored=s['current_carrier_facts']
            facts_match&=all((math.isclose(recomputed[k],stored[k],rel_tol=0,abs_tol=1e-12) if isinstance(recomputed[k],float) else content_equal(recomputed[k],stored[k])) for k in recomputed)
            for field,direction,kind in (('delivery_event','forward','payload_event'),('return_event','return','carrier_event'),('payload_return_event','return','payload_event')):
                stored=next((l[kind] for l in ledger.legs if l['direction']==direction and l[kind] is not None),None)
                legacy_match&=(s[field] is None if stored is None else s[field]['first_tick']==stored['first_tick'] and s[field]['leg_id']==stored['leg_id'])
            fk_max=max(fk_max,abs(s['partner_position'][1]-s['partner_joint']))
            found=classify(s,ids)
            for g,contacts in found.items():
                stats=groups[g];stats['records']+=len(contacts);stats['ticks']+=int(bool(contacts))
                for c in contacts:
                    missing+=int('position_b' not in c or 'contact_distance' not in c)
                    stats['negative_distance_records']+=int(c['contact_distance']<-1e-6)
                    if g not in first_peak:first_peak[g]=dict(first_tick=s['tick'],first_contact=c,first_state=s,peak_contact=c,peak_tick=s['tick'])
                    if c['normal_force']>stats['max_normal_force']:
                        first_peak[g]['peak_contact']=c;first_peak[g]['peak_tick']=s['tick']
                    stats['max_normal_force']=max(stats['max_normal_force'],c['normal_force'])
            if s['tick']>summary['common_start_tick']:
                green_max=max(green_max,math.dist(initial_green,s['objects']['green']['position']))
                for item in ('red','blue','green'):
                    transported=item=='blue' and leg is not None and leg['loaded_at_start']
                    if item==s['robot_target_item'] or transported:refs.pop(item,None)
                    else:
                        refs.setdefault(item,s['objects'][item]['position']);non_target_max=max(non_target_max,math.dist(refs[item],s['objects'][item]['position']))
            final=s
    # 请求在控制边界零tick发生；原序列末端没有额外请求。逐序处理不按tick去重。
    input_checks=[];placements=[]
    for row in rows:
        before=boundaries[row['before_tick']];after=boundaries[row['after_tick']]
        obs=row['observation'];message_user=json.loads(row['messages'][1]['content'])
        check=dict(before_physics=equal(before,row['before_state']),after_physics=equal(after,row['after_state']),
            observation_state_exact=content_equal(obs['physical'],row['before_state']),observation_history_exact=content_equal(obs['history'],row['before_state']['cycle']),
            observation_workspace=obs['workspace']==WORKSPACE,observation_menu=obs['menu']==MENU,messages_exact=content_equal(obs,message_user))
        input_checks.append(dict(sequence=row['sequence'],checks=check,passed=all(check.values())))
        if row['choice'].startswith('place_blue_') or row['choice']=='reload_blue' or row['choice']=='careful_red_left':
            item='red' if row['choice']=='careful_red_left' else 'blue';destination='carrier' if row['choice']=='reload_blue' else row['choice'].split('_')[-1]
            result=row['result'];facts=independent_facts(after,ids,CycleLedger())
            if destination=='carrier':actual=facts['near'] and facts['payload_stable']
            elif destination=='inspection':
                r,bs,rs,ss=support(after,ids,ids['inspection'],GEOMETRY['inspection_center'],[0,0,0])
                actual=ss and math.hypot(*r[:2])<.035 and .025<after['objects']['blue']['position'][2]<.055 and bs<.04
            else:actual=stable_region(after,item,destination)
            placements.append(dict(sequence=row['sequence'],choice=row['choice'],actual_destination_met=bool(actual),
                physical_attempt=result.get('physical_attempt',False),finger_contacts=result.get('finger_contacts',0),lifted_z=result.get('lifted_z'),
                passed=bool(actual and result.get('success') and result.get('physical_attempt') and result.get('finger_contacts',0)>0 and result.get('lifted_z',0)>.12)))
    expected_loaded=[True,True,True] if summary['case']['family']=='A' else [True,False,False,True]
    expected_directions=['forward','return','forward'] if summary['case']['family']=='A' else ['forward','return','forward','return']
    safe=all(v['records']==0 for k,v in groups.items() if k.startswith('forbidden'))
    checks=dict(source_freeze_unchanged=json.loads(FREEZE.read_text())['source_sha256']==hashes(),no_runtime_failure=summary['failure'] is None,
        original_sequence_completed=summary['control_sequence_completed'],all_inputs_physics_exact=all(r['passed'] for r in input_checks),
        all_grasp_places_actual=all(r['passed'] for r in placements),requests_exact=requests_match and ri==len(request_rows),cycle_events_exact=events_match,
        current_carrier_facts_recomputed=facts_match,legacy_first_events_retained=legacy_match,same_tick_FK=fk_max<1e-6,command_profile_exact=command_max<1e-12,
        full_canonical=dict(sha256=h.hexdigest(),ticks=total)==summary['canonical_physics'],final_physics_exact=equal(final,summary['final_state']),final_ledger_exact=content_equal(ledger.snapshot(),summary['cycle']),
        leg_ids=[l['id'] for l in ledger.legs]==list(range(1,len(expected_loaded)+1)),directions=[l['direction'] for l in ledger.legs]==expected_directions,
        loaded_at_start=[l['loaded_at_start'] for l in ledger.legs]==expected_loaded,payload_events=[l['payload_event'] is not None for l in ledger.legs]==expected_loaded,
        all_actual_arrivals=all(l['carrier_event'] is not None and l['completed_tick'] is not None for l in ledger.legs),contact_fields_complete=missing==0,
        forbidden_contacts_zero=safe,loaded_support_all=all(s['ticks']==s['supported_ticks'] for s in legs_support.values() if s['loaded']),
        non_target_preserved=non_target_max<CONFIG['non_target_interval_limit_m'],green_preserved=green_max<CONFIG['non_target_interval_limit_m'])
    return dict(id=summary['case']['id'],passed=all(checks.values()),physically_safe=safe,checks=checks,total_ticks=total,makespan_ticks=summary['makespan_ticks'],
        cost=summary['cost'],groups=groups,contact_evidence={g:v for g,v in first_peak.items() if g.startswith('forbidden')},leg_support=legs_support,
        events=ledger.events,legs=ledger.legs,input_checks=input_checks,placements=placements,green_max_displacement_m=green_max,
        max_non_target_interval_displacement_m=non_target_max,profile_command_max_error=command_max,carrier_FK_max_error=fk_max)


def audit():
    f=json.loads(FREEZE.read_text());assert f['source_sha256']==hashes();reports=[]
    for case in f['cases']:
        r=audit_episode(RESULT/'raw'/'dev0'/case['id']);reports.append(r)
        print(r['id'],r['passed'],[k for k,v in r['checks'].items() if not v],flush=True)
    result=dict(total=len(reports),passed=sum(r['passed'] for r in reports),physically_safe=sum(r['physically_safe'] for r in reports),
        total_ticks=sum(r['total_ticks'] for r in reports),episodes=reports,freeze_sha256=sha(FREEZE),runtime_source_sha256=hashes(),audit_source_sha256=sha(ROOT/'experiments/transport_cycle_v22/audit.py'))
    save(RESULT/'control_audit_dev0.json',result);assert result['passed']==8;print('独立审计通过8',flush=True)


if __name__=='__main__':audit()
