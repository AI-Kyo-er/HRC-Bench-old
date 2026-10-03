"""在报告及全部进程真实退出后归档完整日志SHA，不哈希仍写入的自身日志。"""
import json
import subprocess
from datetime import datetime,timezone
from pathlib import Path
from experiments.physical.run import ROOT,save,sha,asset_hashes,versions
from experiments.dual_goal_v25.run import RESULT,freeze_path,hashes


def finalize():
    summary=json.loads((RESULT/'final_summary.json').read_text());assert all(summary['checks'].values())
    lifecycle=json.loads((RESULT/'raw'/'lifecycle.json').read_text());assert all(r['exit_code']==0 for r in lifecycle['formal_runs'].values())
    pids=[v['pid'] for v in lifecycle['formal_runs'].values() if 'pid' in v]
    probes={str(pid):subprocess.run(['ps','-p',str(pid),'-o','pid=,stat=,etime=,args='],capture_output=True,text=True).stdout for pid in pids}
    assert not any(probes.values())
    sources=hashes();assets=asset_hashes();stages={}
    for stage in ('control','reference','local'):
        f=json.loads(freeze_path(stage).read_text());a=json.loads((RESULT/f'{stage}_audit_dev0.json').read_text())
        assert f['source_sha256']==sources and f['assets_sha256']==assets and f['packages']==versions()
        copied=RESULT/'raw'/f'{stage}_audit_sources'/'audit.py'
        stages[stage]=dict(freeze_sha256=sha(freeze_path(stage)),audit_source_sha256=a['audit_source_sha256'],audit_copy_sha256=sha(copied),
            runtime_copy_all_exact=all(sha(RESULT/'raw'/f'{stage}_runtime_sources'/p)==h for p,h in sources.items()))
        assert stages[stage]['runtime_copy_all_exact'] and stages[stage]['audit_source_sha256']==stages[stage]['audit_copy_sha256']
    raw=(RESULT/'raw').resolve()
    receipt=dict(utc=datetime.now(timezone.utc).isoformat(),source_sha256=sources,assets_sha256=assets,packages=versions(),stages=stages,
        report_source_sha256=sha(ROOT/'experiments/dual_goal_v25/report.py'),finalize_source_sha256=sha(Path(__file__)),
        artifact_sha256={p.name:sha(p) for p in RESULT.glob('*.json') if p.name!='execution_receipt.json'},
        log_sha256={p.name:sha(p) for p in raw.glob('*.log')},lifecycle=lifecycle,pid_probes=probes,
        raw_real_path=str(raw),raw_bytes=sum(p.stat().st_size for p in raw.rglob('*') if p.is_file()),
        tests=dict(focused_passed=15,full_passed=215,full_exit=0,first_focused_error='FakeWorld缺carrier_facts；仅修替身API，原失败源及日志保留。',nature='协议/FakeWorld反例，与48真实物理独立验收分开。'),
        postfreeze_derivation='report新增队列实际生成时刻与规范完整轨迹配对，finalize在report退出后哈希已完成日志；源各独立SHA，不更改冻结评分/运行/物理。',
        storage='raw在数据盘并通过项目软链访问',no_model_gpu_download=True,no_retries_or_condition_changes=True,
        timing='makespan自t0=240到声明，含停车/等待；trace含初始化。U4提前负例耗时不是效率；局部prefix独立列成本。',
        inference_planning='CPU tokenizer与配置/生成源码只读统计仅未来容量建议，未加载模型；3GiB不是prefill显存保证，48步输入界未获证明。',
        scope='48指定规则参考/能力控制与2预设任务负例；非模型、结构泛化、纯结构因果或完整六结构。')
    save(RESULT/'execution_receipt.json',receipt)
    print('最终回执完成',summary['strict_passed'],summary['task_success'],summary['total_ticks'])


if __name__=='__main__':finalize()
