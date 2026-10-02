"""中文连续共同活动的决策层切片。环境状态不传给模型适配器。"""
from __future__ import annotations
import copy
import json

DOMAINS = {
    'packing': {'activity': '共同装箱', 'items': ['红杯', '蓝碗', '小盘'], 'locations': ['左箱', '右箱']},
    'table': {'activity': '共同布置餐桌', 'items': ['汤匙', '水杯', '餐巾'], 'locations': ['左餐位', '右餐位']},
    'tools': {'activity': '共同准备工具', 'items': ['扳手', '螺丝刀', '卷尺'], 'locations': ['左工具盒', '右工具盒']},
}
STRUCTURES = ('retain', 'revoke', 'nested', 'reentry', 'nested_reentry')
SYSTEM = '''你是共同活动中的机器人。依据可见历史维护目前有效的约定、分工与已完成进度。建议只有双方明确接受后才生效；未接受建议不能替代已有约定。撤销更新时按对话中恢复的约定执行。局部纠正只影响指定物品。伙伴暂离不会清空进度；返回后的新分工只有接受后才生效。
当前观察会指定本轮物品。只输出一个JSON动作，不要解释、代码围栏或额外键：
{"action":"place","item":"物品名","destination":"位置名","method":"solo"}
{"action":"place","item":"物品名","destination":"位置名","method":"assisted"}
{"action":"request","item":"物品名"}
{"action":"yield","item":"物品名"}
当前物品由机器人负责时可独立放置solo；需要支撑且伙伴在场时可先request，接受支撑后才可assisted。拒绝支撑后仍可solo。伙伴负责当前物品时必须yield，由伙伴实际完成。不得重复处理已经完成的物品。仅返回本次动作，不能输出计划列表。'''


def build_case(domain, structure, variant, split, partner_accepts=True):
    d = DOMAINS[domain]
    items, locations = d['items'], d['locations']
    initial = []
    for i, item in enumerate(items):
        initial.extend([{'kind': 'propose', 'id': f'base{i}', 'item': item,
                         'destination': locations[(i + variant) % 2], 'owner': 'robot'},
                        {'kind': 'accept', 'id': f'base{i}'}])
    # 所有结构都包含尚未接受的干扰建议，防止“最后一句总是真”的捷径。
    before = [[], [], []]
    before[0] = [{'kind': 'propose', 'id': 'pending', 'item': items[0],
                  'destination': locations[1 - variant], 'owner': 'robot'}]
    if structure == 'revoke':
        before[1] = [{'kind': 'propose', 'id': 'change', 'item': items[1],
                       'destination': locations[variant], 'owner': 'robot'},
                      {'kind': 'accept', 'id': 'change'},
                      {'kind': 'revoke', 'id': 'change', 'item': items[1],
                       'destination': locations[1 - variant], 'owner': 'robot'}]
    if structure in ('nested', 'nested_reentry'):
        before[1] = [{'kind': 'propose', 'id': 'local', 'item': items[1],
                       'destination': locations[variant], 'owner': 'robot'},
                      {'kind': 'accept', 'id': 'local'}]
    if structure in ('reentry', 'nested_reentry'):
        before[1].append({'kind': 'availability', 'available': False})
        before[2] = [{'kind': 'availability', 'available': True},
                     {'kind': 'propose', 'id': 'return', 'item': items[2],
                      'destination': locations[variant], 'owner': 'human'},
                     {'kind': 'accept', 'id': 'return'}]
    return {'id': f'{split}.{domain}.{structure}.v{variant}.p{int(partner_accepts)}', 'domain': domain,
            'structure': structure, 'variant': variant, 'split': split,
            'initial_events': initial, 'before_step': before,
            'partner_accepts': partner_accepts}


def render(event):
    kind = event['kind']
    if kind == 'propose':
        actor = '机器人' if event['owner'] == 'robot' else '我'
        return f"伙伴：建议编号{event['id']}：由{actor}把{event['item']}放到{event['destination']}。这目前只是建议，等待双方确认。"
    if kind == 'accept':
        return f"机器人：我接受编号{event['id']}的建议。伙伴：我也确认，双方约定生效。"
    if kind == 'revoke':
        actor = '机器人' if event['owner'] == 'robot' else '伙伴'
        return f"伙伴：撤销编号{event['id']}的更新，{event['item']}恢复为由{actor}放到{event['destination']}。机器人：同意撤销并恢复上述约定。"
    if kind == 'availability':
        return '伙伴：我已返回，可以参与活动。' if event['available'] else '伙伴：我要暂离，暂时不能提供支撑；有效约定和已完成进度不变。'
    if kind == 'completed':
        return f"环境：{event['item']}已由{event['actor']}放到{event['destination']}，完成记录保留。"
    if kind == 'response':
        return f"伙伴：{'接受' if event['accepted'] else '拒绝'}为{event['item']}提供此次支撑。"
    if kind == 'feedback':
        return event['text']
    raise ValueError(kind)


