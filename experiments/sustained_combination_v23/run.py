"""控制8先审计，参考24后运行；固定同World，不重试到通过。"""
import argparse
import copy
import json
import os
from experiments.physical.run import ROOT,save,sha,asset_hashes,versions
from experiments.transport_cycle_v22.run import SOURCES as PARENT_SOURCES
from experiments.transport_cycle_v22.canonical import digest,content_equal
from experiments.structure_v5.run import keyframe
from experiments.sustained_combination_v23.world import CombinationWorld
from experiments.sustained_combination_v23.protocol import Episode,reference,terminal_score,public_ledger,CONFIG,SYSTEM,candidates,WORKSPACE

RESULT=ROOT/'results/sustained_combination_v23'
SOURCES=PARENT_SOURCES+['experiments/sustained_combination_v23/'+n for n in ('config.json','world.py','protocol.py','run.py')]+['tests/test_sustained_combination_v23.py']


def hashes():return {p:sha(ROOT/p) for p in SOURCES}


def cases(stage):
    if stage=='control':
        return [dict(id=f'{name}_{seed}',control=name,initial_blue='left',reply='rejected' if name=='R3' else 'accepted',presence='retain' if name=='C0' else 'stay',seed=seed)
                for name in ('C0','C1','R2','R3') for seed in CONFIG['seeds']]
    return [dict(id=f'ref_{target}_{reply}_{presence}_{seed}',initial_blue=target,reply=reply,presence=presence,seed=seed)
            for target in ('left','right') for reply in ('accepted','rejected') for presence in ('stay','retain','withdraw') for seed in CONFIG['seeds']]


def freeze_path(stage):return ROOT/f'experiments/sustained_combination_v23/{stage}_freeze_dev0.json'


def freeze(stage):
    path=freeze_path(stage);assert not path.exists()
    if stage=='reference':assert json.loads((RESULT/'control_audit_dev0.json').read_text())['passed']==8
    save(path,dict(version=CONFIG['version'],stage=stage,cases=cases(stage),source_sha256=hashes(),assets_sha256=asset_hashes(),packages=versions(),
        config=CONFIG,system=SYSTEM,candidates=candidates(),workspace=WORKSPACE,
        sequences=dict(common='forward请求→redfirst→当前近端载荷→blueinspection→检查请求接受且child开放→role提议/回应→真实检查交还',
            reference='保守公开ledger；partnerreload返远或robot空返远再blueLR；green最后→declare',
            C0='共同前缀retain/accept→实际presencefar且累计60→reload→载blue返far→greenright→declare',
            C1='共同前缀stay/accept→真实交还240→reload不返→greenright→declare',
            R2='首次交付后未requestcheck即载blue返far→显式forward近端→检查/accept→共同完成',
            R3='同R2但检查open后reject→robotL完成'),
        expected_task_success='control C0/C1为预定任务失败，其余为成功；严格控制/安全与任务成功分列。',
        source_information='脚本初始公共接受及role提议/回应；策略仅已发生history/当前physical，未暴露未来presence计划或private评分。'))
    print('冻结',stage,sha(path),flush=True)


