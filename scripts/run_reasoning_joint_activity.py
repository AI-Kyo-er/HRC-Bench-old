#!/usr/bin/env python3
"""单次原生思考的人意图条件，记录其真实输入输出及计算预算。"""
from hashlib import sha256
import json
from pathlib import Path
import sys

import run_joint_activity as runtime
from hrc_pilot.reasoning_joint_human import ReasoningJointHumanPolicy


if __name__=='__main__':
    sources=[Path(__file__),*[Path('src/hrc_pilot')/name for name in
        ['reasoning_joint_human.py','contribution_joint_human.py','human_contribution_contract.py','semantic_joint_human.py','intent_observation.py']]]
    hashes={str(p):sha256(p.read_bytes()).hexdigest() for p in sources}
    output=Path(sys.argv[sys.argv.index('--output-dir')+1])
    runtime.JointHumanPolicy=ReasoningJointHumanPolicy
    try:runtime.main()
    finally:
        changed=[str(p) for p in sources if sha256(p.read_bytes()).hexdigest()!=hashes[str(p)]]
        adapter={'human_observation_encoding':'intent_semantic_facts_v1',
            'human_contribution_contract':'explicit_parameter_domains_v1','human_thinking_enabled':True,
            'human_generation_token_limit':4096,'source_sha256':hashes,'source_files_changed_during_run':changed}
        if output.is_dir():(output/'observation_adapter_provenance.json').write_text(json.dumps(adapter,ensure_ascii=False,indent=2))
        if (output/'provenance.json').is_file():
            provenance=json.loads((output/'provenance.json').read_text())
            provenance.update({k:v for k,v in adapter.items() if k not in {'source_sha256','source_files_changed_during_run'}})
            provenance['source_sha256'].update(hashes);provenance['source_files_changed_during_run'].extend(changed)
            (output/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
