"""36固定控制/参考，先C8；只跑真实CPU动力学，不调用模型。"""
import argparse
import copy
import json
import os
from pathlib import Path
from experiments.physical.run import ROOT,save,sha,asset_hashes,versions
from experiments.structure_foundation_v20.run_v1 import SOURCES as OLD_SOURCES
from experiments.structure_foundation_v20.canonical import equal,digest
from experiments.structure_foundation_v20.audit_v2 import stable_region
from experiments.structure_v5.run import keyframe
from experiments.sustained_structure_v21.world import StructureWorld
from experiments.sustained_structure_v21.protocol import Episode,reference,public_ledger,SYSTEM,candidates
from experiments.sustained_structure_v21.service import CONFIG
from experiments.sustained_structure_v21.cases import cases

RESULT=ROOT/'results/sustained_structure_v21'
SOURCES=OLD_SOURCES+[
    'experiments/structure_foundation_v20/audit_v2.py',
    *['experiments/sustained_structure_v21/'+name for name in
      ('config.json','cases.py','service.py','world.py','protocol.py','run.py')],
    'tests/test_sustained_structure_v21.py']


def hashes():return {name:sha(ROOT/name) for name in SOURCES}


def freeze_path(stage):return ROOT/f'experiments/sustained_structure_v21/cases/{stage}_freeze_dev0.json'


def terminal_score(ep,world):
    # 独立终止评分；没有任何字段回到act反馈或策略输入。
    ledger=public_ledger(ep.history);physical=world.state();role=ledger['blue_role']
    facts=dict(red_actual_left=stable_region(physical,'red','left'),
        green_actual_right=stable_region(physical,'green','right'),
        check_contribution_completed=not ledger['inspection_required'] or ep.service.completed,
        no_active_child=not ledger['child_active'],
        carrier_return_completed=not ledger['carrier_return_required'] or world.return_event is not None,
        blue_role_completed=(world.payload_return_event is not None and world.return_facts()['payload_returned'])
            if role=='partner_return' else stable_region(physical,'blue',ledger['goals']['blue']))
    return dict(facts=facts,task_compliant=all(facts.values()),declared_task_success=all(facts.values()) and ep.termination_reason=='declared_done')


def freeze(stage):
    path=freeze_path(stage);assert not path.exists(),'不覆盖已冻结版本'
    if stage!='C':assert json.loads((RESULT/'C_audit_dev0.json').read_text())['all_controls_evidence_and_safety_pass']
    save(path,dict(version=CONFIG['version'],stage=stage,cases=cases(stage),config=CONFIG,
        source_sha256=hashes(),assets_sha256=asset_hashes(),packages=versions(),system=SYSTEM,candidates=candidates(),
        score_scope='任务符合与物理接触安全分列；C后四任务故意失败不算任务成功，控制检测符合另计。',
        candidate_scope='所有条件同11；无finish；安全且当前来源核验的错误目标/活动child移动允许真实执行。',
        event_timing='事件机在真实物理step之后采样，同tick服务日志独立保存；actual_tick与动作边界observed_tick分列。',
        policy='公开history归约与真实区域，不读case/score/未来安排；闭环32预算。'))
    print('冻结',stage,sha(path),flush=True)


