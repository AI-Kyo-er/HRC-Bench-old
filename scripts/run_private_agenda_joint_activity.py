#!/usr/bin/env python3
"""双阶段生成式人策略的真实共同活动入口；复用冻结动作与公开观测。"""
from hashlib import sha256
import json
from pathlib import Path
import runpy
import sys

from hrc_pilot.private_agenda_human import PrivateAgendaHumanPolicy
import hrc_pilot.reasoning_constrained_human as reasoning


def main():
    if '--human-source' in sys.argv and sys.argv[sys.argv.index('--human-source')+1]!='neural':
        raise ValueError('私人意图入口只用于真实生成式人，不标注固定参考为神经策略')
    if '--human-complete-observation' not in sys.argv:
        raise ValueError('本条件要求显式完整公共观测')
    sources=[Path(__file__),Path('src/hrc_pilot/private_agenda_human.py')]
    hashes={str(p):sha256(p.read_bytes()).hexdigest() for p in sources}
    output=Path(sys.argv[sys.argv.index('--output-dir')+1])
    # 类选择仅决定策略实现；需要、参与和当前贡献全部由两次NN自己生成。
    reasoning.ReasoningConstrainedHumanPolicy=PrivateAgendaHumanPolicy
    try:runpy.run_path('scripts/run_reasoning_constrained_joint_activity.py',run_name='__main__')
    finally:
        if (output/'provenance.json').exists():
            p=json.loads((output/'provenance.json').read_text())
            p.update(human_policy_interface='private_agenda_then_current_contribution_v1',
                     human_intention_model='online_neural_private_needs_and_arrangement_v1',
                     human_neural_inferences_per_decision=2,
                     private_agenda_shared_with_robot=False)
            p['source_sha256'].update(hashes)
            p['source_files_changed_during_run'].extend(str(q) for q in sources if sha256(q.read_bytes()).hexdigest()!=hashes[str(q)])
            (output/'provenance.json').write_text(json.dumps(p,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
