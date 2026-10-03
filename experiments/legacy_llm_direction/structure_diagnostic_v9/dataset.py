"""仅从v7真实规范messages构造独立checkpoint输入；aid只读公开观察。"""
import copy
import hashlib
import json
from pathlib import Path

from experiments.physical.run import ROOT,sha
from experiments.structure_v7.protocol import reduce_history

SOURCE_FREEZE=ROOT/'experiments/structure_v7/cases/reference_freeze.json'


def public_aid(observation):
    state=reduce_history(observation['history'])
    goals=state['goals']
    placements=observation['physical_placements']
    done={item:target for item,target in goals.items() if target in placements[item]}
    return dict(current_goals_from_public_history=copy.deepcopy(goals),
        scope=dict(active=state['active'],ended=state['ended'],local_check_passed=state['checked']),
        physical_placements=copy.deepcopy(placements),done_under_current_goals=done,
        remaining_items=[item for item in goals if item not in done],
        obligations=dict(must_yield=state['must_yield'],guidance_pending_termination=state['active']),
        accepted_clearance_help=state['granted'],
        source='确定性归约原始公开约定/反馈和实际几何区域；外部显式辅助，不是裸模型能力，也不读取case/未来/参考动作。')


def aid_messages(messages):
    result=copy.deepcopy(messages)
    observation=json.loads(result[1]['content'])
    if 'external_public_scope_aid' in observation:raise ValueError('原输入已有aid。')
    aid=public_aid(observation)
    # 原始system/history/menu/budget/poses原样；只在原user JSON尾部追加一个字段。
    result[1]['content']=result[1]['content'][:-1]+', "external_public_scope_aid": '+json.dumps(aid,ensure_ascii=False)+'}'
    return result


def build_records():
    frozen=json.loads(SOURCE_FREEZE.read_text())
    records=[];sources={str(SOURCE_FREEZE.relative_to(ROOT)):sha(SOURCE_FREEZE)}
    for case in frozen['cases']:
        path=ROOT/'results/structure_v7/raw/reference'/case['id']/'decisions.json'
        source_rows=json.loads(path.read_text());sources[str(path.relative_to(ROOT))]=sha(path)
        if len(source_rows)!=5:raise ValueError('原v7参考必须恰5决策。')
        for index,row in enumerate(source_rows):
            messages=copy.deepcopy(row['messages']);obs=json.loads(messages[1]['content'])
            state=reduce_history(obs['history'])
            for view in ('full_history','public_scope_aid'):
                records.append(dict(id=f'{case["id"]}__d{index+1:02d}__{view}',source_case_id=case['id'],
                    source_path=str(path.relative_to(ROOT)),source_row_index=index,stage=index+1,view=view,
                    seed=case['seed'],outer_blue=state['outer']['blue'],reverse_menu=case['reverse_menu'],
                    messages=messages if view=='full_history' else aid_messages(messages),
                    menu=copy.deepcopy(obs['candidates']),reference_action=row['result']['choice'],
                    original_messages_sha256=hashlib.sha256(json.dumps(messages,ensure_ascii=False).encode()).hexdigest(),
                    source_before_tick=row['before_tick']))
    if len(records)!=80:raise ValueError('必须40×2=80。')
    return records,sources
