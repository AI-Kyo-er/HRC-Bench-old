"""第二完整四臂组独立预审；首组仅复用已保存结果，不重复全tick审计。"""
import json
import os
from pathlib import Path

from transformers import AutoTokenizer
from experiments.physical.run import ROOT, save, sha
from experiments.dual_goal_model_v26.run import RESULT, FREEZE, hashes
from experiments.dual_goal_model_v26.audit import episode_audit
from experiments.dual_goal_model_v26.report import PHYSICAL


def main():
    f = json.loads(FREEZE.read_text())
    assert f['source_sha256'] == hashes()
    first_path = RESULT / 'first_full_group_preaudit.json'
    definition_path = RESULT / 'first_group_reconstruction_definition.json'
    first = json.loads(first_path.read_text())
    definition = json.loads(definition_path.read_text())
    assert first['total'] == 4 and first['freeze_sha256'] == sha(FREEZE)
    assert set(definition['excluded_checks']) == set(PHYSICAL)
    records = [r for r in f['episodes'] if r['stage'] == 'full' and r['group'] == 1]
    assert len(records) == 4
    assert all((RESULT / 'raw/episodes' / r['id'] / 'summary.json').exists() for r in records)
    copied = RESULT / 'raw/second_full_group_audit_sources'
    copied.mkdir(parents=True, exist_ok=True)
    sources = {}
    for name in ('audit.py', 'report.py', 'timing_stage_audit.py'):
        p = ROOT / 'experiments/dual_goal_model_v26' / name
        (copied / name).write_bytes(p.read_bytes())
        sources[name] = sha(p)
    assert first['independent_source_sha256']['audit.py'] == sources['audit.py']
    assert first['independent_source_sha256']['report.py'] == sources['report.py']
    print('第二组独立审计启动', os.getpid(), sources, flush=True)
    tokenizer = AutoTokenizer.from_pretrained(f['model_spec']['path'], local_files_only=True)
    reports = []
    for record in records:
        folder = RESULT / 'raw/episodes' / record['id']
        s = json.loads((folder / 'summary.json').read_text())
        a = episode_audit(folder, tokenizer)
        assert set(a['checks']) == set(definition['included_checks'] + definition['excluded_checks'])
        row = dict(id=record['id'], expression=record['case']['expression'], view=record['view'],
                   reconstruction_consistent=all(a['checks'][k] for k in definition['included_checks']),
                   physical_contract_ok=all(a['checks'][k] for k in PHYSICAL),
                   task_success=a['task_success'], physically_safe=a['physically_safe'],
                   termination_reason=s['termination_reason'], parse_failures=s['parse_failures'],
                   generation_hit_limit=s['generation_hit_limit'], model_calls=s['model_calls'],
                   cost=s['cost'], makespan_ticks=s['makespan_ticks'],
                   failed_checks=[k for k, v in a['checks'].items() if not v], report=a)
        reports.append(row)
        print(row['id'], a['passed'], row['reconstruction_consistent'], row['task_success'],
              row['physically_safe'], row['termination_reason'], row['failed_checks'], flush=True)
    assert f['source_sha256'] == hashes()
    assert sources == {name: sha(ROOT / 'experiments/dual_goal_model_v26' / name) for name in sources}
    result = dict(total=4, reconstruction_consistent=sum(r['reconstruction_consistent'] for r in reports),
                  strict_passed=sum(r['report']['passed'] for r in reports),
                  task_success=sum(r['task_success'] for r in reports),
                  physically_safe=sum(r['physically_safe'] for r in reports),
                  total_ticks=sum(r['report']['total_ticks'] for r in reports), episodes=reports,
                  independent_source_sha256=sources, script_sha256=sources['timing_stage_audit.py'],
                  freeze_sha256=sha(FREEZE), reconstruction_definition_sha256=sha(definition_path),
                  first_group_existing_report_sha256=sha(first_path),
                  scope='第二组四臂全tick CPU预审；原passed/全部checks/接触/支撑/神经核验保留。首组仅读取已审结果，无模型或物理重跑。')
    second_path = RESULT / 'second_full_group_preaudit.json'
    save(second_path, result)

    def compact(row):
        a = row['report']
        return dict(id=row['id'], original_passed=a['passed'], failed_checks=row['failed_checks'],
                    reconstruction_consistent=row['reconstruction_consistent'], task_success=a['task_success'],
                    physically_safe=a['physically_safe'], physical_contract_ok=row['physical_contract_ok'],
                    physical_contract_checks={k: a['checks'][k] for k in PHYSICAL},
                    termination_reason=row['termination_reason'], actual_score=a['actual_score'],
                    service=a['service'], qualified_ticks=a['qualified_ticks'], leg_support=a['leg_support'],
                    contact_groups=a['groups'], neural_checks=a['neural']['checks'],
                    parse_failures=row['parse_failures'], generation_hit_limit=row['generation_hit_limit'],
                    model_calls=row['model_calls'], cost=row['cost'],
                    failed_termination_ticks=row['makespan_ticks'] if not a['task_success'] else None,
                    successful_completion_ticks=row['makespan_ticks'] if a['task_success'] else None)

    before = {(r['expression'], r['view']): r for r in first['episodes']}
    after = {(r['expression'], r['view']): r for r in reports}
    assert before.keys() == after.keys() and len(before) == 4
    pairs = []
    for key in sorted(before):
        b, a = before[key], after[key]
        bc, ac = b['report']['case'], a['report']['case']
        assert {k: v for k, v in bc.items() if k not in ('id', 'timing')} == {
            k: v for k, v in ac.items() if k not in ('id', 'timing')}
        assert bc['timing'] == 'before_check' and ac['timing'] == 'after_handoff'
        pairs.append(dict(expression=key[0], view=key[1], before_check=compact(b),
                          after_handoff=compact(a), both_task_success=b['task_success'] and a['task_success']))
    save(RESULT / 'first_two_groups_timing_preaudit.json', dict(
        total=8, pairs=pairs, first_group_source_sha256=sha(first_path),
        second_group_source_sha256=sha(second_path), script_sha256=sources['timing_stage_audit.py'],
        task_success=sum(r['task_success'] for r in first['episodes'] + reports),
        physically_safe=sum(r['physically_safe'] for r in first['episodes'] + reports),
        cost_interpretation='逐例失败终止耗时保留，不作为任务完成效率；阶段配对不构成总体时机效应或显著性证据。',
        scope='固定前两组八例描述配对；首组不重复全trace审计；统一80终态仍覆盖全部。'))
    print('第二组预审与八例时机配对完成', result['strict_passed'], result['task_success'], result['physically_safe'], flush=True)


if __name__ == '__main__':
    main()
