"""冻结运行之后的只读派生归档；不改已执行源或重跑。"""
import json
import math
import os
import subprocess
from datetime import datetime,timezone
from pathlib import Path
from experiments.physical.run import ROOT,save,sha,asset_hashes,versions
from experiments.shared_slots_v24.run import RESULT,FREEZE,hashes,PREFIX,CONFIG
from experiments.shared_slots_v24.audit import destination_facts,supported_by
from experiments.transport_cycle_v22.audit import independent_facts
from experiments.transport_cycle_v22.cycle import CycleLedger


def source_audit(folder):
    summary=json.loads((folder/'summary.json').read_text());rows=json.loads((folder/'decisions.json').read_text());ids=summary['body_ids'];last={'red':'source','green':'source','blue':'carrier'};records=[]
    for row in rows:
        if not row['result'].get('physical_attempt'):continue
        _,item,target=row['choice'].split('_');before=row['before_state'];origin=last[item]
        if origin=='carrier':
            f=independent_facts(before,ids,CycleLedger());facts=dict(stable=f['near'] and f['payload_stable'],supported=f['supported'])
        elif origin=='source':
            body=ids['objects'][item];actors={ids['robot'],ids['carrier'],ids['inspection'],ids['presence'],*ids['objects'].values(),*ids['inspection_walls']}
            contact=any(body in {c['body_a'],c['body_b']} and len({c['body_a'],c['body_b']})==2 and not (({c['body_a'],c['body_b']}-{body})&actors)
                        and c['contact_distance']<=CONFIG['support_contact_max_distance_m'] and c['normal_force']>CONFIG['support_contact_min_force_n'] for c in before['contacts'])
            facts=dict(stable=math.dist(before['objects'][item]['position'],summary['initial_state']['objects'][item]['position'])<.01 and math.hypot(*before['objects'][item]['velocity'])<.04,supported=contact)
        else:facts=destination_facts(before,item,origin,ids)
        records.append(dict(sequence=row['sequence'],choice=row['choice'],actual_source=origin,facts=facts,passed=all(facts.values())));last[item]=target
    return dict(id=summary['case']['id'],all_sources_actual=all(r['passed'] for r in records),rows=records)


def report():
    runtime=json.loads((RESULT/'control_summary_dev0.json').read_text());audit=json.loads((RESULT/'control_audit_dev0.json').read_text());freeze=json.loads(FREEZE.read_text())
    assert audit['passed']==8 and freeze['source_sha256']==hashes()
    sources=[source_audit(RESULT/'raw'/'dev0'/r['id']) for r in audit['episodes']];assert all(r['all_sources_actual'] for r in sources)
    pairs=[]
    for seed in CONFIG['seeds']:
        es=[e for e in audit['episodes'] if e['id'].endswith('_'+str(seed))]
        prefixes=[e['prefix_physics'] for e in es];same=all(p==prefixes[0] for p in prefixes)
        pairs.append(dict(seed=seed,ids=[e['id'] for e in es],prefixes=prefixes,full_prefix_physics_exact=same));assert same
    groups={g:dict(records=sum(e['groups'][g]['records'] for e in audit['episodes']),ticks=sum(e['groups'][g]['ticks'] for e in audit['episodes']),
        max_normal_force=max(e['groups'][g]['max_normal_force'] for e in audit['episodes'])) for g in audit['episodes'][0]['groups']}
    support=[v for e in audit['episodes'] for v in e['leg_support'].values() if v['loaded']]
    result=dict(total=8,runner_sequence_completed=runtime['control_sequence_completed'],strict_passed=audit['passed'],physically_safe=audit['physically_safe'],
        total_ticks=audit['total_ticks'],total_decisions=sum(e['cost']['decisions'] for e in audit['episodes']),physical_attempts=sum(e['cost']['physical_attempts'] for e in audit['episodes']),
        groups=groups,loaded_motion_ticks=sum(v['ticks'] for v in support),loaded_supported_ticks=sum(v['supported_ticks'] for v in support),prefix_pairs=pairs,
        costs=[dict(id=e['id'],makespan_ticks=e['makespan_ticks'],cost=e['cost']) for e in audit['episodes']],
        max_non_target_interval_displacement_m=max(e['max_non_target_interval_displacement_m'] for e in audit['episodes']),
        max_skill_non_target_displacement_m=max(v for e in audit['episodes'] for p in e['placements'] for v in p['non_target_displacements_m'].values()),
        all_sources_actual=all(r['all_sources_actual'] for r in sources),source_audit=sources,no_check_or_task_success_claim=True,
        report_source_sha256=sha(Path(__file__)))
    save(RESULT/'final_summary.json',result)
    raw=(RESULT/'raw').resolve()
    receipt=dict(utc=datetime.now(timezone.utc).isoformat(),freeze_sha256=sha(FREEZE),source_unchanged=freeze['source_sha256']==hashes(),source_sha256=hashes(),
        assets_unchanged=freeze['assets_sha256']==asset_hashes(),assets_sha256=asset_hashes(),packages=versions(),
        audit_source_sha256=audit['audit_source_sha256'],audit_source_copy_sha256=sha(raw/'audit_sources/audit.py'),report_source_sha256=sha(Path(__file__)),
        artifacts_sha256={p.name:sha(p) for p in RESULT.glob('*.json') if p.name!='execution_receipt.json'},
        log_sha256={p.name:sha(p) for p in raw.glob('*.log')},raw_real_path=str(raw),raw_bytes=sum(p.stat().st_size for p in raw.rglob('*') if p.is_file()),
        handles=dict(run=57791,run_pid=197868,run_exit=0,audit=73119,audit_pid=199234,audit_exit=0,full_tests=45474,full_tests_exit=0),
        pid_probes={str(pid):subprocess.run(['ps','-p',str(pid),'-o','pid=,stat=,etime=,args='],capture_output=True,text=True).stdout for pid in (197868,199234)},
        tests=dict(focused=8,full=200,nature='永久公共事实/独立审计反例，非真实物理'),
        no_gpu_model_download=True,no_retries_or_changed_conditions=True,
        scope='仅8指定几何能力控制，源端支撑/共盘/真实跨盘恢复及接触证据；未请求检查或完成v23共同活动，不是策略/双目标比较。',
        clock='makespan从t0=240到指定序列耗尽，含停车/等待；完整trace包含初始化。不比较墙钟。',
        postfreeze_derivation='report新增只读来源支撑与同seed四序列完整前缀派生，不改变冻结评分/源/物理；report源独立SHA。')
    assert not any(receipt['pid_probes'].values());save(RESULT/'execution_receipt.json',receipt)
    print('归档',result['strict_passed'],result['total_ticks'],result['physical_attempts'],flush=True)


if __name__=='__main__':report()
