"""仅C0–5合格支持无返程N；不把C6/7真实失败改为通过。"""
import json
from experiments.physical.run import ROOT,save,sha,asset_hashes,versions
from experiments.sustained_structure_v21.run import RESULT,freeze_path,hashes
from experiments.sustained_structure_v21.cases import cases
from experiments.sustained_structure_v21.protocol import SYSTEM,candidates
from experiments.sustained_structure_v21.service import CONFIG


def freeze():
    path=freeze_path('N');assert not path.exists()
    proof=json.loads((RESULT/'C_audit_dev0.json').read_text())
    controls=[row for row in proof['episodes'] if row['case']['control']<6]
    assert len(controls)==6 and all(row['passed'] for row in controls)
    save(path,dict(version=CONFIG['version'],stage='N',cases=cases('N'),config=CONFIG,
        source_sha256=hashes(),assets_sha256=asset_hashes(),packages=versions(),system=SYSTEM,candidates=candidates(),
        freeze_generator_sha256=sha(ROOT/'experiments/sustained_structure_v21/freeze_n.py'),
        prerequisite=dict(path='results/sustained_structure_v21/C_audit_dev0.json',sha256=sha(RESULT/'C_audit_dev0.json'),
            controls=[r['id'] for r in controls],all_original_C_pass=proof['all_controls_evidence_and_safety_pass'],
            reason='N不涉及返程；仅独立合格C0–5为前提，原C6/7真实返程碰撞仍为失败，后续H另修订/冻结。'),
        score_scope='完成声明真实终止；任务符合与物理安全分列。',
        candidate_scope='统一11动作不按隐藏目标筛选；真实可执行错误目标/活动child移动允许。'))
    print('独立冻结N',sha(path),flush=True)


if __name__=='__main__':freeze()
