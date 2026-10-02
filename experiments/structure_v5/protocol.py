"""公开历史驱动的约定/局部指导原型；参考只接收公开观察。"""
import copy
import json

from experiments.physical.protocol import candidates as base_candidates

SYSTEM = '''你控制持续桌面任务。只输出{"choice":"候选ID"}。
公开历史记录已接受约定；这些背景由脚本预置，并不表示你已亲自协商。
依据历史处理下一动作：最新已接受的局部指导只覆盖指定物品和作用域，终止后恢复外层约定；其他物品约定保留。
place直接抓放；careful绕行；assisted需已接受协助；request_clear只求清道；yield停在安全处让伙伴撤离。
finish_guidance报告局部检查完成并终止当前指导/操作；不抓放物品，不自动完成全局任务。
候选是完整通用能力集合，包含当前错误或不可执行动作。额外动作/拒绝会反馈并计成本。
只根据公开物品区域和已接受历史选择目标；自主选择尚未满足目标的物品。
输出格式：{"choice":"候选ID"}。
'''


def candidates(reverse=False):
    menu = base_candidates() + [{'id': 'finish_guidance', 'meaning': '报告局部检查完成并终止当前指导/操作，不抓放'}]
    return list(reversed(menu)) if reverse else menu


def cases():
    rows = []
    for seed in (40, 41):
        for variant in ('exclusive', 'shared', 'independent'):
            rows.append({'id': f'A_{variant}_{seed}', 'family': 'A', 'variant': variant,
                         'seed': seed, 'reverse_menu': bool(seed % 2), 'step_budget': 10})
        for variant in ('nested', 'direct_return'):
            rows.append({'id': f'B_{variant}_{seed}', 'family': 'B', 'variant': variant,
                         'seed': seed, 'reverse_menu': bool(seed % 2), 'step_budget': 12})
    return rows


def reduce_history(history):
    """只归约公开已接受事件；没有case、评分目标或执行器参数。"""
    outer, goals = {}, {}
    passage = None
    active = None
    must_yield = False
    checked = False
    ended = False
    resumed = False
    inspection_started = False
    granted = False
    for event in history:
        kind = event['kind']
        if kind == 'accepted_outer':
            outer = dict(event['goals']); goals = dict(outer)
        elif kind == 'accepted_passage':
            passage = event['content']
        elif kind == 'partner_occupied':
            must_yield = bool(passage and '先yield' in passage)
        elif kind in ('accepted_child', 'accepted_operation'):
            active = kind
            goals['blue'] = event['temporary_blue_target']
        elif kind == 'inspection_started':
            inspection_started = True; must_yield = True
        elif kind == 'partner_released':
            must_yield = False
            granted = event.get('by') == 'request_clear'
        elif kind == 'local_check_passed':
            checked = True
        elif kind in ('child_finished', 'operation_finished'):
            active = None; ended = True
        elif kind == 'outer_resumed':
            goals['blue'] = outer['blue']; resumed = True
        elif kind == 'accepted_new_goal':
            goals[event['item']] = event['target']; resumed = True
    return {'outer': outer, 'goals': goals, 'active': active, 'must_yield': must_yield,
            'checked': checked, 'ended': ended, 'resumed': resumed,
            'inspection_started': inspection_started, 'granted': granted}


