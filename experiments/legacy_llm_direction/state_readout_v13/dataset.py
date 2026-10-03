"""原action64重放及同user状态query；只替换三个system任务/输出指令。"""
import copy
import json

from experiments.physical.run import ROOT,sha
from experiments.structure_v11.protocol import reduce_history

V12_INPUTS=ROOT/'results/structure_diagnostic_v12/raw/frozen_inputs.json'
V12_FREEZE=ROOT/'experiments/structure_diagnostic_v12/cases/freeze.json'
REPLACEMENTS=(
    ('你控制持续桌面任务。只输出{"choice":"候选ID"}。',
     '你读取持续桌面任务的公开观察。只输出一个严格JSON对象，按outer_blue_destination、guidance_active、current_blue_destination的键顺序。'),
    ('依据公开原始历史和真实区域继续任务，自主选择尚未满足约定的物品。',
     '依据公开原始历史和真实区域报告最新有效外层blue投递目标、局部指导是否仍活动、当前blue执行目标。不输出动作或分析。'),
    ('输出格式：{"choice":"候选ID"}。',
     '输出字段与类型：outer_blue_destination是left或right字符串；guidance_active是JSON布尔值true或false；current_blue_destination是left、right或neutral字符串。不得加字段、动作、分析或Markdown。'))


def state_system(original):
    for old,new in REPLACEMENTS:
        if original.count(old)!=1:raise ValueError('预定system修改点须恰一次。')
        original=original.replace(old,new,1)
    assert 'choice' not in original
    return original


def public_truth(observation):
    state=reduce_history(observation['history'])
    return dict(outer_blue_destination=state['outer']['blue'],guidance_active=state['active'],current_blue_destination=state['goals']['blue'])


def build_records():
    original=json.loads(V12_INPUTS.read_text());records=[]
    selected=[r for r in original if r['view']=='full_history'];assert len(selected)==64
    for source in selected:
        for query in ('action_replay','state_readout'):
            r=copy.deepcopy(source);r.pop('frozen_input_tokens');r.pop('view')
            r.update(id=f"{source['id']}__{query}",source_v12_id=source['id'],query=query)
            if query=='state_readout':r['messages'][0]['content']=state_system(r['messages'][0]['content'])
            # 正确状态只在评分元数据，从公开历史归约，绝不追加到messages。
            r['public_state_truth']=public_truth(json.loads(r['messages'][1]['content']))
            records.append(r)
    sources={str(V12_INPUTS.relative_to(ROOT)):sha(V12_INPUTS),str(V12_FREEZE.relative_to(ROOT)):sha(V12_FREEZE)}
    sources.update(json.loads(V12_FREEZE.read_text())['source_files_sha256'])
    assert len(records)==128
    return records,sources
