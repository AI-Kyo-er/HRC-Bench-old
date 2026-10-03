"""t0共同活动到停车的实测成本，不从运输启动偷换共同makespan。"""
import copy
import math
from experiments.responsive_transport_v16.world import DT


def review(world,episode):
    final=copy.deepcopy(world.state());event=copy.deepcopy(world.delivery_event);start=world.delivery_start_tick
    red=next((i for i in episode.robot_intervals if i['item']=='red'),None)
    overlap=max(0,min(red['end'],event['first_tick'])-max(red['start'],start)) if red and event else 0
    goal_first=max(world.goal_first_ticks.values()) if {'red','blue'}<=set(world.goal_first_ticks) else None
    green=math.dist(episode.initial_state['objects']['green']['position'],final['objects']['green']['position'])
    return dict(initial_state=episode.initial_state,checkpoint=episode.checkpoint,final_state=final,common_start_tick=world.common_start_tick,end_tick=world.tick,
        closed_task_makespan_ticks=world.tick-world.common_start_tick,closed_task_makespan_seconds=(world.tick-world.common_start_tick)*DT,makespan_includes_final_robot_parking=True,
        delivery_start_tick=start,delivery_event=event,delivery_elapsed_ticks=(event['first_tick']-start if event else None),delivery_from_common_t0_ticks=(event['first_tick']-world.common_start_tick if event else None),
        first_goal_satisfaction_tick=goal_first,first_goal_satisfaction_from_t0_ticks=(goal_first-world.common_start_tick if goal_first is not None else None),goal_first_ticks=copy.deepcopy(world.goal_first_ticks),
        red_skill_transport_overlap_ticks=overlap,overlap_includes_skill_dwell_and_parking=True,
        robot_intervals=episode.robot_intervals,executions=episode.executions,cost=episode.cost,wait_ticks=episode.cost['wait_ticks'],
        green_displacement=green,green_preserved=green<.01,success=episode.success(),public_final_history=episode.history,availability_events=episode.availability_events,
        robot_partner_online=copy.deepcopy(world.contact_audit),other_objects_partner_online=copy.deepcopy(world.object_partner_audit),
        expected_blue_carrier_support_online=copy.deepcopy(world.support_audit),non_target_robot_online=copy.deepcopy(world.non_target_robot_audit),
        body_ids=dict(robot=world.robot,partner=world.partner,objects=dict(world.objects)))
