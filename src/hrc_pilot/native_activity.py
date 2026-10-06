"""公开动态工作要求及离线测量；不产生人/机器人动作，不写物体位置。"""
from dataclasses import asdict, dataclass

import numpy as np

from .protocol import Message


@dataclass(frozen=True)
class WorkUpdate:
    time_s: float
    label: str
    instruction: str
    object_id: str | None = None
    destination: str | None = None
    requirement: str = 'object_region'

    def messages(self, robot_instruction):
        # activity_change replaces the public task board but retains personal memory.
        return [Message('environment','activity_change',self.instruction),
                Message('environment','assignment',robot_instruction,None,'robot'),
                Message('environment','assignment',self.instruction,self.object_id,'human',self.destination)]


def activity_plan(profile):
    if profile=='receiver_changes':
        return [WorkUpdate(0,'准备接收盘','Move plate_1 to plate_ready so the robot can place its bowl. Coordinate access; you may work in parallel.','plate_1','plate_ready'),
                WorkUpdate(15,'改回原位置','The table arrangement has changed. Move plate_1 back to plate_home. The earlier plate_ready request is superseded; tell the robot the new location.','plate_1','plate_home'),
                WorkUpdate(30,'再次准备接收盘','We need the receiving plate at plate_ready again. Move plate_1 there and coordinate with the robot using the actual current state.','plate_1','plate_ready')]
    if profile=='priority_changes':
        return [WorkUpdate(0,'先整理饼干','Move cookies_1 to cookies_ready. The robot works on its bowl independently; coordinate nearby access.','cookies_1','cookies_ready'),
                WorkUpdate(15,'接收盘优先','The receiving plate is now the priority. Move plate_1 to plate_ready first; pause unfinished cookie work if needed and tell the robot.','plate_1','plate_ready'),
                WorkUpdate(30,'饼干改回原位置','Return cookies_1 to cookies_home. The previous plate task is no longer required; decide your next action from the current measurements.','cookies_1','cookies_home')]
    if profile=='interruption_return':
        return [WorkUpdate(0,'整理饼干','Move cookies_1 to cookies_ready while coordinating nearby access with the robot.','cookies_1','cookies_ready'),
                WorkUpdate(12,'临时事务','A personal errand interrupts your table work. Step back from the table for now and tell the robot; earlier object work is suspended.',requirement='clearance'),
                WorkUpdate(18,'返回继续','The errand is over. Return to your table working position and coordinate with the robot before resuming.',requirement='return'),
                WorkUpdate(30,'准备接收盘','Now prepare plate_1 at plate_ready for the robot. Use the current world state rather than assuming the earlier work finished.','plate_1','plate_ready')]
    raise ValueError('未知动态活动')


PROFILES=('receiver_changes','priority_changes','interruption_return')


def activity_regions(objects):
    regions={}
    for obj,prefix in [('plate_1','plate'),('cookies_1','cookies')]:
        if obj not in objects:raise ValueError(f'动态任务缺少物体：{obj}')
        home=np.asarray(objects[obj],dtype=float)
        regions[prefix+'_home']=tuple(home)
        regions[prefix+'_ready']=tuple(home+[0,.12,0])
    # Keep the old marker name for engine/auditor compatibility; it is publicly aliased.
    regions['near_human']=regions['plate_ready']
    return regions


def public_surfaces(regions):
    colors={'plate_ready':'green','plate_home':'blue','cookies_ready':'orange','cookies_home':'purple','near_human':'green'}
    return {name:{'shape':'circle','spatial_reference':'object_center','center_xyz':list(position),
                  'radius_m':.025,'color':colors[name],'source':'visible_marker_geometry'}
            for name,position in regions.items()}


