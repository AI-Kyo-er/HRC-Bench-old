"""固定A6/B2真实循环控制；失败不重试，不覆盖原运行。"""
import argparse
import copy
import json
import os
from experiments.physical.run import ROOT,save,sha,asset_hashes,versions
from experiments.sustained_structure_v21.run import SOURCES as PARENT_SOURCES
from experiments.structure_v5.run import keyframe
from experiments.transport_cycle_v22.world import CycleWorld,CONFIG,TRANSPORT,GEOMETRY
from experiments.transport_cycle_v22.canonical import digest,content_equal

RESULT=ROOT/'results/transport_cycle_v22'
SOURCES=PARENT_SOURCES+['experiments/transport_cycle_v22/'+n for n in ('config.json','cycle.py','world.py','canonical.py','run.py')]+['tests/test_transport_cycle_v22.py']
FREEZE=ROOT/'experiments/transport_cycle_v22/freeze_dev0.json'
MENU=['request_forward','request_return','reload_blue','place_blue_inspection','place_blue_left','place_blue_right','careful_red_left','wait_current_leg','wait_fixed_window']
WORKSPACE=dict(carrier_endpoints=[[.65,.6,.045],[.65,0,.045]],carrier_half_extents=TRANSPORT['carrier_half_extents'],
    trays={name:dict(center=[.65,y,.005],half_extents=[.10,.085,.005]) for name,y in (('left',-.25),('right',.25))},
    inspection_center=GEOMETRY['inspection_center'],inspection_half_extents=GEOMETRY['inspection_half_extents'],
    notes='right盘位于载台扫掠方向；green保持源处直到本控制循环结束。远端blue不能直接抓，需实际前送到近端。来源/职责不按私有目标筛。')


def hashes():return {p:sha(ROOT/p) for p in SOURCES}


def cases():
    return [dict(id=f'A_{source}_{seed}',family='A',source=source,seed=seed) for source in ('inspection','left','right') for seed in CONFIG['seeds']]+[
        dict(id=f'B_empty_{seed}',family='B',source='inspection',seed=seed) for seed in CONFIG['seeds']]


def freeze():
    assert not FREEZE.exists()
    save(FREEZE,dict(version=CONFIG['version'],config=CONFIG,cases=cases(),source_sha256=hashes(),assets_sha256=asset_hashes(),packages=versions(),
        menu=MENU,workspace=WORKSPACE,sequences=dict(A=['request_forward','careful_red_left','wait_current_leg','place_blue_SOURCE','reload_blue','request_return','wait_current_leg','request_forward','wait_current_leg','place_blue_left'],
        B=['request_forward','careful_red_left','wait_current_leg','place_blue_inspection','request_return','wait_1000','request_return_duplicate','request_forward_rejected','wait_current_leg','wait_480_no_queue','request_forward','wait_1000','request_forward_duplicate','request_return_rejected','wait_current_leg','wait_480_no_queue','reload_blue','request_return','wait_current_leg']),
        score='8指定控制；目标为实测抓放/行程/事件/安全，不是策略或研究任务成功。A末blueleft/B末bluefar是控制位置，未用作执行gate。'))
    print('冻结',sha(FREEZE),flush=True)


