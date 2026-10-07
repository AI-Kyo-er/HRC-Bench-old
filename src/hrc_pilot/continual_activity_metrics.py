"""持续共同活动的事后测量；不生成目标、动作或运行时反馈。"""
import numpy as np

from .native_goal_evidence import goal_success


def evaluate_continual_activity(trace,decisions,regions,placement):
    """逐时刻分别测量双方目标、无目标时间、丢失维持关系与新贡献。"""
    scores={r['time_s']:goal_success(r) for r in placement}
    current=[];index=0;dwell={};previous_signature=None;records=[]
    evaluable_time=human_time=robot_time=joint_time=0.
    robot_was_done=False;robot_loss_count=0;last_joint=False;joint_loss_count=0
    signatures=[];new_relations=set();first_joint=None
    for previous,row in zip(trace,trace[1:]):
        now=row['time_s'];dt=now-previous['time_s'];assert dt>0
        while index<len(decisions) and decisions[index]['time_s']<=previous['time_s']+1e-9:
            current=decisions[index]['personal_goal_state']['personal_targets'];index+=1
        # Regional aliases are identical relations, not intention changes.
        signature=tuple(sorted((t['object_id'],t['destination']) if t['destination'].startswith('on:') else (t['object_id'],*regions[t['destination']]) for t in current))
        if signature!=previous_signature:
            dwell={};previous_signature=signature;signatures.append(signature)
        target_records=[]
        for target in current:
            name,dest=target['object_id'],target['destination'];receiver=dest.split(':',1)[1] if dest.startswith('on:') else None
            point=np.asarray(row['objects'][receiver] if receiver else regions[dest])
            position=np.asarray(row['objects'][name]);old=np.asarray(previous['objects'][name]);speed=float(np.linalg.norm(position-old)/dt)
            support=touch=False
            for c in row['contacts']:
                a,b=c['geom1'] or '',c['geom2'] or ''
                if b.startswith(name+'_'):a,b=b,a
                if a.startswith(name+'_'):
                    support|=b.startswith(receiver+'_') if receiver else b==('human_storage_support' if dest.endswith('_shelf') else 'table_collision')
                    touch|=b.startswith(('gripper','human_left_finger','human_right_finger','human_palm','human_fingertip'))
            spatial=(np.linalg.norm(position[:2]-point[:2])<(.03 if receiver else .025)
                     and (position[2]>=point[2] if receiver else abs(position[2]-point[2])<.025))
            receiver_speed=float(np.linalg.norm(point-np.asarray(previous['objects'][receiver]))/dt) if receiver else 0.
            key=(name,dest) if receiver else (name,*regions[dest]);dwell[key]=dwell.get(key,0.)+dt if spatial and support and not touch and max(speed,receiver_speed)<.08 else 0.
            stable=bool(dwell[key]>=.2-1e-9)
            if stable:
                initial=np.asarray(trace[0]['objects'][name])
                baseline=np.asarray(trace[0]['objects'][receiver]) if receiver else point
                initially_spatial=(np.linalg.norm(initial[:2]-baseline[:2])<(.03 if receiver else .025)
                    and (initial[2]>=baseline[2] if receiver else abs(initial[2]-baseline[2])<.025))
                if receiver:
                    initial_support=initial_touch=False
                    for pair in trace[0]['contacts']:
                        a,b=pair['geom1'] or '',pair['geom2'] or ''
                        if b.startswith(name+'_'):a,b=b,a
                        if a.startswith(name+'_'):
                            initial_support|=b.startswith(receiver+'_')
                            initial_touch|=b.startswith(('gripper','human_left_finger','human_right_finger','human_palm','human_fingertip'))
                    initially_spatial=initially_spatial and initial_support and not initial_touch
                if not initially_spatial:new_relations.add(key)
            target_records.append({**target,'actual_support_contact':support,'any_hand_contact':touch,
                                   'object_speed_m_s':speed,'spatial_relation':bool(spatial),
                                   'stable_duration_s':dwell[key],'released_stable_relation':stable})
        evaluable=bool(current);human=bool(evaluable and all(t['released_stable_relation'] for t in target_records))
        robot=scores.get(now,False);joint=bool(human and robot)
        if robot_was_done and not robot:robot_loss_count+=1
        if last_joint and not joint:joint_loss_count+=1
        robot_was_done=robot;last_joint=joint
        evaluable_time+=dt if evaluable else 0.;human_time+=dt if human else 0.;robot_time+=dt if robot else 0.;joint_time+=dt if joint else 0.
        if joint and first_joint is None:first_joint=now
        records.append({'time_s':now,'active_personal_targets':current,'target_relations':target_records,
                        'human_goal_evaluable':evaluable,'human_released_stable_goals':human,
                        'robot_physical_goal':robot,'joint_released_stable_goals':joint})
    duration=trace[-1]['time_s']-trace[0]['time_s'];assert duration>0
    return {'duration_s':duration,'human_goal_evaluable_time_s':evaluable_time,
            'human_goal_unevaluable_time_s':duration-evaluable_time,'human_released_goal_time_s':human_time,
            'robot_physical_goal_time_s':robot_time,'joint_released_goal_time_s':joint_time,
            'joint_fraction_of_evaluable_time':joint_time/evaluable_time if evaluable_time else None,
            'first_joint_released_stable_s':first_joint,'final_joint_released_stable':records[-1]['joint_released_stable_goals'],
            'robot_goal_loss_transitions':robot_loss_count,'joint_goal_loss_transitions':joint_loss_count,
            'semantic_target_set_changes':max(0,len(signatures)-1),'new_relations_from_episode_start_count':len(new_relations),
            'records':records,'criterion_version':'continuous_support_release_v1',
            'interpretation':'事后实测当前生成目标的释放稳定关系和持续时长；空目标不算成功，改写别名不算意图变化，先已满足的位置不计新关系。目标变化可能改变可评分时间，不将比率直接当人格／主观满足或算法排名。'}
