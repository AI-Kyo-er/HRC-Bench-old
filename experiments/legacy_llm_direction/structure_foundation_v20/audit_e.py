"""独立全tick新body/contact/支持/事件复算，不改运行或评分。"""
import argparse
import gzip
import json
import math
from experiments.physical.run import ROOT,save,sha
from experiments.structure_foundation_v20.run_e import RESULT,freeze_path,hashes
from experiments.structure_foundation_v20.world_v1 import CONFIG,TRANSPORT
from experiments.structure_foundation_v20.canonical import equal,digest

GROUPS=('expected_blue_carrier','expected_blue_inspection','expected_target_robot','expected_objects_static_support',
    'forbidden_robot_carrier','forbidden_other_object_carrier','forbidden_carrier_static','forbidden_robot_inspection','forbidden_other_object_inspection',
    'forbidden_presence_contacts','forbidden_non_target_robot','forbidden_robot_static','forbidden_object_object')

def stable_region(state,item,goal):
    obj=state['objects'][item];pos=obj['position'];speed=math.sqrt(sum(v*v for v in obj['velocity']))
    target=[.59+.06*('red','blue','green').index(item),-.25 if goal=='left' else .25]
    return math.dist(pos[:2],target)<.035 and .025<pos[2]<.055 and speed<.04

def support(state,ids,body,centre,velocity):
    blue=state['objects']['blue'];r=[a-b for a,b in zip(blue['position'],centre)];relv=[a-b for a,b in zip(blue['velocity'],velocity)]
    contacts=[c for c in state['contacts'] if {c['body_a'],c['body_b']}=={ids['objects']['blue'],body}]
    supported=any(c['contact_distance']<=CONFIG['support_contact_max_distance_m'] and c['normal_force']>CONFIG['support_contact_min_force_n'] for c in contacts)
    return r,math.sqrt(sum(v*v for v in blue['velocity'])),math.sqrt(sum(v*v for v in relv)),supported