def rollout(case):
    folder=RESULT/'raw'/'dev0'/case['id'];folder.mkdir(parents=True)
    world=CycleWorld(case['seed'],trace_path=folder/'ticks.jsonl.gz')
    rows=[];initial=copy.deepcopy(world.state());failure=None;cost=dict(decisions=0,physical_attempts=0,wait_ticks=0)
    def observation():
        s=world.state()
        return copy.deepcopy(dict(physical=s,history=world.cycle.snapshot(),workspace=WORKSPACE,menu=MENU))
    def act(choice,ticks=None):
        before=copy.deepcopy(world.state());obs=observation();cost['decisions']+=1
        if choice in ('request_forward','request_return'):result=world.request_motion(choice.split('_')[1])
        elif choice.startswith('place_blue_') or choice=='reload_blue':
            destination='carrier' if choice=='reload_blue' else choice[len('place_blue_'):]
            result=world.pick_place('blue',destination,'direct');cost['physical_attempts']+=int(result['physical_attempt'])
        elif choice=='careful_red_left':
            result=world.pick_place('red','left','careful');cost['physical_attempts']+=int(result['physical_attempt'])
        else:
            world.phase=choice;start=world.tick
            if choice=='wait_current_leg':
                for _ in range(CONFIG['wait_budget_ticks']):
                    if world.cycle.active is None:break
                    world.simulate(1)
                result=dict(success=world.cycle.active is None)
            else:world.simulate(ticks);result=dict(success=True)
            result['wait_ticks']=world.tick-start;cost['wait_ticks']+=result['wait_ticks']
        after=copy.deepcopy(world.state())
        rows.append(dict(sequence=len(rows),choice=choice,ticks=ticks,observation=obs,messages=[dict(role='system',content='固定物理能力控制；实际来源/端点决定接受，不按任务正确目标过滤。'),dict(role='user',content=json.dumps(obs,ensure_ascii=False))],
            before_tick=before['tick'],after_tick=after['tick'],before_state=before,after_state=after,result=result))
        save(folder/'decisions.json',rows);keyframe(world,folder/'frames')
        print(case['id'],len(rows),choice,world.tick,flush=True)
        if result.get('success') is False:raise RuntimeError('控制物理/等待失败，完整证据保留。')
        return result
    def request(direction):
        result=act('request_'+direction);assert result['decision']=='accepted';return result
    def probe(direction):
        act('wait_fixed_window',CONFIG['in_motion_probe_ticks'])
        duplicate=act('request_'+direction);rejected=act('request_'+('return' if direction=='forward' else 'forward'))
        assert duplicate['decision']=='already_running' and rejected['decision']=='rejected_motion'
        act('wait_current_leg');before=world.cycle.snapshot();act('wait_fixed_window',CONFIG['no_queue_wait_ticks'])
        assert content_equal(before,world.cycle.snapshot())
    try:
        keyframe(world,folder/'frames');request('forward');act('careful_red_left');act('wait_current_leg');act('place_blue_'+case['source'])
        if case['family']=='A':
            act('reload_blue');request('return');act('wait_current_leg');request('forward');act('wait_current_leg');act('place_blue_left')
        else:
            request('return');probe('return');request('forward');probe('forward');act('reload_blue');request('return');act('wait_current_leg')
    except Exception as error:failure=repr(error)
    finally:
        final=copy.deepcopy(world.state());world.close()
    control_pass=failure is None and len(final['cycle']['legs'])==(3 if case['family']=='A' else 4)
    summary=dict(case=case,failure=failure,control_sequence_completed=control_pass,initial_state=initial,final_state=final,cost=cost,
        common_start_tick=world.common_start_tick,end_tick=world.tick,makespan_ticks=world.tick-world.common_start_tick,
        cycle=final['cycle'],canonical_physics=digest(folder/'ticks.jsonl.gz'),
        body_ids=dict(robot=world.robot,carrier=world.partner,inspection=world.inspection,inspection_walls=world.inspection_walls,presence=world.presence,objects=world.objects),pid=os.getpid())
    save(folder/'summary.json',summary);return summary


def run():
    f=json.loads(FREEZE.read_text());assert f['source_sha256']==hashes() and f['assets_sha256']==asset_hashes() and f['packages']==versions()
    assert not (RESULT/'raw'/'dev0').exists()
    rows=[rollout(c) for c in f['cases']]
    result=dict(total=len(rows),control_sequence_completed=sum(r['control_sequence_completed'] for r in rows),episodes=rows,freeze_sha256=sha(FREEZE),source_sha256=hashes())
    save(RESULT/'control_summary_dev0.json',result);print('控制完成',result['control_sequence_completed'],flush=True)
    assert result['control_sequence_completed']==8


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');a=p.parse_args();freeze() if a.freeze else run()
