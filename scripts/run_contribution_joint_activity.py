#!/usr/bin/env python3
"""显式人贡献参数域条件，实际模型输入与适配器来源一起保存。"""
from hashlib import sha256
import json
from pathlib import Path
import sys

import run_joint_activity as runtime
from hrc_pilot.contribution_joint_human import ContributionJointHumanPolicy


if __name__=='__main__':
    sources=[Path(__file__),*[Path('src/hrc_pilot')/name for name in
        ['contribution_joint_human.py','human_contribution_contract.py','semantic_joint_human.py','intent_observation.py']]]
    hashes={str(p):sha256(p.read_bytes()).hexdigest() for p in sources}
    output=Path(sys.argv[sys.argv.index('--output-dir')+1])
    runtime.JointHumanPolicy=ContributionJointHumanPolicy
    try:runtime.main()
    finally:
        changed=[str(p) for p in sources if sha256(p.read_bytes()).hexdigest()!=hashes[str(p)]]
        adapter={'human_observation_encoding':'intent_semantic_facts_v1',
            'human_contribution_contract':'explicit_parameter_domains_v1','source_sha256':hashes,
            'source_files_changed_during_run':changed}
        if output.is_dir():(output/'observation_adapter_provenance.json').write_text(json.dumps(adapter,ensure_ascii=False,indent=2))
        if (output/'provenance.json').is_file():
            provenance=json.loads((output/'provenance.json').read_text())
            provenance.update(human_observation_encoding=adapter['human_observation_encoding'],
                              human_contribution_contract=adapter['human_contribution_contract'])
            provenance['source_sha256'].update(hashes);provenance['source_files_changed_during_run'].extend(changed)
            (output/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
