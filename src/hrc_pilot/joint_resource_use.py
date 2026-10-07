"""测量双方对同一资源的执行重叠；不将技能调用直接解释为抓取或碰撞。"""
SKILL_OBJECTS={
    'open_middle_drawer':{'wooden_cabinet_1'},
    'bowl_on_stove':{'akita_black_bowl_1','flat_stove_1'},
    'bottle_on_cabinet':{'wine_bottle_1','wooden_cabinet_1'},
    'bowl_inside_top_drawer':{'akita_black_bowl_1','wooden_cabinet_1'},
    'bowl_on_cabinet':{'akita_black_bowl_1','wooden_cabinet_1'},
    'plate_front_stove':{'plate_1','flat_stove_1'},
    'cream_in_bowl':{'cream_cheese_1','akita_black_bowl_1'},
    'bowl_on_plate':{'akita_black_bowl_1','plate_1'},
    'bottle_on_rack':{'wine_bottle_1','wine_rack_1'},
}


def resource_use_evidence(trace,controls,calls,plans):
    by_call={c['call_id']:c for c in calls};by_plan={p['decision_id']:p for p in plans}
    intervals=[];active=None;unknown_steps=0
    for index,control in enumerate(controls):
        row=trace[index];call=by_call[control['model_call_id']]
        plan=by_plan.get(call.get('coordinator_decision_id'),{})
        skill=plan.get('model_selected_skill_id');targets=SKILL_OBJECTS.get(skill)
        actual_vla=control['source'] in {'actual_vla_coordinator_instruction','actual_vla_public_dialogue'}
        if actual_vla and targets is None:unknown_steps+=1
        execution=row['human_execution'];held=execution.get('held_object')
        owned=set(execution.get('carried_objects',[held] if held else []))
        overlap=sorted(owned.intersection(targets or ())) if actual_vla else []
        key=(skill,tuple(overlap),execution.get('active_request_id')) if overlap else None
        end=trace[index+1]['time_s']
        if key is not None and active and active['_key']==key:active['end_s']=end
        else:
            if active:intervals.append(active)
            active=({'start_s':row['time_s'],'end_s':end,'robot_skill_id':skill,
                     'human_owned_objects':overlap,'human_motion_request_id':execution.get('active_request_id'),'_key':key}
                    if key is not None else None)
    if active:intervals.append(active)
    for item in intervals:item.pop('_key')
    return {'intervals':intervals,'same_resource_vla_exposure_s':sum(i['end_s']-i['start_s'] for i in intervals),
        'unmapped_vla_control_steps':unknown_steps,
        'scope':'实际VLA执行期间，所选技能涉及人正在持有／携带的物品。不是实际抓取、碰撞或自动安全失败标签；持物附着有已披露的物理简化。',
        'coordination_score':None}
