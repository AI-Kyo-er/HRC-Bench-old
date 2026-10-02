"""原失败、独立恢复/调度控制及版本回执并列归档。"""
import datetime
import importlib
import json
from experiments.physical.run import ROOT,save,sha

RESULT=ROOT/'results/structure_foundation_v20'

def report():
    stages={name:json.loads((RESULT/f'{name}_audit_dev1.json').read_text()) for name in ('A','BCD','E','F')}
    all_episodes=[r for a in stages.values() for r in a['episodes']];old=json.loads((RESULT/'A_audit_dev0.json').read_text())
    source_checks={}
    for stage,module in (('A','run_v1'),('BCD','run_v1'),('E','run_e'),('F','run_f')):
        m=importlib.import_module('experiments.structure_foundation_v20.'+module);f=json.loads(m.freeze_path(stage).read_text());source_checks[stage]=f['source_sha256']==m.hashes()
    comparisons=[]
    for seed in (120,121):
        for goal in ('left','right'):
            ref=next(r for r in stages['F']['episodes'] if r['id']==f'F_{goal}_{seed}')
            old_during=next(r for r in stages['BCD']['episodes'] if r['id']==f'B_{goal}_during_{seed}')
            old_after=next(r for r in stages['BCD']['episodes'] if r['id']==f'B_{goal}_after_{seed}')
            comparisons.append(dict(seed=seed,first_goal=goal,red_first=dict(passed=ref['passed'],duration_ticks=ref['makespan_ticks'],physical_attempts=ref['physical_attempts']),
                original_during=dict(passed=old_during['passed'],episode_until_end_ticks=old_during['makespan_ticks'],success_duration_ticks=old_during['makespan_ticks'] if old_during['passed'] else None),
                original_after=dict(passed=old_after['passed'],duration_ticks=old_after['makespan_ticks']),
                comparison='F与B_during动作多重集合相同，仅red提前。成功left-during与F均12480tick；失败right-during提前终止时长不是完成时间，不能据此比较效率。'))
    summary=dict(dev1_total=28,dev1_passed=sum(r['passed'] for r in all_episodes),dev1_total_ticks=sum(a['total_ticks'] for a in stages.values()),
        groups={name:dict(total=a['total'],passed=a['passed'],ticks=a['total_ticks']) for name,a in stages.items()},
        dev0=dict(total=4,passed=old['passed'],ticks=old['total_ticks'],robot_inspection_records=sum(r['groups']['forbidden_robot_inspection']['records'] for r in old['episodes']),
            robot_inspection_ticks=sum(r['groups']['forbidden_robot_inspection']['ticks'] for r in old['episodes']),max_force=max(r['groups']['forbidden_robot_inspection']['max_normal_force'] for r in old['episodes'])),
        contacts_records={g:sum(r['groups'][g]['records'] for r in all_episodes) for g in all_episodes[0]['groups']},
        physical_attempts=sum(r['physical_attempts'] for r in all_episodes),zero_tick_repeats=sum(r['zero_tick_repeats'] for r in all_episodes),
        all_runtime_sources_match_freezes=all(source_checks.values()),source_checks=source_checks,scheduling_comparisons=comparisons,
        interpretation='指定物理控制26/28通过、原2动态碰撞不改判。F简单统一red-first安全4/4且无额外成本，当前冲突不支持必须复杂上下文调度。presence仅真实运动、职责退出协议尚未实现；承载返回与空载运动严格分列，非自主/六结构成功。')
    save(RESULT/'final_summary.json',summary)
    handles=dict(dev0_A=dict(run=80708,pid=128998,run_exit=0,audit=64772,audit_pid=130137,audit_exit=1),
        A=dict(run=7182,pid=132009,run_exit=0,audit=76401,audit_exit=0),BCD=dict(run=7943,pid=133641,run_exit=1,audit=48135,audit_pid=137127,audit_exit=1),
        E=dict(run=37641,pid=138218,run_exit=0,audit=49556,audit_pid=138979,audit_exit=0),F=dict(run=93279,pid=140183,run_exit=0,audit=80410,audit_pid=141056,audit_exit=0))
    receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),handles=handles,
        freeze_sha256={stage:sha(importlib.import_module('experiments.structure_foundation_v20.'+module).freeze_path(stage)) for stage,module in (('A','run_v1'),('BCD','run_v1'),('E','run_e'),('F','run_f'))},
        audit_source_sha256={name:a['audit_source_sha256'] for name,a in stages.items()},diagnostic_source_sha256=sha(ROOT/'experiments/structure_foundation_v20/diagnostic.py'),report_source_sha256=sha(ROOT/'experiments/structure_foundation_v20/report.py'),
        artifact_sha256={name:sha(RESULT/name) for name in ('A_audit_dev0.json','A_audit_dev1.json','BCD_audit_dev1.json','E_audit_dev1.json','F_audit_dev1.json','timing_contact_diagnostic.json','final_summary.json','dev0_failure_receipt.json')},
        tests=dict(dev0_focused=6,dev1_focused=4,E_focused=3,F_focused=2,focused_exit=0,preF_full=142,preF_full_handle=93966,preF_full_exit=0,final_full=146,final_full_handle=17124,final_full_exit=0,
            final_full_log_sha256=sha(RESULT/'raw/tests_full_final.log')),
        unexecuted_E_initial=dict(freeze_sha256='1b7a2c6b440a113dd8b0bfda4149d65b18a320fcf1076497e3e37cf7b994c8b5',source_location='raw/unexecuted_E_initial',reason='首次CPU冻结后、未运行物理前把字段存在测试换为实际中间状态反例；旧源/test/freeze保留，实际独立r1冻结。'),
        after_freeze_preservation_audit='A_dev1首次独立审计前加入非目标连续非操纵区间最大位移<.01m；依据既有green保护尺度推广。属于事后派生审计定义，未加入运行gate/未放宽零contact。已执行A audit_v1源存raw/dev1_A_audit_sources，BCD派生audit_v2仅支持真实失败的截短序列。',
        raw_path=str((RESULT/'raw').resolve()),raw_bytes=sum(p.stat().st_size for p in (RESULT/'raw').rglob('*') if p.is_file()),all_runtime_sources_unchanged=all(source_checks.values()),
        concurrency='所有新控制仅CPU；与固定v19 GPU运行98899/PID121752及部分独立CPU审计重叠，不据墙钟比较速度。',no_new_model_or_download=True,
        caution='几何静态净隙只估算，安全依据全tick实测；实际presence到位≠已实现贡献可用/职责退出协议；错误/短路终止时长不当任务完成效率。')
    save(RESULT/'execution_receipt.json',receipt);print('归档',summary['groups'],summary['dev1_total_ticks'],summary['dev1_passed'],flush=True)

if __name__=='__main__':report()
