"""从实际轨迹与调用记录测量过程；不给话语赋予语义成功标签。"""
import numpy as np

from .libero_native import perceived_object_contacts


def original_arrangement_observations(activity,trace,placements,regions):
    """旧安排的物理见证；安排修改后的成败必须另作语义审阅。"""
    if len(placements)!=len(trace)-1:raise ValueError('物理关系记录与实际轨迹不对齐')
    primary={'snack_service':'akita_black_bowl_1','drink_storage':'wine_bottle_1','drawer_access':'cream_cheese_1'}[activity]
    witnesses=[]
    for record,placement in zip(trace[1:],placements):
        if not np.isclose(record['time_s'],placement['time_s']):raise ValueError('物理见证时间不一致')
        all_contacts=perceived_object_contacts(record);contacts=all_contacts[primary]
        released=record['human_execution']['held_object']!=primary and not contacts['robot_hand_contact']
        required=[primary,'cream_cheese_1'] if activity=='snack_service' else [primary]
        all_released=all(name in all_contacts and record['human_execution']['held_object']!=name and
                         not all_contacts[name]['robot_hand_contact'] for name in required)
        native=bool(placement.get('native_physical_goal_success',placement.get('released_stable_placement',False)))
        target=None;distance=None
        if activity=='snack_service':
            target='snack_delivery';distance=float(np.linalg.norm(np.asarray(record['objects'][primary])[:2]-np.asarray(regions[target])[:2]))
            spatial=distance<.025 and 'table' in contacts['contact_entities']
        elif activity=='drawer_access':
            target='drawer_storage'
            drawer=record.get('observable_world',{}).get('drawer')
            point=drawer['support_xyz'] if drawer else regions[target]
            distance=float(np.linalg.norm(np.asarray(record['objects'][primary])[:2]-np.asarray(point)[:2]))
            # 底面接触是存放见证；不据此声称已计算完整几何包含。
            bottom_contact=any('wooden_cabinet_1_g27' in (p['geom1'],p['geom2']) and
                any((g or '').startswith(primary+'_') for g in (p['geom1'],p['geom2'])) for p in record['contacts'])
            spatial=distance<.025 and bottom_contact
        else:
            spatial='wine_rack_1' in contacts['contact_entities']
        witnesses.append({'time_s':record['time_s'],'native_relation':native,'released_primary':released,
            'released_all_required_objects':all_released,
            'support_contact_entities':contacts['contact_entities'],'original_named_target':target,
            'xy_distance_to_target_m':distance,'original_spatial_criterion':bool(spatial),
            'physical_match':bool(native and all_released and spatial)})
    final=witnesses[-1];window=[w for w in witnesses if w['time_s']>=final['time_s']-1.]
    return {'primary_object_id':primary,'terminal_observation':final,
        'first_physical_match_s':next((w['time_s'] for w in witnesses if w['physical_match']),None),
        'last_second_consistently_matches':all(w['physical_match'] for w in window),
        'scope':'原始安排的物理关系／释放／目标位置见证；不评价更新后共同约定、完整抽屉包含、分工合理性或cobalance。',
        'current_arrangement_score':None}


def measured_process(trace, human, controls, receipts):
    if len(trace)<2:
        raise ValueError('过程核查需要至少两个实际状态')
    times=np.asarray([r['time_s'] for r in trace],dtype=float)
    dt=np.diff(times)
    if not np.all(dt>0):
        raise ValueError('实际时间轴必须严格递增')
    aside=np.asarray([r['human_body_xy'][1]>=.8 for r in trace])
    departures=[];returns=[]
    for i in range(1,len(trace)):
        if aside[i] and not aside[i-1]:departures.append(float(times[i]))
        if not aside[i] and aside[i-1]:returns.append(float(times[i]))
    cycles=[]
    for start in departures:
        end=next((t for t in returns if t>start),None)
        cycles.append({'departure_s':start,'return_s':end,'duration_s':end-start if end is not None else None})
    completed={}
    for r in trace:
        for request in r['human_execution']['completed_requests']:
            completed.setdefault(request,r['time_s'])
    receipt_by_id={r['request_id']:r for r in receipts}
    actions=[]
    for row in human:
        c=row['choice'];request=row['decision_id'];receipt=receipt_by_id.get(request,{})
        if c['action'] not in {'pick','place','relocate','away','return'}:continue
        actions.append({'request_id':request,'action':c['action'],'issued_s':row['time_s'],
            'accepted':receipt.get('accepted'),'completed_s':completed.get(request),
            'effect':receipt.get('effect','not_recorded'),
            'interpretation':'完成请求可能是已在目标的无运动满足，不等于一次新增贡献'})
    # 测量选择保持的控制时间；不自动解释为无谓等待。
    holds=sum(dt[i] for i,c in enumerate(controls) if 'hold' in c['source'])
    eef=np.asarray([r['robot_ee'] for r in trace],dtype=float)
    path=float(np.linalg.norm(np.diff(eef,axis=0),axis=1).sum())
    latency=[r['latency_s'] for r in human if 'latency_s' in r]
    return {
        'actual_participation':{
            'initially_aside':bool(aside[0]),'first_workspace_entry_s':returns[0] if aside[0] and returns else None,
            'departures_s':departures,'returns_s':returns,'departure_return_cycles':cycles,
            'measurement':'以实际身体 y>=0.8 识别旁边位置；初始在旁边不计后续暂离'},
        'human_action_requests':actions,
        'accepted_already_satisfied_request_count':sum(r.get('effect')=='already_at_requested_supported_position' for r in receipts),
        'robot_selected_hold_duration_s':float(holds),'robot_eef_path_length_m':path,
        'human_total_inference_wall_s':sum(latency),
        'human_inference_wall_p95_s':float(np.quantile(latency,.95)) if latency else None,
        'interpretation':'实际参与、请求兑现、末端运动和所选保持；无谓等待、分工合理性与协调负担需结合活动语义审阅，不自动计cobalance。',
    }
