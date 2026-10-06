"""同一物理世界中的活动流；更新公开任务，不重置人、机器人或物体。"""
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np

from .protocol import Message, serialize


def _public_record(world, observation):
    record = serialize(observation)
    record['rgb_artifact'] = world.last_observation_path
    record['wrist_rgb_artifact'] = world.last_wrist_observation_path
    return record


def _physical_state(world):
    observation = world.observe()
    return {'objects': observation.objects, 'robot_qpos': observation.robot_qpos,
            'human_position': observation.human_position, 'time_s': observation.time_s}


def run_activity_stream(scenarios, policy, partner, *, output, backend_factory,
                        instructions, seed=0):
    """仅初始化一次。每次活动结束/到期后发布下一项活动的公开分工。

    策略、伙伴、历史、物体位置与模拟时钟保持连续。新活动清空该活动的贡献账本，
    以免旧操作自动获得新任务的贡献；不改变物体或机械臂状态。
    """
    if not scenarios or len(instructions) != len(scenarios):
        raise ValueError('活动及其公开操作指令必须一一对应')
    if len({scenario.tick_hz for scenario in scenarios}) != 1:
        raise ValueError('活动流中的控制频率必须一致')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if hasattr(partner, 'prepare'):
        partner.prepare()
    world = backend_factory(scenarios[0])
    traces, io, observations, activities, transitions = [], [], [], [], []
    try:
        world.bind_output(output)
        world.reset(seed)
        policy.reset()
        partner.reset(seed)
        for index, scenario in enumerate(scenarios):
            before = _physical_state(world)
            world.scenario = scenario
            world.workspace.scenario = scenario
            partner.scenario = scenario
            policy.instruction = instructions[index]
            world.completed_skills.clear()
            for name in ('contact_grasps', 'human_contact_grasps', 'stable_placements',
                         'last_placement', 'last_grasp_role'):
                getattr(world.workspace, name).clear()
            world.say(Message('environment', 'activity_change',
                              f'当前活动更新：{scenario.description}。以下分工替代上一活动安排。'))
            for message in scenario.initial_messages():
                world.say(message)
            after = _physical_state(world)
            preserved = (before['objects'] == after['objects']
                         and before['robot_qpos'] == after['robot_qpos']
                         and before['human_position'] == after['human_position']
                         and before['time_s'] == after['time_s'])
            if not preserved:
                raise RuntimeError('发布活动时改变了物理状态，不能作为无重置活动流')
            transitions.append({'activity_index': index, 'time_s': before['time_s'],
                                'before': before, 'after': after, 'physical_state_preserved': preserved,
                                'goal_before': partner.current_goal if hasattr(partner, 'current_goal') else None})
            start_time = before['time_s']
            for tick in range(scenario.max_steps):
                observation = world.observe()
                human = partner.step(observation)
                for message in human.messages:
                    world.say(message)
                world.apply_human_command(human.command)
                public = world.observe()
                record = _public_record(world, public)
                action = policy.act(public)
                io.append({'step': public.time_s, 'activity_index': index,
                           'observation': record, 'action': serialize(action),
                           'adapter': policy.audit_record()})
                observations.append(record)
                traces.append({'time_s': public.time_s, 'step': len(traces),
                               'activity_index': index, 'objects': public.objects,
                               'human_action': human.command.intent,
                               'human_object': human.command.object_id,
                               'human_destination': human.command.destination,
                               'held_by_human': public.held_by_human,
                               'human_position': public.human_position,
                               'robot_ee': public.robot_ee, 'robot_qpos': public.robot_qpos,
                               'completed_skills': list(world.completed_skills)})
                world.start_action(action)
                world.tick()
                if world.finished_activity():
                    break
            end = _physical_state(world)
            activities.append({'activity_index': index, 'scenario': scenario.name,
                               'start_time_s': start_time, 'end_time_s': end['time_s'],
                               'duration_s': end['time_s'] - start_time,
                               'task_success': world.finished_activity(),
                               'completed_skills': list(world.completed_skills),
                               'human_goal_at_end': getattr(partner, 'current_goal', None)})
        terminal = world.observe()
        traces.append({'time_s': terminal.time_s, 'step': len(traces), 'terminal': True,
                       'objects': terminal.objects, 'robot_qpos': terminal.robot_qpos,
                       'robot_ee': terminal.robot_ee, 'human_position': terminal.human_position,
                       'held_by_human': terminal.held_by_human})
        events = list(world.events)
        world.finish_episode()
        result = {'scenario': 'continuous_activity_stream', 'seed': seed,
                  'task_success': all(row['task_success'] for row in activities),
                  'completed_skills': [skill for row in activities for skill in row['completed_skills']],
                  'completion_time_s': terminal.time_s, 'activities': activities,
                  'world_initialization_count': 1, 'activity_transition_count': len(transitions),
                  'physical_state_preserved_at_all_transitions': all(row['physical_state_preserved'] for row in transitions),
                  'model_calls': policy.calls, 'native_joint_actions': len(io),
                  'interpretation': '同一世界和模型历史的实际活动流；物理连续不等于可靠HRC能力或真人效度。'}
        audit = partner.audit_state()
        files = {'trace.jsonl': traces, 'policy_io.jsonl': io,
                 'public_observations.jsonl': observations, 'activity_transitions.jsonl': transitions,
                 'events.jsonl': events, 'human_policy_io.jsonl': audit.get('policy_io', []),
                 'human_memory.jsonl': audit.get('memory', []),
                 'public_task_board.jsonl': audit.get('public_task_board', []),
                 'human_memory_retrievals.jsonl': audit.get('memory_retrievals', [])}
        for filename, rows in files.items():
            (output / filename).write_text('\n'.join(json.dumps(row, ensure_ascii=False) for row in rows) + '\n')
        (output / 'metrics.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
        (output / 'activities.json').write_text(json.dumps([asdict(s) for s in scenarios], ensure_ascii=False, indent=2))
        return result
    finally:
        world.close()
