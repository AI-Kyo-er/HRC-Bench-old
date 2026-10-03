"""先冻结协议，再实际运行16规则参考；独立核对旧v11机械轨迹。"""
import argparse
import copy
import difflib
import json
import os
import datetime

from experiments.physical.run import ROOT,save,sha,versions,asset_hashes
from experiments.structure_v11.run import SOURCES as OLD_SOURCES
from experiments.structure_v11.protocol import SYSTEM as OLD_SYSTEM
from experiments.structure_v5.audit import contact_audit
from experiments.structure_v5.run import keyframe,prefix_digest
from experiments.structure_v7.world import NeutralWorld
from experiments.structure_handoff_v15.protocol import Episode,cases,reference,reduce_history,effective_blue_returns,SYSTEM,CHILD_CONTENT

RESULT=ROOT/'results/structure_handoff_v15'
FREEZE=ROOT/'experiments/structure_handoff_v15/cases/reference_freeze.json'
SOURCES=OLD_SOURCES+['experiments/structure_handoff_v15/protocol.py','experiments/structure_handoff_v15/reference_run.py']


def hashes():return {n:sha(ROOT/n) for n in SOURCES}
def old_id(case):return case['id'].replace('B_handoff_','B_update_',1)


def review():
    case=cases()[0];source=ROOT/'results/structure_v11/raw/reference'/old_id(case)/'decisions.json'
    row=json.loads(source.read_text())[3];obs=copy.deepcopy(row['observation'])
    old_child=next(e['content'] for e in obs['history'] if e['kind']=='accepted_child')
    for e in obs['history']:
        if e['kind']=='accepted_child':e['content']=CHILD_CONTENT
    obs['history'].append(dict(kind='partner_handoff',content='局部检查已结束，现在交还blue，按当前有效外层约定继续。'))
    result=dict(old_system=OLD_SYSTEM,new_system=SYSTEM,system_diff=''.join(difflib.unified_diff(OLD_SYSTEM.splitlines(True),SYSTEM.splitlines(True),fromfile='v11',tofile='v15')),
        history_content_changes=[dict(kind='accepted_child',old=old_child,new=CHILD_CONTENT)],unchanged_local_check_passed=next(e for e in obs['history'] if e['kind']=='local_check_passed'),
        new_handoff_event=obs['history'][-1],sample_proposed_messages=[dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(obs,ensure_ascii=False))],
        source_path=str(source.relative_to(ROOT)),source_sha256=sha(source),planned_observation_not_new_physical_rollout=True,
        robot_budget=12,old_d5_remaining=8,new_handoff_remaining=9,old_history_events=15,new_history_events=13,
        green_completion_is_sampling_time_not_handoff_precondition=True)
    save(RESULT/'protocol_review.json',result)
    (RESULT/'protocol_review.md').write_text('# v15运行前公开协议变更\n\n```diff\n'+result['system_diff']+'```\n\naccepted_child：\n\n旧：'+old_child+'\n\n新：'+CHILD_CONTENT+
        '\n\nlocal_check_passed原“可终止指导”保持；伙伴交还不透露左右。以下仅旧实际D4承载计划事件的审核样例，不是新轨迹。\n\n```json\n'+json.dumps(obs['history'],ensure_ascii=False,indent=2)+'\n```\n')
    print('公开system/初始指导差异及新history样例已导出。',flush=True)


def freeze():
    if FREEZE.exists():raise RuntimeError('禁止覆盖物理协议冻结。')
    old_freeze=ROOT/'experiments/structure_v11/cases/reference_freeze.json';old=json.loads(old_freeze.read_text())
    assert old['source_sha256']=={n:sha(ROOT/n) for n in old['source_sha256']}
    assert old['packages']==versions() and old['assets_sha256']==asset_hashes()
    review()
    save(FREEZE,dict(version='structure-handoff-v15.0',cases=cases(),source_sha256=hashes(),packages=versions(),assets_sha256=asset_hashes(),
        old_reference_freeze_sha256=sha(old_freeze),review_sha256=sha(RESULT/'protocol_review.json'),system=SYSTEM,candidate_count=22,
        reference_sampling='stage→yield→green真实成功后发送公开handoff→blue。green不是交还合法性前提，物理路径与旧v11相同。',
        event_cost='交还是0tick外生伙伴公开事件、0机器人决策，不借机器人finish计成本；提议与回应保持原时点。',
        budget=dict(initial=12,handoff_checkpoint_remaining=9,old_d5_remaining=8),
        interpretation='脚本响应伙伴接口对照，手工主动finish仍合法；不是自然人/纯措辞因果/神经闭环/组合泛化。'))
    print('物理协议冻结',sha(FREEZE),flush=True)


