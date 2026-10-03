"""公开候选接口；候选只使用对象/区域枚举，不使用有效目标或伙伴私有回应。"""
import json

ITEMS = ('red', 'blue', 'green')
TARGETS = ('left', 'right')
PROMPT_VERSION = 'public-choice-v3.1'
SYSTEM = '''你控制桌面整理机器人。只输出一个JSON对象：{"choice":"候选ID"}，不要解释。
从公开候选选下一动作，使所有物品符合最新已接受指令，并遵守伙伴明确的先让行要求。
放置前先读取该物品已接受的目标字符串left或right，所选ID末尾必须匹配它；菜单顺序不改变目标。
候选列表只是通用能力菜单，包含错误目标和暂不可执行动作，不是正确答案列表。
place独立直接放置；careful独立绕开共享通道；assisted使用已接受的协助直接放置。
request_clear只请求伙伴移开占位物，不执行放置，不是通用的搬运命令；已清空时重复请求无帮助。
yield只停在安全位置让伙伴撤离占位物，不完成任何物品。拒绝后可用careful绕行。
额外请求、无效选择和失败会给反馈并消耗1步，可重试。自主选择下一未完成物品。
示例：选择把green独立绕行放到right，输出{"choice":"careful_green_right"}。
'''


def candidates(items=ITEMS, reverse=False):
    result = []
    for item in items:
        for target in TARGETS:
            for mode, label in (('place', '独立沿共享通道抓放'),
                                 ('careful', '独立绕行抓放'),
                                 ('assisted', '利用已接受的清道协助抓放')):
                result.append({'id': f'{mode}_{item}_{target}',
                               'meaning': f'{label} {item} 到 {target}'})
    result.extend([{'id': 'request_clear', 'meaning': '请求伙伴释放共享通道；不放置任何物品'},
                   {'id': 'yield', 'meaning': '让伙伴先撤离占位物；不放置任何物品'}])
    return list(reversed(result)) if reverse else result


def parse(response, menu):
    try:
        obj = json.loads(response)
        if not isinstance(obj, dict) or set(obj) != {'choice'} or not isinstance(obj['choice'], str):
            raise ValueError('需要唯一字符串字段choice')
        if obj['choice'] not in {x['id'] for x in menu}:
            raise ValueError('choice不在公开候选中')
        return obj['choice'], None
    except (ValueError, TypeError) as exc:
        return None, str(exc)


def calibration_cases():
    """独立开发接口诊断：目标反转、候选重排，4种基础状态。"""
    cases = []
    for mode in ('solo', 'assisted', 'yield', 'refusal'):
        for target in TARGETS:
            for reverse in (False, True):
                menu = candidates(('blue',), reverse)
                facts = f'只有blue尚未完成。已接受指令：blue放到{target}。'
                if mode == 'solo':
                    facts += '共享通道已清空，无需协助，伙伴无分工。现在执行放置。'
                    allowed = {f'place_blue_{target}', f'careful_blue_{target}'}
                elif mode == 'assisted':
                    facts += '伙伴已接受清道协助且实际撤离，共享通道清空，可以直接或绕行放置。'
                    allowed = {f'place_blue_{target}', f'careful_blue_{target}', f'assisted_blue_{target}'}
                elif mode == 'yield':
                    facts += '伙伴正在占位。伙伴明确要求：先停在安全位置让我撤离，当前禁止抓放。'
                    allowed = {'yield'}
                else:
                    facts += '此前你请求清道。伙伴已拒绝，仍占用共享通道；伙伴没有要求先让行。现在通过独立绕行完成物品。'
                    allowed = {f'careful_blue_{target}'}
                cases.append({'id': f'dev_{mode}_{target}_{int(reverse)}', 'mode': mode,
                              'facts': facts, 'menu': menu, 'allowed': sorted(allowed)})
    return cases


def calibration_messages(case):
    return [{'role': 'system', 'content': SYSTEM}, {'role': 'user',
             'content': case['facts'] + '\n公开候选：' + json.dumps(case['menu'], ensure_ascii=False)}]


def formal_cases():
    cases = []
    for seed in (10, 11):
        for accepts in (False, True):
            for condition in ('upfront', 'revision'):
                cases.append({'id': f'formal_{condition}_{seed}_{int(accepts)}',
                              'condition': condition, 'seed': seed,
                              'partner_accepts': accepts, 'reverse_menu': bool(seed % 2),
                              'step_budget': 12})
    return cases


