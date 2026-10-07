#!/usr/bin/env python3
"""从原始视觉输出与真实轨迹量化空间协调；不把位移或回应直接判为合作成功。"""
import argparse
import json
from pathlib import Path

import numpy as np


def rows(path):return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def hand_contacts(row):
    count=0
    for c in row['contacts']:
        a,b=c['geom1'] or '',c['geom2'] or ''
        if b.startswith('human_'):a,b=b,a
        count+=a.startswith(('human_palm','human_left_finger','human_right_finger','human_fingertip')) and b.startswith(('robot','gripper')) and c['distance_m']<=0
    return count


def audit(ep):
    plans=rows(ep/'robot_planner_io.jsonl');trace=rows(ep/'trace.jsonl');calls=rows(ep/'model_calls.jsonl')
    by_step={r['step']:r for r in trace};events=[]
    for index,plan in enumerate(plans):
        if plan['decision']['mode']!='move_ee':continue
        raw=json.loads(plan['raw_output'][plan['raw_output'].find('{'):plan['raw_output'].rfind('}')+1])
        assert raw['mode']=='move_ee' and plan['parse_error'] is None
        desired=np.asarray(raw['delta_xyz_m'],dtype=float)
        assert desired.shape==(3,) and np.isfinite(desired).all() and np.linalg.norm(desired)<=.2+1e-9
        start=by_step[plan['step']];end=by_step[plans[index+1]['step']] if index+1<len(plans) else trace[-1]
        target=np.asarray(plan['public_input']['state'][:3])+desired
        np.testing.assert_allclose(plan['cartesian_target_xyz_m'],target,atol=1e-9)
        selected=[c for c in calls if c['planner_decision_id']==plan['decision_id']]
        assert selected and all(c['action_source']=='vlm_selected_cartesian_primitive' for c in selected)
        movement=np.asarray(end['robot_ee'])-start['robot_ee']
        window=[r for r in trace if start['step']<=r['step']<=end['step']]
        peak=max(np.linalg.norm(np.asarray(b['robot_ee'])-a['robot_ee'])/(b['time_s']-a['time_s']) for a,b in zip(window,window[1:]))
        contact_s=sum(b['time_s']-a['time_s'] for a,b in zip(window,window[1:]) if hand_contacts(b))
        events.append({'decision_id':plan['decision_id'],'start_s':start['time_s'],'end_s':end['time_s'],
            'model_requested_delta_xyz_m':desired.tolist(),'requested_displacement_m':float(np.linalg.norm(desired)),
            'actual_eef_displacement_xyz_m':movement.tolist(),'actual_eef_displacement_m':float(np.linalg.norm(movement)),
            'actual_progress_along_requested_direction_m':float(np.dot(movement,desired)/max(np.linalg.norm(desired),1e-12)),
            'remaining_target_distance_m':float(np.linalg.norm(target-end['robot_ee'])),
            'actual_eef_peak_sampled_speed_m_s':float(peak),'human_robot_contact_time_during_move_s':contact_s,
            'human_robot_contact_pairs_at_start':hand_contacts(start),'human_robot_contact_pairs_at_end':hand_contacts(end),
            'model_reason':plan['decision']['reason'],'public_message':plan['decision']['message']})
    requests=[{'time_s':r['time_s'],'text':m['text']} for r in rows(ep/'human_policy_io.jsonl')
        for m in r.get('negotiation_proposal_messages',[]) if m['text'].startswith('request_space:')]
    for request in requests:
        following=next((e for e in events if e['start_s']>=request['time_s']-1e-9),None)
        request['next_model_selected_move_delay_s']=following['start_s']-request['time_s'] if following else None
    return {'episode':str(ep),'status':'audited','model_selected_spatial_moves':len(events),'events':events,
        'public_space_requests':requests,'interpretation':'模型选择与实际位移、几何接触的描述；后续位移时间不是请求导致的因果证据，也不保证让开整臂、任务完成、安全或cobalance。'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    root=parser.parse_args().input_dir
    episodes=[audit(p.parent) for p in root.rglob('robot_planner_io.jsonl')];assert episodes
    result={'status':'audited','episodes':episodes}
    (root/'spatial_motion_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps([{'episode':e['episode'],'model_selected_spatial_moves':e['model_selected_spatial_moves']} for e in episodes],ensure_ascii=False))
