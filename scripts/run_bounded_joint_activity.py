#!/usr/bin/env python3
"""独立运行有限文本／失败反馈的持续活动；原运行入口保持原协议。"""
from hashlib import sha256
import json
from pathlib import Path
import runpy
import sys

from hrc_pilot.bounded_human_protocol import TEXT_LIMITS
from hrc_pilot.bounded_human_runtime import PROTOCOL,HISTORY_ENCODING,bounded_runtime_overrides


if __name__=='__main__':
    if '--workspace-method' not in sys.argv or '--human-carried-observation' not in sys.argv:
        raise ValueError('新协议要求明确工作区与v5真实载荷观测')
    if '--human-source' in sys.argv and sys.argv[sys.argv.index('--human-source')+1]!='neural':
        raise ValueError('新协议仅用于生成式人，不改变固定参考')
    output=Path(sys.argv[sys.argv.index('--output-dir')+1])
    sources=[Path(__file__),Path('src/hrc_pilot/bounded_human_protocol.py'),
        Path('src/hrc_pilot/bounded_human_runtime.py')]
    hashes={str(p):sha256(p.read_bytes()).hexdigest() for p in sources}
    try:
        with bounded_runtime_overrides():runpy.run_path('scripts/run_workspace_joint_activity.py',run_name='__main__')
    finally:
        for name in ['observation_adapter_provenance.json','provenance.json']:
            path=output/name
            if not path.exists():continue
            value=json.loads(path.read_text())
            value.update(human_output_protocol=PROTOCOL,human_failed_history_encoding=HISTORY_ENCODING,
                human_text_limits=TEXT_LIMITS,
                bounded_human_scope='自由文本语法及实际生成失败反馈；意图／贡献仍由真实模型选择，非任务状态路由。')
            value['source_sha256'].update(hashes)
            value['source_files_changed_during_run'].extend(str(p) for p in sources if sha256(p.read_bytes()).hexdigest()!=hashes[str(p)])
            path.write_text(json.dumps(value,ensure_ascii=False,indent=2))
