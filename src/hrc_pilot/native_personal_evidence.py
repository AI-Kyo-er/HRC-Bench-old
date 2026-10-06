"""模型自选意图的事后可观察测量，不向策略反馈成绩或推荐下一动作。"""
import numpy as np


def signature(targets,regions):
    return tuple(sorted((t['object_id'],*tuple(regions[t['destination']])) for t in targets))


def evaluate_personal_goals(regions,trace,controls,decisions,placement):
    revisions=[];previous=None
    for row in decisions:
        targets=row['personal_goal_state']['personal_targets'];key=signature(targets,regions)
        if key!=previous:
            revisions.append({'start_s':row['time_s'],'targets':targets,'long_term_intention':row['personal_goal_state']['long_term_intention']})
            previous=key
    goals=[]
    for i,revision in enumerate(revisions):
        start=revision['start_s'];end=revisions[i+1]['start_s'] if i+1<len(revisions) else trace[-1]['time_s']
        window=[r for r in trace if start<=r['time_s']<end or (i+1==len(revisions) and r['time_s']==end)]
        for target in revision['targets']:
            obj,dest=target['object_id'],target['destination'];point=np.asarray(regions[dest])
            initial=np.asarray(window[0]['objects'][obj]);distance=float(np.linalg.norm(initial[:2]-point[:2]))
            dwell=0.;first=None;previous_record=None;terminal_distance=None;witness=False
            for r in window:
                position=np.asarray(r['objects'][obj]);terminal_distance=float(np.linalg.norm(position[:2]-point[:2]))
                speed=float(np.linalg.norm(position-np.asarray(previous_record['objects'][obj]))/(r['time_s']-previous_record['time_s'])) if previous_record else float('inf')
                eligible=terminal_distance<.025 and abs(position[2]-point[2])<.025 and speed<.08
                dwell=dwell+.05 if eligible else 0.
                if dwell>=.2-1e-9 and first is None:first=r['time_s']
                previous_record=r
            # This is a contact witness, not causal credit for every displacement.
            relevant=[c for c in controls if window[0]['physics_time_s']<=c['physics_time_s']<=window[-1]['physics_time_s']]
            witness=any(any(n.startswith(obj+'_') for n in c['contact_geoms']) for c in relevant)
            goals.append({**target,'start_s':start,'end_s':end,'initial_xy_distance_m':distance,
                          'already_in_region_when_chosen':distance<.025 and abs(initial[2]-point[2])<.025,
                          'first_stable_relation_s':first,'terminal_relation_satisfied':bool(dwell>=.2-1e-9),
                          'human_contact_in_target_interval':witness,'terminal_xy_distance_m':terminal_distance,
                          'object_displacement_in_target_interval_m':float(np.linalg.norm(np.asarray(window[-1]['objects'][obj])-initial))})
    latest=revisions[-1] if revisions else {'targets':[],'start_s':trace[-1]['time_s']}
    terminal_goals=[g for g in goals if g['start_s']==latest['start_s']]
    evaluable=bool(latest['targets'])
    current_satisfied=bool(evaluable and all(g['terminal_relation_satisfied'] for g in terminal_goals))
    robot=bool(placement and placement[-1]['released_stable_placement'])
    proposals=[m for row in decisions for m in row.get('negotiation_proposal_messages',[])]
    validation_errors=sum(row['personal_goal_state']['target_validation_error'] is not None for row in decisions)
    source_times=[row['time_s'] for row in decisions]
    return {'goal_revisions':revisions,'target_intervals':goals,
            'observable_target_set_changes':max(0,len(revisions)-1),
            'distinct_target_relations':len({signature([g],regions) for g in goals}),
            'target_intervals_with_stable_relation':sum(g['first_stable_relation_s'] is not None for g in goals),
            'new_target_intervals_with_stable_relation':sum(g['first_stable_relation_s'] is not None and not g['already_in_region_when_chosen'] for g in goals),
            'public_negotiation_proposals':len(proposals),'target_validation_errors':validation_errors,
            'human_current_observable_goals_evaluable':evaluable,'human_current_observable_goals_satisfied':current_satisfied,
            'robot_final_released_stable_success':robot,'joint_observable_goals_satisfied':bool(current_satisfied and robot),
            'human_model_calls':len(source_times),'human_generated_goal_decision_times':source_times,
            'interpretation':'仅测量模型自选的可观察物体关系；不将文字改写当目标变化，不将先满足的位置当新贡献，不评判主观意图/人格真实性，不推断机器人接受协商。'}
