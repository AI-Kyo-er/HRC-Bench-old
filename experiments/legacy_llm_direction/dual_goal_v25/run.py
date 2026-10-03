"""固定8更新控制→32完整参考→8真实前缀局部参考；分阶段先审计。"""
import argparse
import copy
import itertools
import json
import os
from experiments.physical.run import ROOT,save,sha,asset_hashes,versions
from experiments.sustained_combination_v23.run import SOURCES as PARENT_SOURCES
from experiments.sustained_combination_v23.world import CombinationWorld
from experiments.transport_cycle_v22.canonical import digest,content_equal
from experiments.structure_v5.run import keyframe
from experiments.dual_goal_v25.protocol import CONFIG,SYSTEM,WORKSPACE,Episode,candidates,public_ledger,reference,terminal_score,opposite
from experiments.structure_foundation_v20.audit_v2 import stable_region

RESULT=ROOT/'results/dual_goal_v25'
SOURCES=sorted(set(PARENT_SOURCES+['experiments/dual_goal_v25/'+n for n in ('config.json','protocol.py','run.py','audit.py')]+[
    'experiments/sustained_combination_v23/audit.py','experiments/transport_cycle_v22/audit.py','experiments/sustained_structure_v21/audit.py','tests/test_dual_goal_v25.py']))


def hashes():return {p:sha(ROOT/p) for p in SOURCES}


def cases(stage):
    if stage=='control':
        return [dict(id=f'{name}_{initial}',control=name,initial_blue=initial,reply='rejected' if name=='U2' else 'accepted',timing='after_handoff',
            expression='direct' if name=='U3' else 'relation',q='same',direct_green=initial,seed=120)
            for initial in ('left','right') for name in ('U1','U2','U3','U4')]
    if stage=='reference':
        result=[]
        for initial,reply,q,expression,timing in itertools.product(('left','right'),('accepted','rejected'),('same','opposite'),('direct','relation'),('before_check','after_handoff')):
            final=opposite(initial) if reply=='accepted' else initial;green=final if q=='same' else opposite(final)
            result.append(dict(id=f'ref_{initial}_{reply}_{q}_{expression}_{timing}',initial_blue=initial,reply=reply,q=q,expression=expression,timing=timing,direct_green=green,seed=120))
        return result
    return [dict(id=f'local_{blue}_{green}_{expression}',initial_blue=blue,reply='rejected',q='same' if blue==green else 'opposite',expression=expression,timing='before_check',direct_green=green,seed=120)
            for blue,green,expression in itertools.product(('left','right'),('left','right'),('direct','relation'))]


def requirement(case):return dict(mode='direct',destination=case['direct_green']) if case['expression']=='direct' else dict(mode='relation',relation=case['q'])


class SnapshotWorld:
    """CPU冻结初始输入仅复用v24已真实初始化状态，不创建或瞬移新物理。"""
    def __init__(self,state):self._state=copy.deepcopy(state);self.tick=state['tick'];self.step_callback=None
    def state(self):return copy.deepcopy(self._state)
    def start_presence(self,destination):raise RuntimeError('初始输入冻结不推进物理。')
    def at_goal(self,item,target):
        if target=='inspection':return item=='blue' and self._state['inspection_facts']['satisfied']
        if target=='carrier':return item=='blue' and self._state['current_carrier_facts']['near'] and self._state['current_carrier_facts']['payload_stable']
        return stable_region(self._state,item,target)


def freeze_path(stage):return ROOT/f'experiments/dual_goal_v25/{stage}_freeze_dev0.json'


