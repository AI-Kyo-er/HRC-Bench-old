"""分阶段冻结：恢复4先验→负面4及参考48；一个World、显式声明终止。"""
import argparse
import copy
import json
import math
import os
import time
from experiments.physical.run import ROOT,save,sha,versions,asset_hashes
from experiments.responsive_transport_v16.run import SOURCES as OLD_SOURCES
from experiments.responsive_transport_v16.world import ResponsiveWorld,CONFIG,CONFIG_PATH,DT
from experiments.responsive_transport_v16.canonical import trace_digest
from experiments.structure_v5.run import keyframe
from experiments.sustained_activity_v18.protocol import Episode,SYSTEM,candidates,reference,public_ledger

RESULT=ROOT/'results/sustained_activity_v18'
SOURCES=OLD_SOURCES+['experiments/sustained_activity_v18/'+n for n in ('protocol.py','run.py')]+['tests/test_sustained_activity_v18.py']


def hashes():return {n:sha(ROOT/n) for n in SOURCES}
def freeze_path(stage):return ROOT/f'experiments/sustained_activity_v18/cases/{stage}_freeze.json'


def cases(stage):
    if stage=='recovery':
        return [dict(id=f'Recovery_{first}_{seed}',seed=seed,initial_blue='right' if first=='left' else 'left',update='none',availability='ready',
            commands=['request_transport','careful_red_left','yield',f'place_blue_{first}',f'place_blue_{first}',f'place_blue_{"right" if first=="left" else "left"}','declare_done'])
            for seed in (100,101) for first in ('left','right')]
    if stage=='negative':
        data=[('initial','left',['declare_done']),('red_only','left',['careful_red_left','declare_done']),
              ('wrong_right','left',['request_transport','careful_red_left','yield','place_blue_right','declare_done']),
              ('wrong_left','right',['request_transport','careful_red_left','yield','place_blue_left','declare_done'])]
        return [dict(id=f'Negative_{name}_100',seed=100,initial_blue=t,update='none',availability='ready',commands=commands) for name,t,commands in data]
    return [dict(id=f'Reference_{initial}_{update}_{availability}_{policy}_{seed}',seed=seed,initial_blue=initial,update=update,availability=availability,policy=policy)
        for seed in (100,101) for initial in ('left','right') for update in ('none','accepted','rejected') for availability in ('ready','temporarily_busy')
        for policy in ('public_ledger_parallel','conservative_serial')]


def freeze(stage):
    path=freeze_path(stage)
    if path.exists():raise RuntimeError('禁止覆盖freeze。')
    old=json.loads((ROOT/'experiments/transport_goal_v17/cases/freeze.json').read_text());assert all(sha(ROOT/n)==v for n,v in old['source_sha256'].items())
    extra={}
    if stage!='recovery':
        summary=json.loads((RESULT/'recovery_summary.json').read_text());audit=json.loads((RESULT/'recovery_audit.json').read_text())
        assert summary['passed']==4 and audit['passed']==4
        assert json.loads(freeze_path('recovery').read_text())['source_sha256']==hashes()
        extra=dict(recovery_freeze_sha256=sha(freeze_path('recovery')),recovery_audit_sha256=sha(RESULT/'recovery_audit.json'))
    save(path,dict(version='sustained-activity-v18.0',stage=stage,cases=cases(stage),source_sha256=hashes(),assets_sha256=asset_hashes(),packages=versions(),
        config_sha256=sha(CONFIG_PATH),config=CONFIG,system=SYSTEM,candidates=candidates(),step_budget=12,
        termination='声明真实终止（允许错误）；budget/physical_failure/wait_timeout另记；不使用result.success。',
        concurrency='可能与固定v17 GPU评测并行CPU工作；模型墙钟不作速度比较。',**extra))
    print('冻结',stage,sha(path),flush=True)


def terminal_score(ep,world):
    assert ep.terminated,'评分只在结束后读取'
    goals=public_ledger(ep.history)['goals'];green=math.dist(ep.initial_state['objects']['green']['position'],world.state()['objects']['green']['position'])
    facts=dict(delivery_occurred=world.delivery_event is not None,red_left=world.at_goal('red','left'),blue_effective_goal=world.at_goal('blue',goals['blue']),green_preserved=green<.01)
    return dict(effective_goals=goals,facts=facts,goal_compliant=all(facts.values()),green_displacement_m=green,declared_done=ep.termination_reason=='declared_done')


