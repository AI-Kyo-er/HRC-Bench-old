#!/usr/bin/env python3
"""独立人观测适配条件：明确记录实际语义输入及额外实现来源。"""
from hashlib import sha256
import json
from pathlib import Path
import sys

import run_joint_activity as runtime
from hrc_pilot.semantic_joint_human import SemanticJointHumanPolicy


if __name__=='__main__':
    sources=[Path(__file__),Path('src/hrc_pilot/semantic_joint_human.py'),Path('src/hrc_pilot/intent_observation.py')]
    hashes={str(p):sha256(p.read_bytes()).hexdigest() for p in sources}
    runtime.JointHumanPolicy=SemanticJointHumanPolicy
    output=Path(sys.argv[sys.argv.index('--output-dir')+1])
    try:runtime.main()
    finally:
        changed=[str(p) for p in sources if sha256(p.read_bytes()).hexdigest()!=hashes[str(p)]]
        adapter={'human_observation_encoding':'intent_semantic_facts_v1','source_sha256':hashes,
                 'source_files_changed_during_run':changed,'auxiliary_kind_fallback':'notice_with_original_value_logged'}
        if output.is_dir():(output/'observation_adapter_provenance.json').write_text(json.dumps(adapter,ensure_ascii=False,indent=2))
        if (output/'provenance.json').is_file():
            provenance=json.loads((output/'provenance.json').read_text())
            provenance['human_observation_encoding']=adapter['human_observation_encoding']
            provenance['source_sha256'].update(hashes)
            provenance['source_files_changed_during_run'].extend(changed)
            (output/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
