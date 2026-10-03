"""8指定共盘/恢复控制，原单World与真实摩擦技能；无评分目标过滤。"""
import argparse
import copy
import json
import os
from pathlib import Path
from experiments.physical.run import ROOT,save,sha,asset_hashes,versions
from experiments.sustained_combination_v23.run import SOURCES as PARENT_SOURCES
from experiments.sustained_combination_v23.world import CombinationWorld
from experiments.sustained_combination_v23.protocol import WORKSPACE
from experiments.transport_cycle_v22.canonical import digest
from experiments.structure_v5.run import keyframe

CONFIG=json.loads(Path(__file__).with_name('config.json').read_text())
RESULT=ROOT/'results/shared_slots_v24'
FREEZE=ROOT/'experiments/shared_slots_v24/freeze_dev0.json'
SOURCES=sorted(set(PARENT_SOURCES+['experiments/shared_slots_v24/'+n for n in ('config.json','run.py','audit.py')]+[
    'experiments/transport_cycle_v22/audit.py','experiments/sustained_structure_v21/audit.py','experiments/structure_foundation_v20/audit_v2.py',
    'tests/test_shared_slots_v24.py']))
PREFIX=['request_forward','careful_red_left','wait_near_payload','place_blue_inspection','request_return','wait_far_empty']
MENU=['request_forward','request_return','wait_near_payload','wait_far_empty','careful_red_left','place_blue_inspection','place_blue_left','place_blue_right','careful_green_left','careful_green_right']
SYSTEM='固定物理能力控制：所有条件同World/菜单，命令按实际来源及几何执行；无检查请求/私有任务目标门槛，完成仅指指定控制序列结束。'


def hashes():return {p:sha(ROOT/p) for p in SOURCES}


def cases():
    return [dict(id=f'{name}_{seed}',sequence=name,seed=seed,commands=PREFIX+commands)
            for name,commands in CONFIG['sequences'].items() for seed in CONFIG['seeds']]


def waiting_satisfied(state,choice):
    cf=state['current_carrier_facts']
    idle=state['cycle']['active'] is None
    return bool(idle and (cf['near'] and cf['payload_stable'] if choice=='wait_near_payload' else cf['far']))


def freeze():
    assert not FREEZE.exists()
    save(FREEZE,dict(version=CONFIG['version'],config=CONFIG,cases=cases(),source_sha256=hashes(),assets_sha256=asset_hashes(),packages=versions(),
        system=SYSTEM,menu=MENU,workspace=WORKSPACE,common_prefix=PREFIX,
        conditions='presence留近端且不运动，无request_check或服务实例；forward载blue、空return，后续全部carrier当前far稳定且无活动。',
        evaluation='指定命令真实抓放/来源目的支撑、C/D离盘再回、全tick接触/非目标持续保持；不使用v23检查或green-right任务评分。'))
    print('冻结',sha(FREEZE),flush=True)


def rollout(case):
    folder=RESULT/'raw'/'dev0'/case['id'];folder.mkdir(parents=True)
    world=CombinationWorld(case['seed'],trace_path=folder/'ticks.jsonl.gz')
    rows=[];initial=copy.deepcopy(world.state());cost=dict(decisions=0,physical_attempts=0,wait_ticks=0);failure=None;checkpoint=None
    def act(choice):
        before=copy.deepcopy(world.state());obs=copy.deepcopy(dict(physical=before,history=world.cycle.snapshot(),workspace=WORKSPACE,menu=MENU))
        cost['decisions']+=1
        if choice in ('request_forward','request_return'):result=world.request_motion(choice.split('_')[-1])
        elif choice.startswith('wait_'):
            world.phase=choice;start=world.tick
            for _ in range(CONFIG['wait_limit_ticks']):
                if waiting_satisfied(world.state(),choice):break
                world.simulate(1)
            result=dict(success=waiting_satisfied(world.state(),choice),wait_ticks=world.tick-start)
            cost['wait_ticks']+=result['wait_ticks']
        else:
            _,item,target=choice.split('_');route=CONFIG['green_route'] if item=='green' else 'careful' if item=='red' else CONFIG['blue_route']
            result=world.pick_place(item,target,route);cost['physical_attempts']+=int(result['physical_attempt'])
        after=copy.deepcopy(world.state())
        rows.append(dict(sequence=len(rows),choice=choice,observation=obs,messages=[dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(obs,ensure_ascii=False))],
            before_tick=before['tick'],after_tick=after['tick'],before_state=before,after_state=after,result=result))
        save(folder/'decisions.json',rows);keyframe(world,folder/'frames');print(case['id'],len(rows),choice,world.tick,result.get('success',result.get('decision')),flush=True)
        if result.get('success') is False:raise RuntimeError('指定技能/等待失败，保留完整控制。')
        if choice in ('request_forward','request_return') and result['decision']!='accepted':raise RuntimeError('固定运动请求发生非预期拒绝。')
    try:
        keyframe(world,folder/'frames')
        for index,choice in enumerate(case['commands']):
            act(choice)
            if index==len(PREFIX)-1:
                checkpoint=copy.deepcopy(world.state());assert waiting_satisfied(checkpoint,'wait_far_empty')
    except Exception as error:failure=repr(error)
    finally:
        final=copy.deepcopy(world.state());world.close()
    summary=dict(case=case,initial_state=initial,final_state=final,prefix_checkpoint=checkpoint,cost=cost,failure=failure,
        control_sequence_completed=failure is None and len(rows)==len(case['commands']),common_start_tick=world.common_start_tick,end_tick=world.tick,
        makespan_ticks=world.tick-world.common_start_tick,canonical_physics=digest(folder/'ticks.jsonl.gz'),cycle=final['cycle'],pid=os.getpid(),
        body_ids=dict(robot=world.robot,carrier=world.partner,inspection=world.inspection,inspection_walls=world.inspection_walls,presence=world.presence,objects=world.objects,trays=world.trays),
        no_check_service=True,no_task_success_claim=True)
    save(folder/'summary.json',summary);return summary


def run():
    f=json.loads(FREEZE.read_text());assert f['source_sha256']==hashes() and f['assets_sha256']==asset_hashes() and f['packages']==versions()
    assert not (RESULT/'raw'/'dev0').exists()
    source_copy=RESULT/'raw'/'runtime_sources';source_copy.mkdir(parents=True)
    for path in SOURCES:savepath=source_copy/path;savepath.parent.mkdir(parents=True,exist_ok=True);savepath.write_bytes((ROOT/path).read_bytes())
    rows=[rollout(c) for c in f['cases']]
    result=dict(total=len(rows),control_sequence_completed=sum(r['control_sequence_completed'] for r in rows),episodes=rows,freeze_sha256=sha(FREEZE),source_sha256=hashes())
    save(RESULT/'control_summary_dev0.json',result);print('控制结束',result['control_sequence_completed'],'/8',flush=True)
    assert result['control_sequence_completed']==8


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');a=p.parse_args();freeze() if a.freeze else run()