def freeze(stage):
    path=freeze_path(stage);assert not path.exists()
    if stage in ('reference','local'):
        previous='control' if stage=='reference' else 'reference';expected=8 if previous=='control' else 32
        assert json.loads((RESULT/f'{previous}_audit_dev0.json').read_text())['passed']==expected
    source=ROOT/CONFIG['source_initial_state'];state=json.loads(source.read_text())['initial_state'];inputs=[]
    for case in cases(stage):
        ep=Episode(SnapshotWorld(state),case['initial_blue'],requirement(case),case['reply'],case['timing']);inputs.append(dict(id=case['id'],messages=ep.messages()))
    save(path,dict(version=CONFIG['version'],stage=stage,config=CONFIG,cases=cases(stage),source_sha256=hashes(),assets_sha256=asset_hashes(),packages=versions(),
        system=SYSTEM,candidates=candidates(),workspace=WORKSPACE,initial_messages=inputs,initial_state_source=dict(path=CONFIG['source_initial_state'],sha256=sha(source),kind='v24真实初始化，正式第一观察逐字核对；未来及局部边界输入按冻结源动态构造、事后重建。'),
        sequences=dict(control='forward/redfirst/actual delivery/blueinspection/emptyreturn actualfar/greenI/checkrequest/actualhandoff+同tick事务/U1-U4/declare',
            reference='forward/redfirst/delivery/blueinspection/checkrequest/handoff/emptyreturn actualfar/bluecurrent/greencurrent/declare',
            local='reference实际公共前缀至check完成和空返far；记录前缀cost，begin_local公开有效目标表达且预算12，从同World继续blue/green/declare'),
        visibility='直接臂初始只公开G不公开生成q；脚本回复仅生成后进入可观察队列，无case/F/未来标签；声明不产生更新。',
        expected_task='control U4两条失败其余成功；reference32与local8均成功，严格/安全另报。'))
    print('冻结',stage,sha(path),flush=True)