def rollout(case,folder):
    folder.mkdir(parents=True);world=NeutralWorld(case['seed'],trace_path=folder/'ticks.jsonl.gz');rows=[]
    try:
        ep=Episode(case,world);checkpoint=None;rendered=case['seed']==60 and case['reply']=='accepted' and case['initial_blue']=='left'
        if rendered:keyframe(world,folder/'frames')
        for _ in range(case['step_budget']):
            if ep.success():break
            obs=ep.observation();messages=ep.messages();choice=reference(obs);before=world.tick;result=ep.act(choice)
            rows.append(dict(observation=obs,messages=messages,prediction=dict(response=json.dumps(dict(choice=choice)),policy='public_history_reference'),
                result=result,before_tick=before,after_tick=world.tick))
            print(case['id'],len(rows),choice,result['feedback'],flush=True)
            if rendered:keyframe(world,folder/'frames')
            # reference采样时点，不是protocol前提；核心方法也允许green之前交还。
            if choice=='place_green_right' and result.get('execution',{}).get('success'):
                handoff=ep.partner_handoff();assert handoff['valid'];checkpoint=ep.observation()
                save(folder/'handoff.json',dict(result=handoff,audit=ep.handoff_audit,observation=checkpoint))
                if rendered:keyframe(world,folder/'frames')
        s=dict(case=case,success=ep.success(),cost=ep.cost,partner_handoffs=ep.partner_handoffs,rejected_handoffs=ep.rejected_handoffs,
            prefix_execution=ep.prefix,final_state=world.state(),update_audit=ep.update_audit,handoff_audit=ep.handoff_audit,
            checkpoint_observation=checkpoint,first_blue_return_attempt=ep.first_blue_return_attempt,pre_first_blue_actions=ep.pre_first_blue_actions,
            final_public_reduction_for_audit=reduce_history(ep.history),
            green_done_while_child=any(r['result']['choice']=='place_green_right' and reduce_history(r['observation']['history'])['active'] and r['result']['execution']['success'] for r in rows),
            robot_partner_online=copy.deepcopy(world.contact_audit),object_partner_online=copy.deepcopy(world.object_partner_audit),
            body_ids=dict(robot=world.robot,partner=world.partner,objects=dict(world.objects)))
        save(folder/'decisions.json',rows)
    except Exception as exc:
        save(folder/'failure.json',dict(case=case,error=repr(exc),state=world.state(),decisions=rows,source_sha256=hashes()))
        save(folder/'decisions.json',rows);raise
    finally:world.close()
    ids=s['body_ids'];audit=contact_audit(folder/'ticks.jsonl.gz',ids['robot'],ids['partner'],ids['objects'].values());s['contacts']=audit
    assert audit['total_ticks']==s['robot_partner_online']['total_ticks']
    assert audit['robot_partner']['ticks']==s['robot_partner_online']['robot_partner_ticks'] and audit['object_partner']['ticks']==s['object_partner_online']['ticks']
    old_folder=ROOT/'results/structure_v11/raw/reference'/old_id(case);old=json.loads((old_folder/'summary.json').read_text())
    old_rows=json.loads((old_folder/'decisions.json').read_text());handoff=s['handoff_audit'];first=s['first_blue_return_attempt']
    prefix=prefix_digest(folder/'ticks.jsonl.gz',handoff['after']['tick']);full=prefix_digest(folder/'ticks.jsonl.gz',s['final_state']['tick'])
    checks=dict(handoff_zero_tick=handoff['before']==handoff['after'],old_d5_physical_exact=handoff['after']==old['finish_audit']['after'],
        full_prefix_trace_exact=prefix==prefix_digest(old_folder/'ticks.jsonl.gz',old['finish_audit']['after']['tick']),
        complete_trace_exact=full==prefix_digest(old_folder/'ticks.jsonl.gz',old['final_state']['tick']),final_physical_exact=s['final_state']==old['final_state'],
        primitive_choices_except_zero_finish_exact=[r['result']['choice'] for r in rows]==[r['result']['choice'] for r in old_rows if r['result']['choice']!='finish_guidance'],
        robot_decisions_four=s['cost']['decisions']==4 and s['cost']['finishes']==0,green_preserved=handoff['green_right_before'] and handoff['green_right_after'],
        child_ended=not handoff['public_after']['active'] and handoff['public_after']['ended'],blue_still_neutral=checkpoint['physical_placements']['blue']==['neutral'],
        budget_nine=checkpoint['remaining_decisions']==9,event_count_thirteen=len(checkpoint['history'])==13,whole_task_not_done_at_handoff=not handoff['global_success_immediately_after_handoff'],
        first_return_correct_without_prior_feedback=bool(first and first['target_correct'] and first['placement_success'] and first['prior_target_corrections']==0),
        zero_contact_records=audit['zero_record_passed'] and audit['all_missing_distance_records']==0)
    s.update(checks=checks,passed=s['success'] and s['green_done_while_child'] and all(checks.values()),
        effective_blue_returns=effective_blue_returns(checkpoint),prefix_canonical_sha256=prefix,full_trace_canonical_sha256=full,old_case_id=old_id(case))
    save(folder/'summary.json',s);return s


def run():
    frozen=json.loads(FREEZE.read_text());assert frozen['source_sha256']==hashes() and frozen['packages']==versions() and frozen['assets_sha256']==asset_hashes()
    output=RESULT/'raw/reference';output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()):raise RuntimeError('禁止覆盖物理参考。')
    save(output/'started.json',dict(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),freeze_sha256=sha(FREEZE)))
    rows=[rollout(c,output/c['id']) for c in frozen['cases']]
    summary=dict(total=16,passed=sum(r['passed'] for r in rows),success=sum(r['success'] for r in rows),
        ticks=sum(r['contacts']['total_ticks'] for r in rows),robot_partner_ticks=sum(r['contacts']['robot_partner']['ticks'] for r in rows),
        object_partner_ticks=sum(r['contacts']['object_partner']['ticks'] for r in rows),robot_decisions=sum(r['cost']['decisions'] for r in rows),
        partner_handoffs=sum(r['partner_handoffs'] for r in rows),physical_attempts_including_red_prefix=sum(r['cost']['physical_attempts']+1 for r in rows),
        episodes=[dict(id=r['case']['id'],passed=r['passed'],checks=r['checks']) for r in rows],freeze_sha256=sha(FREEZE))
    save(RESULT/'reference_summary.json',summary);save(output/'finished.json',dict(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),episodes=16))
    assert summary['passed']==16;print('16物理参考完成',json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('review','freeze','run'));a=p.parse_args()
    {'review':review,'freeze':freeze,'run':run}[a.stage]()