class Episode:
    def __init__(self, case, world):
        self.case = case
        self.world = world
        left, right = ('left', 'right') if case['seed'] % 2 == 0 else ('right', 'left')
        self.final = {'red': left, 'blue': left, 'green': right}
        self.goals = dict(self.final)
        if case['condition'] == 'revision':
            self.goals['blue'] = right
        self.events = [f'已接受初始指令：{json.dumps(self.goals, ensure_ascii=False)}。',
                       '未接受建议：green改放另一边。此建议没有被接受。',
                       '伙伴：你可以自主选择未完成物品。共享通道当前清空。']
        self.intervened = False
        self.granted = False
        self.must_yield = False
        self.cost = {'decisions': 0, 'requests': 0, 'yields': 0, 'invalid': 0,
                     'physical_attempts': 0, 'physical_failures': 0, 'redundant_requests': 0}

    def completed(self):
        return {item: self.goals[item] for item in ITEMS if self.world.at_goal(item, self.goals[item])}

    def success(self):
        return self.intervened and self.goals == self.final and len(self.completed()) == 3

    def observation(self):
        # 只给实际几何区域，不给按评分目标判定的已完成标志。
        state = self.world.state()
        return {'history': self.events, 'physical': {'objects': state['objects'],
                'partner_position': state['partner_position'],
                'direct_path_blocked': self.world.direct_blocked()},
                'physical_placements': {item: [target for target in TARGETS
                                               if self.world.at_goal(item, target)]
                                        for item in ITEMS},
                'remaining_decisions': self.case['step_budget'] - self.cost['decisions'],
                'candidates': candidates(reverse=self.case['reverse_menu'])}

    def messages(self):
        return [{'role': 'system', 'content': SYSTEM}, {'role': 'user',
                 'content': json.dumps(self.observation(), ensure_ascii=False)}]

    def act(self, choice):
        self.cost['decisions'] += 1
        result = {'choice': choice, 'valid': True}
        if choice is None:
            result.update(valid=False, feedback='无法解析动作，请按公开JSON接口重试。')
        elif choice == 'request_clear':
            self.cost['requests'] += 1
            if not self.world.direct_blocked():
                self.cost['redundant_requests'] += 1
                result['feedback'] = '伙伴：共享通道已经清空，无需再请求。请直接推进物品。'
            elif self.case['partner_accepts']:
                self.granted = True
                result['partner_motion'] = self.world.move_partner(False)
                result['feedback'] = '伙伴：接受清道协助，已撤离。现在可以直接放置。'
            else:
                result['feedback'] = '伙伴：拒绝清道请求。我仍占位，你可独立careful绕行。'
        elif choice == 'yield':
            self.cost['yields'] += 1
            if self.must_yield:
                result['partner_motion'] = self.world.move_partner(False)
                self.must_yield = False
                result['feedback'] = '伙伴：谢谢让行，已撤离；先前其他约定继续有效。'
            else:
                result['feedback'] = '伙伴：当前没有待撤离承诺，让行不推进物品。'
        else:
            mode, item, target = choice.split('_')
            if self.must_yield:
                result.update(valid=False, feedback='伙伴已要求先让行撤离；当前禁止抓放，请yield。')
            elif target != self.goals[item]:
                result.update(valid=False, feedback=f'目标与已接受指令冲突：{item}应到{self.goals[item]}，可重试。')
            elif self.world.at_goal(item, target):
                result.update(valid=False, feedback='该物品已物理完成，请选择其他未完成物品。')
            elif mode == 'assisted' and not self.granted:
                result.update(valid=False, feedback='没有已接受的清道协助，可请求或独立绕行。')
            else:
                physics = self.world.pick_place(item, target, 'careful' if mode == 'careful' else 'direct')
                result['execution'] = physics
                self.cost['physical_attempts'] += int(physics['physical_attempt'])
                self.cost['physical_failures'] += int(physics['physical_attempt'] and not physics['success'])
                result['feedback'] = physics['reason']
                if physics['success'] and not self.intervened:
                    self.intervened = True
                    self.goals = dict(self.final)
                    result['partner_motion'] = self.world.move_partner(True)
                    correction = f'已接受局部修正：blue最终放到{self.final["blue"]}。' if self.case['condition'] == 'revision' else '已接受确认：所有目标保持最初指令。'
                    self.events.append(correction + '其他物品约定与物理进度保留。伙伴进入共享通道。')
                elif physics['success'] and len(self.completed()) == 2:
                    result['partner_motion'] = self.world.move_partner(True)
                    self.granted = False
                    self.must_yield = True
                    self.events.append('伙伴：我再次占位整理，请先停在安全位置让我撤离；当前禁止抓放。')
        if not result['valid']:
            self.cost['invalid'] += 1
        self.events.append(f'机器人选择{choice}。反馈：{result["feedback"]}')
        result['completed'] = self.completed()
        result['success'] = self.success()
        return result


def reference(observation):
    """仅接收公开观察，与模型共享能力菜单与执行器。"""
    history = observation['history']
    # 自事件归约当前已接受约定，不接受case、隐藏伙伴回应或Episode对象。
    initial = history[0].split('：', 1)[1].rstrip('。')
    goals = json.loads(initial)
    must_yield = False
    granted = False
    refused = False
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
        if '拒绝清道请求' in event:
            refused = True
    if must_yield:
        return 'yield'
    if observation['physical']['direct_path_blocked'] and not refused:
        return 'request_clear'
    for item in ITEMS:
        if goals[item] not in observation['physical_placements'][item]:
            mode = 'careful' if observation['physical']['direct_path_blocked'] else ('assisted' if granted else 'place')
            return f'{mode}_{item}_{goals[item]}'
    raise ValueError('没有剩余子任务')
