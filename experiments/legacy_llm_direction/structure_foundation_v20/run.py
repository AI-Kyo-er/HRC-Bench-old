"""指定20物理控制，A4通过后其余16；无模型、无自主能力评分。"""
import argparse
import copy
import json
import os
from experiments.physical.run import ROOT,save,sha,asset_hashes,versions
from experiments.sustained_activity_v18.run import SOURCES as OLD_SOURCES
from experiments.structure_v5.run import keyframe
from experiments.structure_foundation_v20.world import FoundationWorld,CONFIG,CONFIG_PATH
from experiments.structure_foundation_v20.canonical import digest,equal

RESULT=ROOT/'results/structure_foundation_v20';SOURCES=OLD_SOURCES+['experiments/structure_foundation_v20/'+n for n in ('world.py','canonical.py','run.py','config.json')]+['tests/test_structure_foundation_v20.py']
def hashes():return {n:sha(ROOT/n) for n in SOURCES}
def freeze_path(stage):return ROOT/f'experiments/structure_foundation_v20/cases/{stage}_freeze_dev0.json'

def cases(stage):
    out=[]
    for seed in (120,121):
        if stage=='A':
            for goal in ('left','right'):out.append(dict(id=f'A_{goal}_{seed}',group='A',seed=seed,goal=goal,commands=['request','red_left','wait_delivery','blue_inspection',f'blue_{goal}']))
        else:
            for first in ('left','right'):
                for timing in ('during','after'):
                    commands=['request']+(['wait_delivery'] if timing=='after' else [])+[f'green_{first}',f'green_{first}',f'green_{"right" if first=="left" else "left"}','red_left','wait_delivery',f'blue_{first}']
                    out.append(dict(id=f'B_{first}_{timing}_{seed}',group='B',seed=seed,first=first,timing=timing,commands=commands))
            for goal in ('left','right'):out.append(dict(id=f'C_{goal}_{seed}',group='C',seed=seed,goal=goal,commands=['request','wait_delivery','blue_inspection','presence_far','green_right','wait_far','presence_near','red_left','wait_near',f'blue_{goal}']))
            for payload in ('on_carrier','taken_left'):
                commands=['request','red_left','wait_delivery']+(['blue_left'] if payload=='taken_left' else [])+['start_return','wait_return']
                out.append(dict(id=f'D_{payload}_{seed}',group='D',seed=seed,payload=payload,commands=commands))
    return out

def freeze(stage):
    path=freeze_path(stage);assert not path.exists()
    if stage=='BCD':assert json.loads((RESULT/'A_audit_dev0.json').read_text())['passed']==4
    save(path,dict(version='structure-foundation-v20-dev0',stage=stage,cases=cases(stage),source_sha256=hashes(),assets_sha256=asset_hashes(),packages=versions(),config=CONFIG,
        termination='固定指定序列耗尽；真实技能失败则保存并停止本例剩余动作，不读成功评分选动作。',initialization='同一World初始化新增body后settle60，控制共同t0；所有新body始终存在。',
        concurrent_v19='仅CPU指定控制，可与固定v19 GPU评测并行；不比较墙钟速度。'))
    print('冻结',stage,sha(path),flush=True)

def command(world,choice):
    if choice=='request':world.start_delivery();return dict(success=True,kind='request')
    if choice=='wait_delivery':return world.wait_delivery()
    if choice=='start_return':return dict(success=True,kind='start_return',motion=world.start_return())
    if choice=='wait_return':return world.wait_return()
    if choice in ('presence_far','presence_near'):return dict(success=True,kind='presence',motion=world.start_presence(choice.split('_')[1]))
    if choice in ('wait_far','wait_near'):return world.wait_presence(choice.split('_')[1])
    item,target=choice.split('_')
    if world.at_goal(item,target):return dict(success=True,no_op=True,physical_attempt=False,reason='实际已在所选区域，未重复抓放。')
    return world.pick_place(item,target,'careful' if item in ('red','green') else 'direct')