def rollout(case,stage,folder):
    folder.mkdir(parents=True);start_wall=time.monotonic();world=ResponsiveWorld(case['seed'],case['availability'],trace_path=folder/'ticks.jsonl.gz');ep=Episode(world,case['initial_blue'],case['update'],12);rows=[]
    # 实验者/算法身份仅metadata，不传policy。每回合只创建一次world，没有隐式red prefix。
    init=copy.deepcopy(world.state());rendered=case['seed']==100 and (stage!='reference' or case['update']=='accepted')
    try:
        if rendered:keyframe(world,folder/'frames')
        for index in range(12):
            if ep.terminated:break
            observation=ep.observation();messages=ep.messages();assert json.loads(messages[1]['content'])==observation
            choice=case['commands'][index] if 'commands' in case else reference(copy.deepcopy(observation),case['policy'])
            before=copy.deepcopy(world.state());history_before=copy.deepcopy(ep.history);result=ep.act(choice)
            after=copy.deepcopy(world.state())
            rows.append(dict(sequence=index,observation=observation,messages=messages,choice=choice,result=result,before_state=before,after_state=after,history_before=history_before,history_after=copy.deepcopy(ep.history),before_tick=before['tick'],after_tick=after['tick']))
            print(case['id'],index+1,choice,result['feedback'],world.tick,flush=True)
            if rendered:keyframe(world,folder/'frames')
        scored=terminal_score(ep,world);final=copy.deepcopy(world.state())
        score_before=copy.deepcopy(ep.history);state_before=copy.deepcopy(world.state())
        try:ep.act('yield');raise AssertionError('终止后动作竟执行')
        except RuntimeError:pass
        after_terminal_unchanged=state_before==world.state() and score_before==ep.history
        s=dict(case=case,initial_state=init,final_state=final,checkpoint=init,common_start_tick=world.common_start_tick,end_tick=world.tick,
            termination_reason=ep.termination_reason,declaration=ep.declaration,terminal_score=scored,after_terminal_rejected_no_mutation=after_terminal_unchanged,
            cost=ep.cost,executions=ep.executions,robot_intervals=ep.robot_intervals,delivery_start_tick=world.delivery_start_tick,delivery_event=copy.deepcopy(world.delivery_event),
            public_final_history=copy.deepcopy(ep.history),availability_events=copy.deepcopy(ep.availability_events),legacy_left_only_goal_first_ticks=copy.deepcopy(world.goal_first_ticks),
            expected_blue_carrier_support_online=copy.deepcopy(world.support_audit),robot_partner_online=copy.deepcopy(world.contact_audit),other_objects_partner_online=copy.deepcopy(world.object_partner_audit),non_target_robot_online=copy.deepcopy(world.non_target_robot_audit),
            body_ids=dict(robot=world.robot,partner=world.partner,objects=dict(world.objects)),closed_activity_makespan_ticks=world.tick-world.common_start_tick,
            closed_activity_makespan_seconds=(world.tick-world.common_start_tick)*DT,makespan_includes_final_skill_parking=True,wall_seconds=time.monotonic()-start_wall,
            execution_environment=dict(pid=os.getpid(),cuda_visible_devices=os.environ.get('CUDA_VISIBLE_DEVICES'),concurrent_v17_thinking_pid_alive=__import__('pathlib').Path('/proc/101226').exists()),
            initial_red_already_left=world.at_goal('red','left') if not rows else 'left' in rows[0]['observation']['physical_placements']['red'])
        save(folder/'decisions.json',rows);save(folder/'summary.json',s)
    finally:world.close()
    s['canonical_full_trace']=trace_digest(folder/'ticks.jsonl.gz');save(folder/'summary.json',s)
    # 全量安全/支持及目标符合性由冻结后的独立audit复核，不拿skill成功替代实际区域。
    expected=stage!='negative';s['passed']=bool(scored['goal_compliant']==expected and ep.termination_reason=='declared_done' and all(e['success'] for e in ep.executions) and after_terminal_unchanged and not s['initial_red_already_left'])
    save(folder/'summary.json',s);return s


def run(stage):
    f=json.loads(freeze_path(stage).read_text());assert f['source_sha256']==hashes() and f['assets_sha256']==asset_hashes() and f['packages']==versions()
    folder=RESULT/'raw'/stage;folder.mkdir(parents=True,exist_ok=True)
    if any(folder.iterdir()):raise RuntimeError('禁止覆盖已开始的物理轨迹。')
    rows=[rollout(c,stage,folder/c['id']) for c in f['cases']]
    report=dict(stage=stage,total=len(rows),passed=sum(r['passed'] for r in rows),goal_compliant=sum(r['terminal_score']['goal_compliant'] for r in rows),total_ticks=sum(r['robot_partner_online']['total_ticks'] for r in rows),
        freeze_sha256=sha(freeze_path(stage)),source_sha256=hashes(),episodes=[dict(id=r['case']['id'],passed=r['passed'],score=r['terminal_score'],termination_reason=r['termination_reason'],cost=r['cost'],makespan_ticks=r['closed_activity_makespan_ticks']) for r in rows])
    save(RESULT/f'{stage}_summary.json',report);print('完成',stage,report['total'],report['passed'],report['goal_compliant'],flush=True)
    assert report['passed']==len(rows)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('recovery','negative','reference'));p.add_argument('--freeze',action='store_true');a=p.parse_args();freeze(a.stage) if a.freeze else run(a.stage)
