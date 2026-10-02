"""全量接触分类及真实首次交付事件复核，必要承载不计禁止接触。"""
import gzip
import json
import math

from experiments.physical.run import ROOT, save, sha

RESULT=ROOT/'results/structure_v8'


def audit_trace(folder, config):
    summary=json.loads((folder/'summary.json').read_text())
    ids=summary['body_ids']; robot,carrier=ids['robot'],ids['partner']; objects=ids['objects']
    groups={name:dict(ticks=0,records=0,max_normal_force=0,negative_distance_records=0,near_zero_distance_records=0,positive_distance_records=0)
            for name in ('expected_blue_carrier','forbidden_robot_carrier','forbidden_other_object_carrier','carrier_static','non_target_robot')}
    total=missing=transport_ticks=supported_ticks=0
    first=None; event_consistent=True; stored_first=None; max_slip=0; non_target_items={}
    max_fk_error=0; facts_match=True; first_goals={}; max_green_displacement=0
    for name in groups: groups[name]['body_pairs']={}
    with gzip.open(folder/'ticks.jsonl.gz','rt') as stream:
        for line in stream:
            state=json.loads(line); total+=1
            missing+=sum('contact_distance' not in c or 'position_b' not in c for c in state['contacts'])
            found={name:[] for name in groups}
            for c in state['contacts']:
                pair={c['body_a'],c['body_b']}
                if pair=={objects['blue'],carrier}: found['expected_blue_carrier'].append(c)
                if pair=={robot,carrier}: found['forbidden_robot_carrier'].append(c)
                if any(pair=={objects[x],carrier} for x in ('red','green')): found['forbidden_other_object_carrier'].append(c)
                if carrier in pair and (pair-{carrier}).isdisjoint({robot,*objects.values()}): found['carrier_static'].append(c)
                for item,body in objects.items():
                    if pair=={robot,body} and item!=state['robot_target_item']:
                        found['non_target_robot'].append(c)
                        non_target_items[item]=non_target_items.get(item,0)+1
            for name,contacts in found.items():
                group=groups[name]; group['ticks']+=int(bool(contacts)); group['records']+=len(contacts)
                for c in contacts:
                    group['max_normal_force']=max(group['max_normal_force'],c['normal_force'])
                    distance=c['contact_distance']
                    key='negative_distance_records' if distance < -1e-6 else ('positive_distance_records' if distance>1e-6 else 'near_zero_distance_records')
                    group[key]+=1
                    body_pair=f'{min(c["body_a"],c["body_b"])}-{max(c["body_a"],c["body_b"])}'
                    group['body_pairs'][body_pair]=group['body_pairs'].get(body_pair,0)+1
            support=found['expected_blue_carrier']
            actual_support=any(c['contact_distance']<=config['support_contact_max_distance'] and c['normal_force']>config['support_contact_min_force'] for c in support)
            blue=state['objects']['blue']
            relative=[blue['position'][0]-.65,blue['position'][1]-state['partner_joint'],blue['position'][2]-config['carrier_center_start'][2]]
            blue_speed=math.sqrt(sum(v*v for v in blue['velocity']))
            relative_speed=math.sqrt(sum(v*v for v in (blue['velocity'][0],blue['velocity'][1]-state['partner_velocity'],blue['velocity'][2])))
            max_fk_error=max(max_fk_error,abs(state['partner_position'][1]-state['partner_joint']))
            if state['tick'] >= summary['initial_state']['tick']:
                max_green_displacement=max(max_green_displacement,math.dist(state['objects']['green']['position'],summary['initial_state']['objects']['green']['position']))
            for index,item in enumerate(('red','blue')):
                obj=state['objects'][item]; pos=obj['position']; vel=math.sqrt(sum(v*v for v in obj['velocity']))
                if item not in first_goals and math.dist(pos[:2],[.59+.06*index,-.25])<.035 and .025<pos[2]<.055 and vel<.04:
                    first_goals[item]=state['tick']
            satisfied=(state['delivery_start_tick'] is not None and abs(state['partner_joint'])<config['carrier_goal_joint_tolerance'] and
                abs(state['partner_velocity'])<config['carrier_speed_limit'] and math.hypot(*relative[:2])<config['blue_relative_xy_tolerance'] and
                config['blue_relative_z_range'][0]<relative[2]<config['blue_relative_z_range'][1] and
                blue_speed<config['blue_world_speed_limit'] and relative_speed<config['blue_relative_speed_limit'] and actual_support)
            facts_match=facts_match and bool(satisfied)==state['delivery_facts']['satisfied']
            if state['delivery_start_tick'] is not None and first is None:
                transport_ticks+=1; supported_ticks+=int(actual_support); max_slip=max(max_slip,math.hypot(*relative[:2]))
            if satisfied and first is None: first=state['tick']
            if first is None:
                event_consistent=event_consistent and state['delivery_event'] is None
            else:
                if stored_first is None: stored_first=state['delivery_event']
                event_consistent=event_consistent and state['delivery_event']==stored_first and stored_first['first_tick']==first
    online_support=summary['expected_blue_carrier_support_online']
    online_match=(total==summary['robot_partner_online']['total_ticks'] and
        groups['forbidden_robot_carrier']['ticks']==summary['robot_partner_online']['robot_partner_ticks'] and
        groups['forbidden_other_object_carrier']['ticks']==summary['other_objects_partner_online']['ticks'] and
        groups['expected_blue_carrier']['records']==online_support['records'] and
        transport_ticks==online_support['transport_ticks'] and supported_ticks==online_support['transport_supported_ticks'] and
        groups['non_target_robot']['records']==summary['non_target_robot_online']['records'])
    return dict(total_ticks=total,groups=groups,missing_distance_or_position_pair_records=missing,
        recomputed_first_delivery_tick=first,recomputed_first_goal_region_ticks=first_goals,goal_first_ticks_match=first_goals==summary['goal_first_ticks'],
        same_tick_current_FK_joint_max_y_error_m=max_fk_error,all_delivery_facts_match_independent_recomputation=facts_match,max_green_displacement_m=max_green_displacement,event_history_consistent=event_consistent,event_persists_after_pickup=event_consistent if any(i['item']=='blue' for i in summary['robot_intervals']) else None,online_match=online_match,pickup_exposed=any(i['item']=='blue' for i in summary['robot_intervals']),
        transport_ticks=transport_ticks,transport_supported_ticks=supported_ticks,max_relative_xy_slip_m=max_slip,
        support_coverage=supported_ticks/transport_ticks if transport_ticks else None,non_target_robot_contact_records_by_item=non_target_items,
        safety_pass=all(groups[n]['records']==0 for n in ('forbidden_robot_carrier','forbidden_other_object_carrier','carrier_static')),
        trace_sha256=sha(folder/'ticks.jsonl.gz'))


def controls():
    report={}
    for version,config_name in (('dev0','transport_config.json'),('dev1','transport_config_v1.json'),('dev2','transport_config_v1.json')):
        config=json.loads((ROOT/'experiments/structure_v8'/config_name).read_text())
        report[version]=[dict(id=f.name,audit=audit_trace(f,config)) for f in sorted((RESULT/f'raw/controls_{version}').iterdir())]
    save(RESULT/'control_contact_audit.json',report)
    print('controls audit',[(name,sum(row['audit']['safety_pass'] and row['audit']['recomputed_first_delivery_tick'] is not None for row in rows)) for name,rows in report.items()],flush=True)


if __name__=='__main__':
    controls()