def rollout(case,stage):
    folder=RESULT/'raw'/'dev0'/stage/case['id'];folder.mkdir(parents=True)
    world=CombinationWorld(case['seed'],trace_path=folder/'ticks.jsonl.gz',service_trace_path=folder/'service_ticks.jsonl.gz')
    ep=Episode(world,case['initial_blue'],case['reply'],case['presence']);initial=copy.deepcopy(world.state());rows=[];checkpoints={};failure=None
    def act(choice):
        obs=ep.observation();before=copy.deepcopy(world.state());service_before=ep.service.snapshot();message=ep.messages()
        result=ep.act(choice);after=copy.deepcopy(world.state())
        rows.append(dict(sequence=len(rows),choice=choice,observation=obs,messages=message,before_state=before,after_state=after,before_tick=before['tick'],after_tick=after['tick'],
            service_before=service_before,service_after=ep.service.snapshot(),history_after=copy.deepcopy(ep.history),result=result))
        save(folder/'decisions.json',rows);keyframe(world,folder/'frames');print(case['id'],len(rows),choice,world.tick,result['valid'],flush=True)
        if result.get('execution',{}).get('physical_attempt') and not result['execution']['success']:raise RuntimeError('真实物理技能失败，保留完整版本。')
        if not result['valid']:raise RuntimeError('固定控制发生非预期拒绝，保留证据。')
        return result
    def wait_until(predicate):
        while not predicate():
            if ep.terminated:raise RuntimeError('达到所需事实前已终止。')
            act('yield')
    def complete():
        while not ep.terminated:act(reference(ep.observation()))
    def delivery():
        act('request_transport');act('careful_red_left');wait_until(lambda:world.cycle.active is None and world.carrier_facts()['near'] and world.carrier_facts()['payload_stable'])
        checkpoints['first_delivery']=copy.deepcopy(world.state())
    try:
        keyframe(world,folder/'frames')
        if stage=='control':
            name=case['control'];delivery()
            if name in ('R2','R3'):
                act('request_return');wait_until(lambda:world.cycle.active is None and world.carrier_facts()['far'])
                checkpoints['early_return']=dict(state=copy.deepcopy(world.state()),service=ep.service.snapshot(),public_history=copy.deepcopy(ep.history))
                act('request_transport');wait_until(lambda:world.cycle.active is None and world.carrier_facts()['near'])
                checkpoints['recovered_forward']=copy.deepcopy(world.state());complete()
            else:
                act('place_blue_inspection');act('request_check')
                if name=='C0':
                    wait_until(lambda:any(e['kind']=='presence_far_observed' for e in ep.history))
                    checkpoints['far_before_reload']=dict(state=copy.deepcopy(world.state()),service=ep.service.snapshot())
                    act('reload_blue');act('request_return');wait_until(lambda:world.cycle.active is None and world.carrier_facts()['far'])
                else:
                    wait_until(lambda:ep.service.completed);act('reload_blue')
                act('careful_green_right');act('declare_done')
        else:complete()
        ep.observation();final=copy.deepcopy(world.state());service=ep.service.snapshot();history=copy.deepcopy(ep.history);cost=copy.deepcopy(ep.cost)
        immutable=False
        try:ep.act('yield')
        except RuntimeError:immutable=content_equal(final,world.state()) and history==ep.history and service==ep.service.snapshot() and cost==ep.cost
    except Exception as error:
        failure=repr(error);ep.observation();final=copy.deepcopy(world.state());immutable=False
    finally:world.close()
    score=terminal_score(ep,final);expected=stage!='control' or case['control'] not in ('C0','C1')
    summary=dict(case=case,initial_state=initial,final_state=final,checkpoints=checkpoints,public_history=ep.history,service=ep.service.snapshot(),cost=ep.cost,
        score=score,expected_task_success=expected,runner_expected_match=score['task_success']==expected and failure is None and immutable,
        after_terminal_immutable=immutable,failure=failure,termination_reason=ep.termination_reason,common_start_tick=world.common_start_tick,end_tick=world.tick,
        makespan_ticks=world.tick-world.common_start_tick,canonical_physics=digest(folder/'ticks.jsonl.gz'),pid=os.getpid(),
        body_ids=dict(robot=world.robot,carrier=world.partner,inspection=world.inspection,inspection_walls=world.inspection_walls,presence=world.presence,objects=world.objects))
    save(folder/'summary.json',summary);return summary


def run(stage):
    f=json.loads(freeze_path(stage).read_text());assert f['source_sha256']==hashes() and f['assets_sha256']==asset_hashes() and f['packages']==versions()
    assert not (RESULT/'raw'/'dev0'/stage).exists()
    reports=[rollout(c,stage) for c in f['cases']];result=dict(stage=stage,total=len(reports),runner_expected_match=sum(r['runner_expected_match'] for r in reports),
        task_success=sum(r['score']['task_success'] for r in reports),episodes=reports,freeze_sha256=sha(freeze_path(stage)),source_sha256=hashes())
    save(RESULT/f'{stage}_summary_dev0.json',result);print('阶段完成',stage,result['runner_expected_match'],result['task_success'],flush=True)
    assert result['runner_expected_match']==len(reports)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('control','reference'));p.add_argument('--freeze',action='store_true');a=p.parse_args();freeze(a.stage) if a.freeze else run(a.stage)