def audit(stage):
    f=json.loads(freeze_path(stage).read_text());assert f['source_sha256']==hashes();episodes=[]
    for case in f['cases']:
        folder=RESULT/'raw'/(stage+'_dev1')/case['id'];summary=json.loads((folder/'summary.json').read_text());rows=json.loads((folder/'decisions.json').read_text());ids=summary['body_ids']
        groups={name:dict(records=0,ticks=0,max_normal_force=0,negative_distance_records=0,positive_distance_records=0,near_zero_distance_records=0) for name in GROUPS}
        before_after={t:None for r in rows for t in (r['before_tick'],r['after_tick'])};first_delivery=first_return=first_payload=None;presence_first={};missing=total=0
        forward_ticks=forward_supported=return_ticks=return_supported=0;events=True;facts_match=True;carrier_fk=presence_fk=0.;delivery_stored=None;max_non_target_step_displacement=0.
        previous=None;non_target_displacement_by_item={i:0. for i in ids['objects']};preserve_refs={};max_non_target_interval_displacement=0.
        with gzip.open(folder/'ticks.jsonl.gz','rt') as stream:
            for line in stream:
                s=json.loads(line);total+=1
                if s['tick'] in before_after:before_after[s['tick']]=s
                found={name:[] for name in GROUPS};missing+=sum('position_b' not in c or 'contact_distance' not in c for c in s['contacts'])
                for c in s['contacts']:
                    pair={c['body_a'],c['body_b']};robot=ids['robot'];carrier=ids['carrier'];inspection=ids['inspection'];presence=ids['presence'];objects=set(ids['objects'].values())
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
                        if pair=={robot,body}:found['expected_target_robot' if item==s['robot_target_item'] else 'forbidden_non_target_robot'].append(c)
                        if body in pair and (pair-{body}).isdisjoint({robot,carrier,inspection,presence,*objects}):found['expected_objects_static_support'].append(c)
                    if robot in pair and (pair-{robot}).isdisjoint({carrier,inspection,presence,*objects,*ids['inspection_walls']}):found['forbidden_robot_static'].append(c)
                for name,contacts in found.items():
                    g=groups[name];g['records']+=len(contacts);g['ticks']+=int(bool(contacts))
                    for c in contacts:
                        g['max_normal_force']=max(g['max_normal_force'],c['normal_force']);d=c['contact_distance'];g['negative_distance_records' if d<-1e-6 else ('positive_distance_records' if d>1e-6 else 'near_zero_distance_records')]+=1
                carrier_fk=max(carrier_fk,abs(s['partner_position'][1]-s['partner_joint']))
                r,bs,rs,supported=support(s,ids,ids['carrier'],[.65,s['partner_joint'],TRANSPORT['carrier_center_start'][2]],[0,s['partner_velocity'],0])
                delivered=s['delivery_start_tick'] is not None and abs(s['partner_joint'])<TRANSPORT['carrier_goal_joint_tolerance'] and abs(s['partner_velocity'])<TRANSPORT['carrier_speed_limit'] and math.hypot(*r[:2])<TRANSPORT['blue_relative_xy_tolerance'] and TRANSPORT['blue_relative_z_range'][0]<r[2]<TRANSPORT['blue_relative_z_range'][1] and bs<TRANSPORT['blue_world_speed_limit'] and rs<TRANSPORT['blue_relative_speed_limit'] and supported
                facts_match&=bool(delivered)==s['delivery_facts']['satisfied']
                if s['delivery_start_tick'] is not None and first_delivery is None:forward_ticks+=1;forward_supported+=int(supported)
                if delivered and first_delivery is None:first_delivery=s['tick'];delivery_stored=s['delivery_event']
                events&=(s['delivery_event'] is None if first_delivery is None else s['delivery_event']==delivery_stored and delivery_stored['first_tick']==first_delivery)
                if s['return_start_tick'] is not None:
                    returned=abs(s['partner_joint']-TRANSPORT['travel_m'])<CONFIG['position_tolerance_m'] and abs(s['partner_velocity'])<CONFIG['stable_speed_m_s']
                    payload=returned and supported and math.hypot(*r[:2])<TRANSPORT['blue_relative_xy_tolerance'] and TRANSPORT['blue_relative_z_range'][0]<r[2]<TRANSPORT['blue_relative_z_range'][1] and rs<TRANSPORT['blue_relative_speed_limit'] and bs<TRANSPORT['blue_world_speed_limit']
                    facts_match&=bool(returned)==s['return_facts']['carrier_returned'] and bool(payload)==s['return_facts']['payload_returned']
                    if first_return is None:return_ticks+=1;return_supported+=int(supported)
                    if returned and first_return is None:first_return=s['tick']
                    if payload and first_payload is None:first_payload=s['tick']
                    events&=(s['return_event'] is None if first_return is None else s['return_event']['first_tick']==first_return)
                    events&=(s['payload_return_event'] is None if first_payload is None else s['payload_return_event']['first_tick']==first_payload)
                if s['inspection_facts'] is not None:
                    ri,bsi,rsi,si=support(s,ids,ids['inspection'],CONFIG['inspection_center'],[0,0,0]);inspect=math.hypot(*ri[:2])<CONFIG['inspection_xy_tolerance_m'] and CONFIG['inspection_z_range_m'][0]<ri[2]+CONFIG['inspection_center'][2]<CONFIG['inspection_z_range_m'][1] and bsi<CONFIG['inspection_speed_m_s'] and si
                    facts_match&=bool(inspect)==s['inspection_facts']['satisfied']
                if s['presence'] is not None:
                    pf=s['presence'];presence_fk=max(presence_fk,abs(pf['position'][1]-pf['joint']))
                    for dest in ('near','far'):
                        actual=abs(pf['joint']-CONFIG['presence_'+dest+'_joint'])<CONFIG['position_tolerance_m'] and abs(pf['velocity'])<CONFIG['stable_speed_m_s'];facts_match&=bool(actual)==pf[dest]
                    for e in s['presence_events']:
                        dest=e['kind'].split('_')[1]
                        if e['kind'] not in presence_first:
                            presence_first[e['kind']]=s['tick'];events&=e['first_tick']==s['tick'] and pf[dest]
                if previous is not None and s['tick']>summary['common_start_tick']:
                    for item in ids['objects']:
                        if item!=s['robot_target_item'] and not (item=='blue' and (first_delivery is None or s['return_start_tick'] is not None)):
                            d=math.dist(s['objects'][item]['position'],previous['objects'][item]['position']);max_non_target_step_displacement=max(max_non_target_step_displacement,d);non_target_displacement_by_item[item]+=d
                            if item not in preserve_refs:preserve_refs[item]=previous['objects'][item]['position']
                            max_non_target_interval_displacement=max(max_non_target_interval_displacement,math.dist(s['objects'][item]['position'],preserve_refs[item]))
                        else:preserve_refs.pop(item,None)
                previous=s;final=s
        input_checks=[]
        for row in rows:
            check=dict(before_actual=equal(row['before_state'],before_after[row['before_tick']]),after_actual=equal(row['after_state'],before_after[row['after_tick']]),
                repeat_physics_equal=not row['result'].get('no_op',False) or (equal(row['before_state'],row['after_state']) and row['before_tick']==row['after_tick']))
            input_checks.append(dict(sequence=row['sequence'],passed=all(check.values()),checks=check))
        actual=dict(all_commands_executed=len(rows)==len(case['commands']),all_commands_successful=all(r['result']['success'] for r in rows),forward_delivery=first_delivery is not None)
        if case['group']=='A':actual.update(inspection_actual=rows[3]['after_state']['inspection_facts']['satisfied'],blue_final=stable_region(final,'blue',case['goal']),red_preserved=stable_region(final,'red','left'),green_source_preserved=math.dist(summary['initial_state']['objects']['green']['position'],final['objects']['green']['position'])<.01)
        elif case['group']=='B':
            first=case['first'];other='right' if first=='left' else 'left';green=[r for r in rows if r['choice'].startswith('green_')]
            actual.update(green_final=stable_region(final,'green',other),red_final=stable_region(final,'red','left'),blue_final=stable_region(final,'blue',first),repeat_real_noop=green[1]['result'].get('no_op',False) and equal(green[1]['before_state'],green[1]['after_state']),timing_actually_exposed=green[0]['before_state']['delivery_event'] is not None if case['timing']=='after' else green[0]['before_state']['delivery_event'] is None)
        elif case['group']=='C':actual.update(inspection_actual=rows[2]['after_state']['inspection_facts']['satisfied'],presence_far_event='presence_far' in presence_first,presence_near_event='presence_near' in presence_first,green_final=stable_region(final,'green','right'),red_final=stable_region(final,'red','left'),blue_final=stable_region(final,'blue',case['goal']))
        elif case['group']=='E':actual.update(first_real_region=stable_region(rows[3]['after_state'],'blue',case['first']),inspection_actual=rows[4]['after_state']['inspection_facts']['satisfied'],blue_final=stable_region(final,'blue',case['goal']),red_preserved=stable_region(final,'red','left'),green_source_preserved=math.dist(summary['initial_state']['objects']['green']['position'],final['objects']['green']['position'])<.01)
        elif case['group']=='D':actual.update(carrier_return_actual=first_return is not None,payload_return_truth=(first_payload is not None)==(case['payload']=='on_carrier'),forward_event_preserved=events,red_preserved=stable_region(final,'red','left'),taken_blue_preserved=case['payload']!='taken_left' or stable_region(final,'blue','left'))
        safety=all(g['records']==0 for name,g in groups.items() if name.startswith('forbidden'))
        checks=dict(all_script_facts=all(actual.values()),runtime_facts_match=actual==summary['facts'],all_snapshots=all(c['passed'] for c in input_checks),contact_fields_complete=missing==0,
            support_facts_recomputed=facts_match,event_actual_and_latch=events,forward_support=forward_supported==forward_ticks,carrier_fk=carrier_fk<1e-6,presence_fk=presence_fk<1e-6,
            full_canonical_exact=digest(folder/'ticks.jsonl.gz')==summary['canonical_physics'],final_actual_exact=equal(final,summary['final_state']),full_contact_safety=safety,non_target_interval_preserved=max_non_target_interval_displacement<.01)
        if case['group']=='D':checks['reverse_support_truth']=return_supported==return_ticks if case['payload']=='on_carrier' else return_supported==0
        report=dict(id=case['id'],checks=checks,passed=all(checks.values()),actual_facts=actual,input_checks=input_checks,groups=groups,total_ticks=total,missing_contact_fields=missing,
            forward_ticks=forward_ticks,forward_supported_ticks=forward_supported,return_ticks=return_ticks,return_supported_ticks=return_supported,first_delivery=first_delivery,first_return=first_return,first_payload_return=first_payload,
            presence_actual_events=presence_first,carrier_fk_max=carrier_fk,presence_fk_max=presence_fk,non_target_sum_step_displacement_m=non_target_displacement_by_item,max_non_target_step_displacement_m=max_non_target_step_displacement,max_non_target_interval_displacement_m=max_non_target_interval_displacement,
            makespan_ticks=summary['makespan_ticks'],physical_attempts=summary['physical_attempts'],zero_tick_repeats=summary['zero_tick_repeats'])
        episodes.append(report);print(case['id'],report['passed'],[k for k,v in checks.items() if not v],flush=True)
    result=dict(stage=stage,total=len(episodes),passed=sum(e['passed'] for e in episodes),total_ticks=sum(e['total_ticks'] for e in episodes),episodes=episodes,
        source_sha256=hashes(),freeze_sha256=sha(freeze_path(stage)),audit_source_sha256=sha(ROOT/'experiments/structure_foundation_v20/audit_e.py'))
    save(RESULT/f'{stage}_audit_dev1.json',result);assert result['passed']==len(episodes);print('阶段审计通过',stage,result['total_ticks'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('E',));audit(p.parse_args().stage)
