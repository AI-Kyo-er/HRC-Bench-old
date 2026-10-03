"""只调整尚未运行H与独立C6/7重验的真实顺序，不改原运行源。"""
import argparse
import copy
import json
import os
from experiments.physical.run import ROOT,save,sha,asset_hashes,versions
from experiments.structure_foundation_v20.canonical import equal,digest
from experiments.structure_v5.run import keyframe
from experiments.sustained_structure_v21.world import StructureWorld
from experiments.sustained_structure_v21.protocol import Episode,public_ledger,SYSTEM,candidates
from experiments.sustained_structure_v21.run import RESULT,hashes as original_hashes,terminal_score
from experiments.sustained_structure_v21.cases import cases as original_cases
from experiments.sustained_structure_v21.service import CONFIG


def hashes():
    return dict(original_hashes(),**{p:sha(ROOT/p) for p in (
        'experiments/sustained_structure_v21/run_r1.py','tests/test_sustained_structure_v21_r1.py')})


def cases(stage):
    if stage=='C_return':
        return [dict(case,id=case['id'].replace('_120','_r1_120')) for case in original_cases('C') if case['control']>=6]
    return original_cases('H')


def freeze_path(stage):return ROOT/f'experiments/sustained_structure_v21/cases/{stage}_freeze_r1.json'


def reference_r1(observation):
    ledger=public_ledger(observation['history']);regions=observation['physical_placements']
    if not ledger['transport_started']:return 'request_transport'
    if 'left' not in regions['red']:return 'careful_red_left'
    if observation['delivery_event'] is None:return 'yield'
    requested=any(e['kind']=='return_request_accepted' for e in observation['history'])
    if not requested:
        if ledger['blue_role']=='robot' and 'inspection' not in regions['blue']:return 'place_blue_inspection'
        return 'request_return'
    if observation['carrier_return_event'] is None:return 'yield'
    if ledger['blue_role']=='partner_return' and observation['payload_return_event'] is None:return 'yield'
    if ledger['blue_role']=='robot' and ledger['goals']['blue'] not in regions['blue']:
        return 'place_blue_'+ledger['goals']['blue']
    if 'right' not in regions['green']:return 'careful_green_right'
    return 'declare_done'


def freeze(stage):
    path=freeze_path(stage);assert not path.exists()
    if stage=='H':assert json.loads((RESULT/'C_return_audit_r1.json').read_text())['all_controls_evidence_and_safety_pass']
    proof=json.loads((RESULT/'C_audit_dev0.json').read_text());assert all(r['passed'] for r in proof['episodes'] if r['case']['control']<6)
    save(path,dict(version='sustained-structure-v21-return-order-r1',stage=stage,cases=cases(stage),config=CONFIG,
        source_sha256=hashes(),assets_sha256=asset_hashes(),packages=versions(),system=SYSTEM,candidates=candidates(),
        changes='新C6/7仅green放到真实返程之后；H共同前缀green保留源区，机器人角色统一先buffer到检查支撑、返回后再投LR；伙伴角色留载返回。检查台buffer不请求检查。',
        unchanged='原C/运行源/几何/曲线/服务规则/目标/11菜单不改。H两个角色都公开要求载台返回，反盘条件不删除。',
        original_C_audit_sha256=sha(RESULT/'C_audit_dev0.json')))
    print('独立冻结r1',stage,sha(path),flush=True)