def rollout(case,stage):
    folder=RESULT/'raw'/stage/case['id'];folder.mkdir(parents=True)
    world=StructureWorld(case['seed'],trace_path=folder/'ticks.jsonl.gz',service_trace_path=folder/'service_ticks.jsonl.gz')
    family='H' if case['family']=='H' or (case['family']=='C' and case['control']>=6) else 'N'
    ep=Episode(world,case['initial_blue'],case['reply'],case['presence'],family)
    rows=[];checkpoints={};initial=copy.deepcopy(world.state())

    def act(choice):
        observation=ep.observation();before=copy.deepcopy(world.state());service_before=ep.service.snapshot()
        history_before=copy.deepcopy(ep.history);message=ep.messages()
        result=ep.act(choice);after=copy.deepcopy(world.state())
        rows.append(dict(sequence=len(rows),choice=choice,observation=observation,messages=message,
            before_state=before,after_state=after,before_tick=before['tick'],after_tick=after['tick'],
            service_before=service_before,service_after=ep.service.snapshot(),
            history_before=history_before,history_after=copy.deepcopy(ep.history),result=result))
        save(folder/'decisions.json',rows);keyframe(world,folder/'frames')
        print(case['id'],len(rows),choice,result['valid'],world.tick,flush=True)
        if result.get('execution') and not result['execution']['success']:raise RuntimeError('指定物理技能失败，原轨迹保留。')
        return result

    def seen(kind):return any(event['kind']==kind for event in ep.history)

    def wait_until(predicate):
        while not predicate():
            if ep.terminated:raise RuntimeError('等待目标事实前Episode已经终止。')
            act('yield')

    def prefix(check=False):
        act('request_transport');act('careful_red_left')
        if not check:act('careful_green_right')
        wait_until(lambda: world.delivery_event is not None)
        checkpoints['handoff_delivery']=copy.deepcopy(world.state())
        checkpoints['handoff_prefix_decisions']=len(rows)
        if check:
            act('place_blue_inspection');act('request_check')
            checkpoints['check_request_tick']=world.tick

    def complete(policy='public_ledger_progress'):
        while not ep.terminated:act(reference(ep.observation(),policy))

    infrastructure_failure=None
    try:
        keyframe(world,folder/'frames')
        if stage=='C':
            control=case['control']
            if control==0:
                early=act('request_check');act('yield')
                checkpoints['early_no_queue']=dict(reply=early['check_reply'],service=ep.service.snapshot(),
                    transport_start_tick=world.delivery_start_tick,physical=copy.deepcopy(world.state()))
                complete()
            elif control==1:
                prefix(check=True);before=ep.service.snapshot();tick=world.tick
                duplicate=act('request_check')
                checkpoints['duplicate']=dict(before=before,after=ep.service.snapshot(),tick_before=tick,tick_after=world.tick,reply=duplicate['check_reply'])
                complete()
            elif control==2:
                prefix(check=True);wait_until(lambda:seen('presence_far_observed'))
                checkpoints['paused_before_move']=ep.service.snapshot()
                act('place_blue_left');wait_until(lambda:seen('presence_near_observed'))
                before=ep.service.snapshot();act('yield')
                checkpoints['off_table_after_return']=dict(before=before,after=ep.service.snapshot(),physical=copy.deepcopy(world.state()))
                act('place_blue_inspection');complete()
            elif control==3:
                prefix(check=True);wait_until(lambda:seen('presence_near_observed'))
                before=ep.service.snapshot();act('yield')
                checkpoints['withdraw_no_restart']=dict(before=before,after=ep.service.snapshot(),physical=copy.deepcopy(world.state()))
                act('request_check');complete()
            elif control==4:act('declare_done')
            elif control==5:prefix(check=True);act('declare_done')
            else:
                prefix()
                if control==6:act('place_blue_left')
                act('request_return');wait_until(lambda:world.return_event is not None)
                # 同一实际等待窗口排除载台刚到位而载荷尚未稳定的瞬态。
                act('yield');act('declare_done')
        else:
            if stage=='H':prefix()
            complete(case['policy'])
        ep.observation();score=terminal_score(ep,world);final=copy.deepcopy(world.state());history=copy.deepcopy(ep.history);service=ep.service.snapshot()
        rejected=False
        try:ep.act('yield')
        except RuntimeError:rejected=True
        terminal_immutable=rejected and equal(final,world.state()) and history==ep.history and service==ep.service.snapshot()
    except Exception as error:
        infrastructure_failure=repr(error)
        save(folder/'failure.json',dict(error=repr(error),state=world.state(),history=ep.history,service=ep.service.snapshot()))
        ep.observation();score=terminal_score(ep,world);final=copy.deepcopy(world.state());terminal_immutable=False
    finally:world.close()
    expected_success=not(stage=='C' and case['control']>=4)
    summary=dict(case=case,initial_state=initial,final_state=final,public_history=ep.history,
        cost=ep.cost,service=ep.service.snapshot(),checkpoints=checkpoints,termination_reason=ep.termination_reason,
        terminal_score=score,expected_task_success=expected_success,
        runner_expected_match=score['declared_task_success']==expected_success and terminal_immutable and infrastructure_failure is None,
        after_terminal_immutable=terminal_immutable,infrastructure_failure=infrastructure_failure,
        common_start_tick=world.common_start_tick,end_tick=world.tick,makespan_ticks=world.tick-world.common_start_tick,
        body_ids=dict(robot=world.robot,carrier=world.partner,inspection=world.inspection,inspection_walls=world.inspection_walls,presence=world.presence,objects=world.objects),
        canonical_physics=digest(folder/'ticks.jsonl.gz'),pid=os.getpid())
    save(folder/'summary.json',summary);return summary


def run(stage):
    f=json.loads(freeze_path(stage).read_text())
    assert f['source_sha256']==hashes() and f['assets_sha256']==asset_hashes() and f['packages']==versions()
    assert not (RESULT/'raw'/stage).exists(),'禁止覆写已执行物理'
    reports=[rollout(case,stage) for case in f['cases']]
    result=dict(stage=stage,total=len(reports),runner_expected_matches=sum(s['runner_expected_match'] for s in reports),
        task_success=sum(s['terminal_score']['declared_task_success'] for s in reports),episodes=reports,
        source_sha256=hashes(),freeze_sha256=sha(freeze_path(stage)))
    save(RESULT/f'{stage}_summary_dev0.json',result)
    print('阶段完成',stage,result['runner_expected_matches'],result['task_success'],flush=True)
    assert result['runner_expected_matches']==len(reports)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('C','N','H'));parser.add_argument('--freeze',action='store_true')
    args=parser.parse_args();freeze(args.stage) if args.freeze else run(args.stage)