def evaluate_activity(plan, regions, trace, controls, decisions, placement):
    """分别量化公开更新响应和真实完成；所有结果仅用于事后报告。"""
    stages=[]
    for index,update in enumerate(plan):
        end=plan[index+1].time_s if index+1<len(plan) else trace[-1]['time_s']
        selected=[d for d in decisions if update.time_s<=d['time_s']<end]
        window=[r for r in trace if update.time_s<=r['time_s']<end or
                (index==len(plan)-1 and r['time_s']==end)]
        stale=0;pushes=0;selected_latency=None
        for d in selected:
            c=d['parsed_decision'];intent=c['intent']
            matches=(intent=='push' and c.get('object_id')==update.object_id and c.get('destination')==update.destination
                     if update.requirement=='object_region' else intent=={'clearance':'away','return':'return'}[update.requirement])
            if matches and selected_latency is None:selected_latency=d['time_s']-update.time_s
            if intent=='push':
                pushes+=1;stale+=int(not matches)
        start_physics=trace[0]['physics_time_s']
        phase_controls=[c for c in controls if update.time_s<=c['physics_time_s']-start_physics<end]
        witness=bool(update.object_id and any(any(name.startswith(update.object_id+'_') for name in c['contact_geoms']) for c in phase_controls))
        dwell=0.;first_completion=None;dt=.05
        previous=None;initial_distance=None;last_distance=None
        for r in window:
            if update.requirement=='object_region':
                p=np.asarray(r['objects'][update.object_id]);g=np.asarray(regions[update.destination])
                dist=float(np.linalg.norm(p[:2]-g[:2]))
                if initial_distance is None:initial_distance=dist
                last_distance=dist
                speed=(float(np.linalg.norm(p-np.asarray(previous['objects'][update.object_id]))/dt) if previous else float('inf'))
                # Require a witness at/before this sample, never future contact.
                contact_seen=any(any(n.startswith(update.object_id+'_') for n in c['contact_geoms']) for c in phase_controls
                                 if c['physics_time_s']<=r['physics_time_s']+1e-9)
                eligible=dist<.025 and abs(p[2]-g[2])<.025 and speed<.08 and contact_seen
            elif update.requirement=='clearance':
                eligible=r['human_position'][1]>=.80 and r['human_hand_position'][1]>=.75
            else:
                eligible=(any(s['requirement']=='clearance' and s['physical_completion_observed'] for s in stages)
                          and r['human_position'][1]<=.65 and r['human_hand_position'][1]<=.70)
            dwell=dwell+dt if eligible else 0.
            if dwell>=.2-1e-9 and first_completion is None:first_completion=r['time_s']
            previous=r
        stages.append({**asdict(update),'end_s':end,'human_model_decisions':len(selected),
                       'first_matching_action_latency_s':selected_latency,
                       'first_physical_completion_s':first_completion,
                       'physical_completion_latency_s':None if first_completion is None else first_completion-update.time_s,
                       'physical_completion_observed':first_completion is not None,
                       'terminal_requirement_satisfied':dwell>=.2-1e-9,
                       'push_decisions':pushes,'obsolete_or_other_task_push_decisions':stale,
                       'phase_object_contact_witness':witness,'initial_xy_distance_m':initial_distance,
                       'terminal_xy_distance_m':last_distance})
    final_human=stages[-1]['terminal_requirement_satisfied']
    final_robot=bool(placement and placement[-1]['released_stable_placement'])
    contacts=sum(any(('human_fingertip' in str(c['geom1']) and str(c['geom2']).startswith(('robot','gripper')))
                     or ('human_fingertip' in str(c['geom2']) and str(c['geom1']).startswith(('robot','gripper')))
                     for c in r['contacts']) for r in trace)
    return {'stages':stages,'public_work_updates':len(plan),'world_initializations':1,
            'human_policy_resets':1,'human_final_goal_success':bool(final_human),
            'robot_final_goal_success':final_robot,'joint_final_goal_success':bool(final_human and final_robot),
            'physically_completed_stage_count':sum(s['physical_completion_observed'] for s in stages),
            'robot_fingertip_contact_control_samples':contacts,
            'interpretation':'公开工作要求变化下的生成式行为与真实执行测量；阶段完成不等于最终共同完成，动作选择响应不等于物理完成；单卡生成推理期间模拟时钟暂停。'}
