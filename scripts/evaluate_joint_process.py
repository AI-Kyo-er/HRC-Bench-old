#!/usr/bin/env python3
"""独立重建共同活动过程见证；不把语言次数／原生目标自动当成cobalance。"""
import argparse
import json
from pathlib import Path

import numpy as np

from hrc_pilot.joint_process_metrics import measured_process


def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def evaluate(root):
    ep=root/'episode';trace=rows(ep/'trace.jsonl');human=rows(ep/'human_policy_io.jsonl')
    dialogue=rows(ep/'public_dialogue.jsonl');calls=rows(ep/'model_calls.jsonl')
    plans=rows(ep/'robot_planner_io.jsonl') if (ep/'robot_planner_io.jsonl').exists() else []
    actions=[];first_completions={};away=[];started=None
    for i,r in enumerate(trace):
        for request in r['human_execution']['completed_requests']:
            first_completions.setdefault(request,r['time_s'])
        body=r['human_body_xy'][1]
        if body>=.8 and started is None:started=r['time_s']
        if body<.8 and started is not None:
            if r['time_s']-started>=.5:away.append({'start_s':started,'end_s':r['time_s']})
            started=None
    if started is not None and trace[-1]['time_s']-started>=.5:
        away.append({'start_s':started,'end_s':trace[-1]['time_s']})
    for d in human:
        c=d['choice']
        if c['action'] not in {'pick','place','relocate','away','return'}:continue
        index=round(d['time_s']*20);r=trace[index]
        complete=first_completions.get(d['decision_id'])
        obj=c.get('object_id') or r['human_execution']['held_object']
        displacement=None
        if obj in r['objects'] and complete is not None:
            end=trace[min(round(complete*20),len(trace)-1)]
            displacement=float(np.linalg.norm(np.asarray(end['objects'][obj])-r['objects'][obj]))
        destination=c.get('destination');already_near=None
        if obj in r['objects'] and destination:
            source_scene=d.get('observation_source_scene',d['private_input']['scene'])
            point=source_scene['regions_xyz'].get(destination)
            if point is not None:already_near=float(np.linalg.norm(np.asarray(r['objects'][obj])[:2]-np.asarray(point)[:2]))<.025
        actions.append({'time_s':d['time_s'],'request_id':d['decision_id'],'action':c['action'],
            'object_id':obj,'destination':destination,'completed_time_s':complete,
            'measured_object_displacement_m':displacement,'object_already_near_destination_at_request':already_near,
            'public_expression':c.get('message'),'private_reason_for_review':c.get('reason')})
    readiness=[]
    for r in trace:
        world=r.get('observable_world',{});near=world.get('object_distance_to_named_region_xy_m',{})
        obj,region={'snack_service':('akita_black_bowl_1','serving_ready'),
            'drink_storage':('wine_bottle_1','drink_staging'),
            'drawer_access':('plate_1','plate_1_personal')}[json.loads((root/'provenance.json').read_text())['activity']]
        contact=world.get('object_contacts',{}).get(obj,{})
        ready=(near.get(obj,{}).get(region,float('inf'))<.025 and r['human_execution']['held_object']!=obj
               and not contact.get('robot_hand_contact',False) and 'table' in contact.get('contact_entities',[]))
        readiness.append(ready)
    stable=0.;first_ready=None
    for r,ready in zip(trace,readiness):
        stable=stable+.05 if ready else 0.
        if stable>=.2-1e-9 and first_ready is None:first_ready=r['time_s']
    reads=[]
    for message in dialogue:
        if message['speaker'] not in {'human','robot'}:continue
        read_time=None
        if message['speaker']=='robot':
            for h in human:
                actual_input=h['private_input']['scene']
                actual_dialogue=actual_input.get('public_dialogue',actual_input.get('public_partner_statements_not_execution_facts',[]))
                if message in actual_dialogue:
                    read_time=h['time_s'];break
        else:
            for p in plans:
                if p['time_s']>=message['time_s'] and any(m['speaker']=='human' and m['text']==message['text']
                                                         for m in p['public_input']['dialogue']):
                    read_time=p['time_s'];break
            if not plans:
                for c in calls:
                    if c['time_s']>=message['time_s'] and message['text'] in c['prompt']:
                        read_time=c['time_s'];break
        reads.append({'speaker':message['speaker'],'published_time_s':message['time_s'],'text':message['text'],
                      'first_input_read_time_s':read_time,'input_delivery_delay_s':read_time-message['time_s'] if read_time is not None else None,
                      'interpretation':'仅是进入对方输入，不是理解／同意／因果响应的证据'})
    placements=rows(ep/'placement_evidence.jsonl')
    robot_first=next((r['time_s'] for r in placements if r.get('native_physical_goal_success',r.get('released_stable_placement',False))),None)
    result={'status':'audited','body_away_intervals':away,'completed_human_actions':actions,
        'first_released_supported_preparation_s':first_ready,'robot_first_physical_contribution_s':robot_first,
        'placement_before_prepared_witness':bool(robot_first is not None and (first_ready is None or robot_first<first_ready)),
        'already_near_relocation_request_count':sum(a['action']=='relocate' and a['object_already_near_destination_at_request'] is True for a in actions),
        'public_message_input_receipts':reads,
        'shared_current_outcome_status':'requires_public_arrangement_semantic_review',
        'interpretation':'动作完成／初始近目标／身体离返／输入递送的实测见证；重复搬运可能有合理原因，语言与模式数量不直接代表协作质量。'}
    controls=rows(ep/'robot_control.jsonl');receipts=rows(ep/'human_command_receipts.jsonl')
    result['measured_process']=measured_process(trace,human,controls,receipts)
    result['preparation_measurement_scope']='指定准备区域的桌面释放支撑，不穷尽可用准备方式；抽屉的plate_personal位置不是所有合理清理方式。'
    (root/'joint_process_evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in {'completed_human_actions','public_message_input_receipts'}},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    evaluate(parser.parse_args().input_dir)
