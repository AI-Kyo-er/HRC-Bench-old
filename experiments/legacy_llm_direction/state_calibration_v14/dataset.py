"""24公开文本字段控制；不执行物理，不把合成观察称为真实轨迹。"""
import copy
import json
import re

from experiments.physical.run import ROOT,save
from experiments.structure_v11.protocol import candidates,reduce_history,update_events
from experiments.state_readout_v13.dataset import state_system
from experiments.structure_v11.protocol import SYSTEM

RESULT=ROOT/'results/state_calibration_v14'
STATE_SYSTEM=state_system(SYSTEM)


def public_truth(observation):
    history=observation['history']
    direct=[e for e in history if e['kind']=='public_state_statement']
    if direct:
        if len(direct)!=1 or len(history)!=2:raise ValueError('直接公开陈述须独立且唯一。')
        text=direct[0]['content']
        outer=re.search(r'有效外层blue投递目标是(left|right)。',text)
        active=re.search(r'局部blue指导当前(活动|不活动)。',text)
        current=re.search(r'blue当前应执行的规范目标是(left|right|neutral)。',text)
        if not all((outer,active,current)):raise ValueError('直接公开状态陈述不完整。')
        truth=dict(outer_blue_destination=outer[1],guidance_active=active[1]=='活动',current_blue_destination=current[1])
        if truth['current_blue_destination']!=('neutral' if truth['guidance_active'] else truth['outer_blue_destination']):
            raise ValueError('公开陈述与协议矛盾。')
        return truth
    ledger=reduce_history(history)
    return dict(outer_blue_destination=ledger['outer']['blue'],guidance_active=ledger['active'],current_blue_destination=ledger['goals']['blue'])


def observation(history,blue_region):
    # 几何事实为明确标注的合成文本，非运行控制器/瞬移物理证据。
    positions={'source':[.42,0,.022],'neutral':[.65,0,.032],'left':[.65,-.26,.032],'right':[.65,.26,.032]}
    obj={item:dict(position=position,orientation=[0,0,0,1],velocity=[0,0,0])
         for item,position in (('red',[.59,-.26,.032]),('blue',positions[blue_region]),('green',[.71,.26,.032]))}
    return dict(history=copy.deepcopy(history),physical=dict(objects=obj,partner_position=[.54,.60,.24],direct_path_blocked=False),
        physical_placements=dict(red=['left'],blue=[] if blue_region=='source' else [blue_region],green=['right']),
        remaining_decisions=12,candidates=candidates(False))


def background():
    return dict(kind='background_source',content='公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。')


def outer_event(target):
    return dict(kind='accepted_outer',goals=dict(red='left',blue=target,green='right'),content='已共同接受blue外层投递目标；当前没有活动的局部blue指导。')


def controls():
    rows=[]
    for target in ('left','right'):
        for active in (False,True):
            current='neutral' if active else target
            for region in ('source','neutral'):
                history=[background(),dict(kind='public_state_statement',content=
                    f'有效外层blue投递目标是{target}。局部blue指导当前'+('活动' if active else '不活动')+
                    f'。blue当前应执行的规范目标是{current}。上述目标是规范要求，实际所在区域不改变该目标。')]
                rows.append(dict(id=f'direct_{target}_{"active" if active else "inactive"}_{region}',group='direct',observation=observation(history,region)))
        for ended in (False,True):
            for region in ('neutral',target):
                history=[background(),outer_event(target),dict(kind='accepted_child',content='已接受blue局部指导并开始：暂存neutral；伙伴检查撤离后可finish_guidance终止。局部指导开始不取消外层约定。')]
                if ended:
                    history.extend([
                        dict(kind='action_feedback',choice='stage_blue_neutral',content='blue已暂存到neutral。'),
                        dict(kind='inspection_started',content='伙伴检查进入共享通道，需要先yield。'),
                        dict(kind='partner_released',by='yield',content='伙伴已撤离共享通道。'),
                        dict(kind='local_check_passed',content='blue在neutral，局部检查通过，可终止指导。'),
                        dict(kind='child_finished',content='finish_guidance已执行，当前局部指导明确终止。'),
                        dict(kind='outer_resumed',content='恢复当时有效外层blue约定，其他分工与进度保留。')])
                    if region!= 'neutral':history.append(dict(kind='action_feedback',choice=f'place_blue_{target}',content=f'指导终止后blue已投递到{target}。'))
                else:
                    history[-1]['content']+='当前尚未检查，也尚未终止；blue实际区域可能仍在原外层盘或已在neutral。'
                rows.append(dict(id=f'scope_{target}_{"ended" if ended else "started"}_{region}',group='scope',observation=observation(history,region)))
        for reply in ('accepted','rejected'):
            for region in ('source','neutral'):
                proposed='right' if target=='left' else 'left'
                history=[background(),outer_event(target)]+update_events(proposed,reply)
                history[2]['content']=f'提议将blue的有效外层投递目标调整为{proposed}；只调整blue外层投递，red/green约定不变。'
                # 原事件词保留；显式说明没有child，更新不会创建局部指导。
                history.append(dict(kind='public_context',content='本例始终没有开始局部blue指导；只处理这一次外层提议与回应。'))
                rows.append(dict(id=f'update_{target}_{reply}_{region}',group='update',observation=observation(history,region)))
    for row in rows:
        obs=row.pop('observation');row.update(messages=[dict(role='system',content=STATE_SYSTEM),dict(role='user',content=json.dumps(obs,ensure_ascii=False))],
            public_state_truth=public_truth(obs),synthetic_text=True,physics_actions_executed=0)
    assert len(rows)==24
    return rows


def build_records():
    records=[]
    for model in ('qwen2_5_14b','qwen3_vl_8b'):
        for row in controls():
            r=copy.deepcopy(row);r.update(model=model,suite='control',query='state_readout',source_id=row['id'],id=f'{model}__{row["id"]}')
            records.append(r)
    path=ROOT/'results/state_readout_v13/raw/frozen_inputs.json'
    for row in json.loads(path.read_text()):
        r=copy.deepcopy(row);r.pop('frozen_input_tokens');r.update(model='qwen3_vl_8b',suite='v13',source_id=row['id'],id=f'qwen3_vl_8b__{row["id"]}')
        records.append(r)
    old=ROOT/'experiments/model_scale_v4/cases/freeze.json'
    for row in json.loads(old.read_text())['records']:
        r=copy.deepcopy(row);r.update(model='qwen3_vl_8b',suite='v4',original_suite=row['suite'],query='action',source_id=row['id'],id=f'qwen3_vl_8b__{row["id"]}')
        records.append(r)
    assert len(records)==216
    return records


def export():
    rows=controls();save(RESULT/'raw/control_inputs_for_review.json',rows)
    parts=['# 24条合成公开状态控制（审核稿，未冻结、未推理）','全部system逐字沿用v13 state；这里只展示完整user与公开归约真值。真值是审核/评分元数据，不传入messages。']
    for r in rows:
        parts.extend([f'## {r["id"]}', '```json',json.dumps(json.loads(r['messages'][1]['content']),ensure_ascii=False,indent=2),'```',
            '公开归约真值：`'+json.dumps(r['public_state_truth'],ensure_ascii=False)+'`'])
    (RESULT/'control_review.md').write_text('\n\n'.join(parts)+'\n')
    print('已导出24控制供审核；未冻结、未推理。',flush=True)


if __name__=='__main__':export()