def rollout(case,stage,frozen_initial_messages):
    folder=RESULT/'raw'/'dev0'/stage/case['id'];folder.mkdir(parents=True)
    world=CombinationWorld(case['seed'],trace_path=folder/'ticks.jsonl.gz',service_trace_path=folder/'service_ticks.jsonl.gz')
    ep=Episode(world,case['initial_blue'],requirement(case),case['reply'],case['timing']);initial=copy.deepcopy(world.state());rows=[];checkpoints={};failure=None
    assert ep.messages()==frozen_initial_messages
    phase='prefix' if stage=='local' else stage
    def act(choice):
        obs=ep.observation();before=copy.deepcopy(world.state());service_before=ep.service.snapshot();messages=ep.messages();ledger_before=public_ledger(obs['history'])
        result=ep.act(choice);after=copy.deepcopy(world.state())
        rows.append(dict(sequence=len(rows),phase=phase,choice=choice,observation=obs,messages=messages,before_state=before,after_state=after,before_tick=before['tick'],after_tick=after['tick'],
            budget_origin=ep.budget_origin,decision_budget=ep.decision_budget,service_before=service_before,service_after=ep.service.snapshot(),history_after=copy.deepcopy(ep.history),result=result,
            known_at_start=ledger_before,actual_updates_during_skill=[copy.deepcopy(e) for e in ep.history if e['kind'] in ('proposal','proposal_reply') and before['tick']<e['actual_tick']<=after['tick']]))
        save(folder/'decisions.json',rows);keyframe(world,folder/'frames');print(case['id'],len(rows),phase,choice,world.tick,result['valid'],flush=True)
        if result.get('execution',{}).get('physical_attempt') and not result['execution']['success']:raise RuntimeError('真实技能失败，保留原版本。')
        if not result['valid']:raise RuntimeError('固定参考非预期拒绝，保留原版本。')
    def wait_until(predicate):
        start=world.tick
        while not predicate():
            if world.tick-start>=CONFIG['wait_limit_ticks'] or ep.terminated:raise RuntimeError('指定事实等待达到上限或活动已终止。')
            act('yield')
        if world.tick-start>CONFIG['wait_limit_ticks']:raise RuntimeError('指定等待实际超出6000tick，保留失败。')
    def delivery():
        act('request_transport');act('careful_red_left');wait_until(lambda:world.cycle.active is None and world.carrier_facts()['near'] and world.carrier_facts()['payload_stable'])
    def inspection():
        act('place_blue_inspection');act('request_check');wait_until(lambda:ep.service.completed)
    def far():
        act('request_return');wait_until(lambda:world.cycle.active is None and world.carrier_facts()['far'])
    def complete():
        while not ep.terminated:act(reference(ep.observation()))
    try:
        keyframe(world,folder/'frames')
        if stage=='control':
            delivery();act('place_blue_inspection');far();act('careful_green_'+case['initial_blue']);checkpoints['old_green']=dict(state=copy.deepcopy(world.state()),history=copy.deepcopy(ep.history))
            act('request_check');wait_until(lambda:ep.service.completed);checkpoints['after_update']=dict(state=copy.deepcopy(world.state()),history=copy.deepcopy(ep.history))
            ledger=public_ledger(ep.history);act('place_blue_'+ledger['goals']['blue'])
            if case['control']=='U1':act('careful_green_'+ledger['goals']['green'])
            act('declare_done')
        elif stage=='local':
            delivery();inspection();far();checkpoints['local_start']=dict(state=copy.deepcopy(world.state()),service=ep.service.snapshot(),history=copy.deepcopy(ep.history),cost=copy.deepcopy(ep.cost),row_boundary=len(rows))
            ep.begin_local();phase='local';checkpoints['local_start']['messages']=ep.messages();complete()
        else:complete()
        ep.observation();final=copy.deepcopy(world.state());service=ep.service.snapshot();history=copy.deepcopy(ep.history);cost=copy.deepcopy(ep.cost);immutable=False
        try:ep.act('yield')
        except RuntimeError:immutable=content_equal(final,world.state()) and history==ep.history and service==ep.service.snapshot() and cost==ep.cost
    except Exception as error:failure=repr(error);ep.observation();final=copy.deepcopy(world.state());immutable=False
    finally:world.close()
    score=terminal_score(ep,final);expected=case.get('control')!='U4';prefix_cost=checkpoints.get('local_start',{}).get('cost');local_cost=None
    if prefix_cost is not None:local_cost={k:ep.cost[k]-prefix_cost[k] for k in ep.cost}
    summary=dict(stage=stage,case=case,initial_state=initial,final_state=final,checkpoints=checkpoints,public_history=ep.history,service=ep.service.snapshot(),cost=ep.cost,
        prefix_cost=prefix_cost,local_cost=local_cost,local_makespan_ticks=None if prefix_cost is None else world.tick-checkpoints['local_start']['state']['tick'],
        score=score,expected_task_success=expected,runner_expected_match=score['task_success']==expected and failure is None and immutable,after_terminal_immutable=immutable,
        failure=failure,termination_reason=ep.termination_reason,common_start_tick=world.common_start_tick,end_tick=world.tick,makespan_ticks=world.tick-world.common_start_tick,
        canonical_physics=digest(folder/'ticks.jsonl.gz'),pid=os.getpid(),body_ids=dict(robot=world.robot,carrier=world.partner,inspection=world.inspection,inspection_walls=world.inspection_walls,presence=world.presence,objects=world.objects,trays=world.trays))
    save(folder/'summary.json',summary);return summary


def run(stage):
    f=json.loads(freeze_path(stage).read_text());assert f['source_sha256']==hashes() and f['assets_sha256']==asset_hashes() and f['packages']==versions()
    assert not (RESULT/'raw'/'dev0'/stage).exists();source_copy=RESULT/'raw'/f'{stage}_runtime_sources';source_copy.mkdir(parents=True)
    for p in SOURCES:out=source_copy/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((ROOT/p).read_bytes())
    inputs={r['id']:r['messages'] for r in f['initial_messages']};reports=[rollout(c,stage,inputs[c['id']]) for c in f['cases']]
    result=dict(stage=stage,total=len(reports),runner_expected_match=sum(r['runner_expected_match'] for r in reports),task_success=sum(r['score']['task_success'] for r in reports),episodes=reports,freeze_sha256=sha(freeze_path(stage)),source_sha256=hashes())
    save(RESULT/f'{stage}_summary_dev0.json',result);print('阶段完成',stage,result['runner_expected_match'],result['task_success'],flush=True);assert result['runner_expected_match']==len(reports)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('control','reference','local'));p.add_argument('--freeze',action='store_true');a=p.parse_args();freeze(a.stage) if a.freeze else run(a.stage)
