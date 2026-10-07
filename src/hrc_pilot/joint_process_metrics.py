"""从实际轨迹与调用记录测量过程；不给话语赋予语义成功标签。"""
import numpy as np


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