def rollout(case,stage):
    folder=RESULT/'raw'/(stage+'_r1')/case['id'];folder.mkdir(parents=True)
    world=StructureWorld(case['seed'],trace_path=folder/'ticks.jsonl.gz',service_trace_path=folder/'service_ticks.jsonl.gz')
    ep=Episode(world,case['initial_blue'],case['reply'],'stay','H');rows=[];initial=copy.deepcopy(world.state());checkpoints={}
    def act(choice):
        observation=ep.observation();before=copy.deepcopy(world.state());service_before=ep.service.snapshot();history_before=copy.deepcopy(ep.history)
        result=ep.act(choice);after=copy.deepcopy(world.state())
        rows.append(dict(sequence=len(rows),choice=choice,observation=observation,
            messages=[dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(observation,ensure_ascii=False))],
            before_state=before,after_state=after,before_tick=before['tick'],after_tick=after['tick'],
            service_before=service_before,service_after=ep.service.snapshot(),history_before=history_before,
            history_after=copy.deepcopy(ep.history),result=result))
        save(folder/'decisions.json',rows);keyframe(world,folder/'frames')
        print(case['id'],len(rows),choice,result['valid'],world.tick,flush=True)
        if result.get('execution') and not result['execution']['success']:raise RuntimeError('真实技能失败，原轨迹保留。')
    error=None
    try:
        keyframe(world,folder/'frames');act('request_transport');act('careful_red_left')
        while world.delivery_event is None:act('yield')
        checkpoints['handoff_delivery']=copy.deepcopy(world.state());checkpoints['handoff_prefix_decisions']=len(rows)
        if stage=='C_return':
            if case['control']==6:act('place_blue_left')
            act('request_return')
            while world.return_event is None:act('yield')
            act('yield') # 同原负面控制，额外实际窗口排除瞬态。
            act('careful_green_right');act('declare_done')
        else:
            while not ep.terminated:act(reference_r1(ep.observation()))
        ep.observation();score=terminal_score(ep,world);final=copy.deepcopy(world.state());history=copy.deepcopy(ep.history);service=ep.service.snapshot()
        rejected=False
        try:ep.act('yield')
        except RuntimeError:rejected=True
        immutable=rejected and equal(final,world.state()) and history==ep.history and service==ep.service.snapshot()
    except Exception as exc:
        error=repr(exc);save(folder/'failure.json',dict(error=error,state=world.state(),history=ep.history))
        ep.observation();score=terminal_score(ep,world);final=copy.deepcopy(world.state());immutable=False
    finally:world.close()
    expected=stage=='H'
    summary=dict(case=case,initial_state=initial,final_state=final,public_history=ep.history,
        cost=ep.cost,service=ep.service.snapshot(),checkpoints=checkpoints,termination_reason=ep.termination_reason,
        terminal_score=score,expected_task_success=expected,runner_expected_match=score['declared_task_success']==expected and immutable and error is None,
        after_terminal_immutable=immutable,infrastructure_failure=error,common_start_tick=world.common_start_tick,end_tick=world.tick,makespan_ticks=world.tick-world.common_start_tick,
        body_ids=dict(robot=world.robot,carrier=world.partner,inspection=world.inspection,inspection_walls=world.inspection_walls,presence=world.presence,objects=world.objects),
        canonical_physics=digest(folder/'ticks.jsonl.gz'),pid=os.getpid())
    save(folder/'summary.json',summary);return summary


def run(stage):
    f=json.loads(freeze_path(stage).read_text());assert f['source_sha256']==hashes() and f['assets_sha256']==asset_hashes() and f['packages']==versions()
    assert not (RESULT/'raw'/(stage+'_r1')).exists()
    reports=[rollout(case,stage) for case in f['cases']]
    result=dict(stage=stage,total=len(reports),runner_expected_matches=sum(r['runner_expected_match'] for r in reports),
        task_success=sum(r['terminal_score']['declared_task_success'] for r in reports),episodes=reports,source_sha256=hashes(),freeze_sha256=sha(freeze_path(stage)))
    save(RESULT/f'{stage}_summary_r1.json',result);print('阶段完成r1',stage,result['runner_expected_matches'],result['task_success'],flush=True)
    assert result['runner_expected_matches']==len(reports)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('C_return','H'));p.add_argument('--freeze',action='store_true');args=p.parse_args()
    freeze(args.stage) if args.freeze else run(args.stage)
