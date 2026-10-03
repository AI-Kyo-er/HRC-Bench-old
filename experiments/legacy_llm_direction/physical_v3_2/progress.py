"""公开历史归约与独立多物品开发fixture；不读取case评分目标。"""
import copy
import json
import math

from experiments.physical.protocol import SYSTEM, ITEMS, TARGETS, candidates


def snapshot_observation(observation):
    """日志必须脱离Episode.events的共享可变列表。"""
    return copy.deepcopy(observation)


def public_progress(observation):
    history = observation['history']
    initial = history[0].split('：', 1)[1].rstrip('。')
    goals = json.loads(initial)
    must_yield, granted = False, False
    for event in history:
        if event.startswith('已接受局部修正：'):
            goals['blue'] = event.split('放到', 1)[1].split('。', 1)[0]
        if '伙伴：我再次占位整理，请先' in event:
            must_yield = True
            granted = False
        if '谢谢让行，已撤离' in event:
            must_yield = False
        if '接受清道协助，已撤离' in event:
            granted = True
    done = {item: goals[item] for item in ITEMS if goals[item] in observation['physical_placements'][item]}
    return {'current_goals_from_public_history': goals,
            'done_under_public_goals': done,
            'remaining_items': [item for item in ITEMS if item not in done],
            'must_yield': must_yield, 'accepted_clearance_help': granted,
            'source': '确定性归约公开历史与物理区域；显式外部进度辅助，不是裸模型输出。'}


def dev_cases():
    """3种已完成物品×目标反转×候选反序，纯接口状态fixture非物理rollout。"""
    cases = []
    for completed in ITEMS:
        for flip in (False, True):
            for reverse in (False, True):
                goals = {'red': 'right' if flip else 'left',
                         'blue': 'left' if flip else 'right',
                         'green': 'right' if flip else 'left'}
                placements = {item: [goals[item]] if item == completed else [] for item in ITEMS}
                objects = {}
                for index, item in enumerate(ITEMS):
                    goal_y = -.25 if goals[item] == 'left' else .25
                    position = ([.59 + .06 * index, goal_y, .032] if item == completed else
                                [.42, -.16 + .16 * index, .022])
                    objects[item] = {'position': position, 'orientation': [0, 0, 0, 1], 'velocity': [0, 0, 0]}
                events = [f'已接受初始指令：{json.dumps(goals, ensure_ascii=False)}。',
                          '未接受建议：green改放另一边。此建议没有被接受。',
                          '伙伴：共享通道已清空，无需请求协助。',
                          f'机器人选择careful_{completed}_{goals[completed]}。反馈：物品静止在目标槽。',
                          f'机器人选择careful_{completed}_{goals[completed]}。反馈：该物品已物理完成，请选择其他未完成物品。']
                obs = {'history': events, 'physical': {'objects': objects,
                       'partner_position': [.54, .6, .24], 'direct_path_blocked': False},
                       'physical_placements': placements, 'remaining_decisions': 8,
                       'candidates': candidates(reverse=reverse)}
                allowed = [f'{mode}_{item}_{goals[item]}' for item in ITEMS if item != completed
                           for mode in ('place', 'careful')]
                cases.append({'id': f'dev_after_{completed}_{int(flip)}_{int(reverse)}',
                              'completed_item': completed, 'flip': flip, 'reverse': reverse,
                              'observation': obs, 'allowed_progress_choices': allowed,
                              'type': '独立人工接口fixture；不是物理执行轨迹，不来自v3.1 formal状态。'})
    return cases


def messages(observation, view):
    obs = copy.deepcopy(observation)
    if view == 'public_progress_aid':
        obs['external_public_progress_aid'] = public_progress(observation)
    elif view != 'full_history':
        raise ValueError(view)
    return [{'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': json.dumps(obs, ensure_ascii=False)}]


def detect_regions(objects):
    placements = {}
    for index, item in enumerate(ITEMS):
        xyz = objects[item]['position']
        speed = math.sqrt(sum(x*x for x in objects[item]['velocity']))
        placements[item] = [target for target in TARGETS if
            math.hypot(xyz[0] - (.59 + .06*index), xyz[1] - (-.25 if target == 'left' else .25)) < .035
            and .025 < xyz[2] < .055 and speed < .04]
    return placements
