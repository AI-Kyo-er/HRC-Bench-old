"""全部v11 D4/D5，正常原输入和离线反菜单；公开ledger辅助不读私有标签。"""
import copy
import json

from experiments.physical.run import ROOT,sha
from experiments.structure_v11.protocol import reduce_history

SOURCE_FREEZE=ROOT/'experiments/structure_v11/cases/reference_freeze.json'


def public_aid(observation):
    state=reduce_history(observation['history']);goals=state['goals'];regions=observation['physical_placements']
    done={item:target for item,target in goals.items() if target in regions[item]}
    return dict(current_goals_from_public_history=copy.deepcopy(goals),
        scope=dict(active=state['active'],ended=state['ended'],local_check_passed=state['checked']),
        done_under_current_goals=done,remaining_items=[item for item in goals if item not in done],
        obligations=dict(must_yield=state['must_yield'],guidance_pending_termination=state['active']),
        accepted_clearance_help=state['granted'],
        source='确定性归约原始公开约定/反馈和实际几何区域；外部显式辅助，不是裸模型能力，也不读取case/未来/参考动作。')


def menu_messages(messages,reverse):
    result=copy.deepcopy(messages)
    if reverse:
        obs=json.loads(result[1]['content']);old=json.dumps(obs['candidates'],ensure_ascii=False)
        assert result[1]['content'].count(old)==1
        result[1]['content']=result[1]['content'].replace(old,json.dumps(list(reversed(obs['candidates'])),ensure_ascii=False),1)
    return result


def aid_messages(messages):
    result=copy.deepcopy(messages);obs=json.loads(result[1]['content'])
    assert 'external_public_scope_aid' not in obs
    result[1]['content']=result[1]['content'][:-1]+', "external_public_scope_aid": '+json.dumps(public_aid(obs),ensure_ascii=False)+'}'
    return result


def build_records():
    frozen=json.loads(SOURCE_FREEZE.read_text());sources={str(SOURCE_FREEZE.relative_to(ROOT)):sha(SOURCE_FREEZE)};records=[]
    for case in frozen['cases']:
        path=ROOT/'results/structure_v11/raw/reference'/case['id']/'decisions.json'
        rows=json.loads(path.read_text());assert len(rows)==5;sources[str(path.relative_to(ROOT))]=sha(path)
        for index in (3,4):
            row=rows[index];obs=json.loads(row['messages'][1]['content']);history=obs['history'];state=reduce_history(history)
            proposal_index=next(i for i,e in enumerate(history) if e['kind']=='update_proposed')
            child_index=next(i for i,e in enumerate(history) if e['kind']=='accepted_child')
            decision=next(e['decision'] for e in history if e['kind']=='proposal_reply')
            initial=next(e['goals']['blue'] for e in history if e['kind']=='accepted_outer')
            for reverse in (False,True):
                full=menu_messages(row['messages'],reverse)
                for view in ('full_history','public_scope_aid'):
                    messages=full if view=='full_history' else aid_messages(full)
                    records.append(dict(id=f"{case['id']}__d{index+1:02d}__{'reverse' if reverse else 'normal'}__{view}",
                        source_case_id=case['id'],source_path=str(path.relative_to(ROOT)),source_row_index=index,stage=index+1,
                        seed=case['seed'],timing='before_child' if proposal_index<child_index else 'during_child',
                        acceptance='accepted' if decision=='accept' else 'rejected',initial_blue=initial,effective_blue=state['outer']['blue'],
                        reverse_menu=reverse,view=view,messages=copy.deepcopy(messages),menu=json.loads(messages[1]['content'])['candidates'],
                        reference_action=row['result']['choice'],source_before_tick=row['before_tick']))
    assert len(records)==128
    return records,sources