def facts(world,case,rows):
    s=world.state();group=case['group'];successes=dict(all_commands_executed=len(rows)==len(case['commands']),all_commands_successful=all(r['result']['success'] for r in rows),forward_delivery=s['delivery_event'] is not None)
    if group=='A':successes.update(inspection_actual=rows[3]['after_state']['inspection_facts']['satisfied'],blue_final=world.at_goal('blue',case['goal']),red_preserved=world.at_goal('red','left'),green_source_preserved=__import__('math').dist(world.initial_state['objects']['green']['position'],s['objects']['green']['position'])<.01)
    elif group=='B':
        first=case['first'];other='right' if first=='left' else 'left';green=[r for r in rows if r['choice'].startswith('green_')]
        successes.update(green_final=world.at_goal('green',other),red_final=world.at_goal('red','left'),blue_final=world.at_goal('blue',first),repeat_real_noop=green[1]['result'].get('no_op',False) and equal(green[1]['before_state'],green[1]['after_state']),
            timing_actually_exposed=green[0]['before_state']['delivery_event'] is not None if case['timing']=='after' else green[0]['before_state']['delivery_event'] is None)
    elif group=='C':successes.update(inspection_actual=rows[2]['after_state']['inspection_facts']['satisfied'],presence_far_event=any(e['kind']=='presence_far' for e in s['presence_events']),presence_near_event=any(e['kind']=='presence_near' for e in s['presence_events']),green_final=world.at_goal('green','right'),red_final=world.at_goal('red','left'),blue_final=world.at_goal('blue',case['goal']))
    elif group=='D':successes.update(carrier_return_actual=s['return_event'] is not None,payload_return_truth=(s['payload_return_event'] is not None)==(case['payload']=='on_carrier'),forward_event_preserved=s['delivery_event']==next(r['after_state']['delivery_event'] for r in rows if r['choice']=='wait_delivery'),red_preserved=world.at_goal('red','left'),taken_blue_preserved=case['payload']!='taken_left' or world.at_goal('blue','left'))
    return successes

def rollout(case,stage):
    folder=RESULT/'raw'/stage/case['id'];folder.mkdir(parents=True);world=FoundationWorld(case['seed'],trace_path=folder/'ticks.jsonl.gz');rows=[];initial=copy.deepcopy(world.state())
    try:
        if case['seed']==120:keyframe(world,folder/'frames')
        for index,choice in enumerate(case['commands']):
            before=copy.deepcopy(world.state());result=command(world,choice);after=copy.deepcopy(world.state())
            rows.append(dict(sequence=index,choice=choice,before_state=before,result=result,after_state=after,before_tick=before['tick'],after_tick=after['tick']))
            save(folder/'decisions.json',rows);print(case['id'],index,choice,result['success'],world.tick,flush=True)
            if case['seed']==120:keyframe(world,folder/'frames')
            if not result['success']:break
        evidence=facts(world,case,rows) if len(rows)==len(case['commands']) else dict(all_commands_executed=False,all_commands_successful=False)
        summary=dict(case=case,initial_state=initial,final_state=world.state(),facts=evidence,passed=all(evidence.values()),common_start_tick=world.common_start_tick,
            end_tick=world.tick,makespan_ticks=world.tick-world.common_start_tick,body_ids=dict(robot=world.robot,carrier=world.partner,inspection=world.inspection,inspection_walls=world.inspection_walls,presence=world.presence,objects=world.objects),
            physical_attempts=sum(r['result'].get('physical_attempt',False) for r in rows),zero_tick_repeats=sum(r['result'].get('no_op',False) for r in rows),
            run_environment=dict(pid=os.getpid(),concurrent_v19_gpu_pid_alive=__import__('pathlib').Path('/proc/121752').exists()))
        save(folder/'summary.json',summary)
    finally:world.close()
    summary['canonical_physics']=digest(folder/'ticks.jsonl.gz');save(folder/'summary.json',summary);return summary

def run(stage):
    f=json.loads(freeze_path(stage).read_text());assert f['source_sha256']==hashes() and f['assets_sha256']==asset_hashes() and f['packages']==versions()
    folder=RESULT/'raw'/stage;assert not folder.exists(),'不覆盖失败或已运行轨迹'
    reports=[rollout(c,stage) for c in f['cases']]
    result=dict(stage=stage,total=len(reports),passed=sum(s['passed'] for s in reports),episodes=reports,freeze_sha256=sha(freeze_path(stage)),source_sha256=hashes())
    save(RESULT/f'{stage}_summary_dev0.json',result);print('阶段完成',stage,result['total'],result['passed'],flush=True);assert result['passed']==len(reports)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('A','BCD'));p.add_argument('--freeze',action='store_true');a=p.parse_args();freeze(a.stage) if a.freeze else run(a.stage)