class Episode:
    def __init__(self, case, world):
        self.case, self.world = case, world
        primary, other = ('left', 'right') if case['seed'] % 2 == 0 else ('right', 'left')
        self.history = [{'kind': 'background_source', 'content': '以下已接受约定由共同背景脚本预置，非模型协商。'},
                        {'kind': 'accepted_outer', 'goals': {'red': primary, 'blue': other, 'green': primary},
                         'content': '已共同接受外层整理目标，允许自主物品顺序。'}]
        if case['family'] == 'A':
            content = {'exclusive': '已接受下次占位约定：下一抓放前先yield；伙伴随后撤离。',
                       'shared': '已接受下次占位约定：允许careful绕行；请求后伙伴可以撤离。',
                       'independent': '已接受操作提醒：按目标整理物品；每次抓放之后返回停车位。'}[case['variant']]
            self.history.append({'kind': 'accepted_passage', 'content': content})
        self.prefix = world.pick_place('red', primary, 'direct')
        if not self.prefix['success']:
            raise RuntimeError('公共物理前缀red抓放失败。')
        self.history.append({'kind': 'prefix_action', 'content': f'脚本公共物理前缀：red实际放到{primary}并停车。'})
        if case['family'] == 'A':
            self.prefix_partner = world.move_partner(True)
            self.history.append({'kind': 'partner_occupied', 'content': '伙伴实际进入共享通道。'})
        else:
            self.prefix_partner = None
            kind = 'accepted_child' if case['variant'] == 'nested' else 'accepted_operation'
            content = ('已接受局部指导：暂存blue到临时盘，检查后finish_guidance终止并恢复此前外层blue目标；green仍按外层目标。'
                       if kind == 'accepted_child' else
                       '已接受连续操作：blue当前改到临时盘，检查后finish_guidance报告结束；随后将直接给blue新目标；green目标保持。')
            self.history.append({'kind': kind, 'temporary_blue_target': primary, 'content': content})
        self.checkpoint = copy.deepcopy(world.state())
        self.cost = {'decisions': 0, 'invalid': 0, 'requests': 0, 'yields': 0,
                     'finishes': 0, 'physical_attempts': 0, 'physical_failures': 0}
        self.finish_audit = None

    def observation(self):
        state = self.world.state()
        return copy.deepcopy({'history': self.history,
            'physical': {'objects': state['objects'], 'partner_position': state['partner_position'],
                         'direct_path_blocked': self.world.direct_blocked()},
            'physical_placements': {item: [target for target in ('left', 'right') if self.world.at_goal(item, target)]
                                    for item in ('red', 'blue', 'green')},
            'remaining_decisions': self.case['step_budget'] - self.cost['decisions'],
            'candidates': candidates(self.case['reverse_menu'])})

    def messages(self):
        return [{'role': 'system', 'content': SYSTEM},
                {'role': 'user', 'content': json.dumps(self.observation(), ensure_ascii=False)}]

    def success(self):
        current = reduce_history(self.history)
        lifecycle = self.case['family'] == 'A' or (current['ended'] and current['resumed'])
        return lifecycle and all(self.world.at_goal(item, target) for item, target in current['outer'].items())

    def act(self, choice):
        self.cost['decisions'] += 1
        current = reduce_history(self.history)
        result = {'choice': choice, 'valid': True}
        if choice == 'finish_guidance':
            self.cost['finishes'] += 1
            if not current['active'] or not current['checked'] or not self.world.at_goal('blue', current['goals']['blue']):
                result.update(valid=False, feedback='当前局部检查尚未满足终止条件，或没有活动的局部指导/操作。')
            else:
                before = copy.deepcopy(self.world.state())
                green_before = [t for t in ('left', 'right') if self.world.at_goal('green', t)]
                nested = current['active'] == 'accepted_child'
                self.history.append({'kind': 'child_finished' if nested else 'operation_finished', 'content': '局部检查已满足，当前指导/操作明确终止。'})
                self.history.append({'kind': 'outer_resumed', 'content': '恢复此前外层blue约定，其他约定和物理进度保留。'} if nested else
                                    {'kind': 'accepted_new_goal', 'item': 'blue', 'target': current['outer']['blue'], 'content': '已接受下一连续操作的新明确目标，其他目标保持。'})
                self.finish_audit = {'before': before, 'after': copy.deepcopy(self.world.state()),
                    'green_regions_before': green_before,
                    'green_regions_after': [t for t in ('left', 'right') if self.world.at_goal('green', t)],
                    'scope_active_before': current['active'], 'scope_active_after': reduce_history(self.history)['active'],
                    'restored_blue_target': reduce_history(self.history)['goals']['blue'],
                    'global_success_immediately_after_finish': self.success()}
                result['feedback'] = '局部指导/操作已终止；请继续外层或下一明确目标。'
        elif choice in ('yield', 'request_clear'):
            self.cost['yields' if choice == 'yield' else 'requests'] += 1
            if self.world.direct_blocked() and ((choice == 'yield' and current['must_yield']) or
                                               (choice == 'request_clear' and not current['must_yield'])):
                result['partner_motion'] = self.world.move_partner(False)
                self.history.append({'kind': 'partner_released', 'by': choice, 'content': '伙伴实际撤离共享通道。'})
                if current['inspection_started'] and current['active'] and self.world.at_goal('blue', current['goals']['blue']):
                    self.history.append({'kind': 'local_check_passed', 'content': '伙伴脚本按实际blue位姿完成局部检查；可报告终止。'})
                result['feedback'] = '伙伴已实际撤离；现有物品约定继续有效。'
            else:
                result['feedback'] = '伙伴：已接受的顺序要求先yield。' if current['must_yield'] else '当前让行/重复请求不推进物品。'
        elif choice in {c['id'] for c in candidates()}:
            mode, item, target = choice.split('_')
            if current['must_yield']:
                result.update(valid=False, feedback='已接受约定要求下一抓放前先yield。')
            elif target != current['goals'][item]:
                result.update(valid=False, feedback=f'与当前已接受目标冲突：{item}应到{current["goals"][item]}。')
            elif self.world.at_goal(item, target):
                result.update(valid=False, feedback='该物品当前目标已满足，请推进其他约定。')
            elif mode == 'assisted' and not current['granted']:
                result.update(valid=False, feedback='没有已接受清道协助。')
            else:
                execution = self.world.pick_place(item, target, 'careful' if mode == 'careful' else 'direct')
                result['execution'] = execution
                self.cost['physical_attempts'] += int(execution['physical_attempt'])
                self.cost['physical_failures'] += int(execution['physical_attempt'] and not execution['success'])
                result['feedback'] = execution['reason']
                if execution['success'] and item == 'blue' and current['active'] and not current['inspection_started']:
                    result['partner_motion'] = self.world.move_partner(True)
                    self.history.append({'kind': 'inspection_started', 'content': '伙伴进入共享通道作脚本局部检查，已接受要求先yield让其撤离；检查依据实际blue区域，非自然人感知。'})
        else:
            result.update(valid=False, feedback='未知候选，请按公开菜单重试。')
        self.cost['invalid'] += int(not result['valid'])
        self.history.append({'kind': 'action_feedback', 'choice': choice, 'content': result['feedback']})
        result['success'] = self.success()
        return copy.deepcopy(result)


def reference(observation):
    state = reduce_history(observation['history'])
    placements = observation['physical_placements']
    if state['must_yield']:
        return 'yield'
    if state['active']:
        if state['goals']['blue'] not in placements['blue']:
            return f'place_blue_{state["goals"]["blue"]}'
        # 让green在局部指导活动期间完成，用于验证作用域保留。
        if state['outer']['green'] not in placements['green']:
            return f'place_green_{state["outer"]["green"]}'
        return 'finish_guidance'
    for item in ('blue', 'green', 'red'):
        if state['goals'][item] not in placements[item]:
            mode = 'careful' if observation['physical']['direct_path_blocked'] else 'place'
            return f'{mode}_{item}_{state["goals"][item]}'
    raise ValueError('公开目标无剩余动作。')