def reference_state(events):
    """独立参考归约器：只能读取公开事件，无case/条件标签/未来伙伴状态。"""
    proposals, agreements, completed = {}, {}, {}
    available = True
    for event in events:
        kind = event['kind']
        if kind == 'propose':
            proposals[event['id']] = dict(item=event['item'], destination=event['destination'], owner=event['owner'])
        elif kind == 'accept':
            proposal = proposals.pop(event['id'])
            agreements[proposal['item']] = dict(destination=proposal['destination'], owner=proposal['owner'])
        elif kind == 'revoke':
            agreements[event['item']] = dict(destination=event['destination'], owner=event['owner'])
            proposals.pop(event['id'], None)
        elif kind == 'availability':
            available = event['available']
        elif kind == 'completed':
            completed[event['item']] = event['destination']
    return {'agreements': agreements, 'pending_proposals': proposals,
            'completed': completed, 'partner_available': available}


def summary_text(events):
    state = reference_state(events)
    lines = ['这是由独立参考规则生成的当前有效状态摘要：']
    for item, agreement in state['agreements'].items():
        owner = '机器人' if agreement['owner'] == 'robot' else '伙伴'
        lines.append(f"已接受约定：{item}由{owner}负责，目的地{agreement['destination']}。")
    for proposal in state['pending_proposals'].values():
        lines.append(f"尚未接受的建议：{proposal['item']}放到{proposal['destination']}，尚未生效。")
    for item, destination in state['completed'].items():
        lines.append(f"已完成：{item}位于{destination}。")
    lines.append('伙伴目前在场。' if state['partner_available'] else '伙伴目前暂离。')
    # 支撑响应属于本轮瞬时信息，同样保留，不能由摘要丢失。
    for event in events:
        if event['kind'] == 'response':
            lines.append(render(event))
    return '\n'.join(lines)


class Episode:
    def __init__(self, case):
        self.case = copy.deepcopy(case)
        self.events = copy.deepcopy(case['initial_events'])
        self.step = -1
        self.granted = False
        self.requests = 0
        self.invalid = 0
        self.parse_errors = 0

    def start_step(self, step):
        self.step = step
        self.granted = False
        self.events.extend(copy.deepcopy(self.case['before_step'][step]))

    def observation(self):
        d = DOMAINS[self.case['domain']]
        item = d['items'][self.step]
        state = reference_state(self.events)
        return f"当前物品：{item}。可用位置：{'、'.join(d['locations'])}。本轮{'需要' if self.step == 1 else '不需要'}支撑。伙伴{'在场' if state['partner_available'] else '暂离'}。支撑{'已接受' if self.granted else '尚未接受'}。请选择本次动作。"

    def messages(self, view):
        d = DOMAINS[self.case['domain']]
        context = '\n'.join(map(render, self.events)) if view == 'full_history' else summary_text(self.events)
        return [{'role': 'system', 'content': SYSTEM},
                {'role': 'user', 'content': f"活动：{d['activity']}。物品：{'、'.join(d['items'])}。\n{context}\n{self.observation()}"}]

    def allowed_actions(self):
        state = reference_state(self.events)
        item = DOMAINS[self.case['domain']]['items'][self.step]
        if item in state['completed']:
            return []
        agreement = state['agreements'][item]
        if agreement['owner'] == 'human':
            return [{'action': 'yield', 'item': item}]
        actions = [{'action': 'place', 'item': item, 'destination': agreement['destination'], 'method': 'solo'}]
        if self.step == 1 and state['partner_available']:
            if self.granted:
                actions.append({'action': 'place', 'item': item, 'destination': agreement['destination'], 'method': 'assisted'})
            else:
                actions.append({'action': 'request', 'item': item})
        return actions

    def act(self, action):
        """伙伴只在实际request/yield时响应；无预录支撑轨迹。"""
        if action not in self.allowed_actions():
            self.invalid += 1
            self.events.append({'kind': 'feedback', 'text': '环境：该动作没有执行，当前物品尚未完成。'})
            return False, True
        item = action['item']
        if action['action'] == 'request':
            self.requests += 1
            self.granted = self.case['partner_accepts']
            self.events.append({'kind': 'response', 'item': item, 'accepted': self.granted})
            return False, False
        state = reference_state(self.events)
        self.events.append({'kind': 'completed', 'item': item,
                            'destination': state['agreements'][item]['destination'],
                            'actor': '伙伴' if action['action'] == 'yield' else '机器人'})
        return True, True


def parse_action(response):
    try:
        action = json.loads(response.strip())
    except json.JSONDecodeError as error:
        return None, f'JSONDecodeError:{error.msg}'
    if not isinstance(action, dict):
        return None, 'not_object'
    schemas = {'place': {'action', 'item', 'destination', 'method'},
               'request': {'action', 'item'}, 'yield': {'action', 'item'}}
    if action.get('action') not in schemas or set(action) != schemas[action['action']]:
        return None, 'schema_error'
    if not all(isinstance(v, str) for v in action.values()):
        return None, 'value_type_error'
    return action, None
