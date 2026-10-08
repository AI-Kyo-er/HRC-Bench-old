#!/usr/bin/env python3
"""明确需要、分离功能区与观测触发的动态人共同活动入口。"""
from hashlib import sha256
import json
from pathlib import Path
import sys

import run_contract_joint_activity


if __name__=='__main__':
    if '--workspace-method' not in sys.argv:raise ValueError('新任务方法要求显式--workspace-method')
    output=Path(sys.argv[sys.argv.index('--output-dir')+1]);source=Path(__file__)
    digest=sha256(source.read_bytes()).hexdigest()
    try:run_contract_joint_activity.main()
    finally:
        if (output/'provenance.json').exists():
            p=json.loads((output/'provenance.json').read_text())
            p['source_sha256'][str(source)]=digest
            if sha256(source.read_bytes()).hexdigest()!=digest:p['source_files_changed_during_run'].append(str(source))
            p['workspace_method_scope']='explicit_needs_separated_surfaces_and_observation_driven_neural_choices_v1'
            (output/'provenance.json').write_text(json.dumps(p,ensure_ascii=False,indent=2))
