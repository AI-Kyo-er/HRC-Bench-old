"""下一版家具面空位反馈的独立入口；不热改当前两个系统。"""
from hashlib import sha256
import json
from pathlib import Path
import runpy
import sys

from hrc_pilot.fixture_area_human_executor import (
    CONTRACT, FixtureAreaHumanExecutor, fixture_executor_override)


if __name__ == '__main__':
    if '--workspace-method' not in sys.argv or '--human-area-placement' not in sys.argv:
        raise ValueError('家具面接口需要明确工作区与区域执行方法')
    output = Path(sys.argv[sys.argv.index('--output-dir') + 1])
    sources = [Path(__file__), Path('src/hrc_pilot/fixture_area_human_executor.py'),
               Path('src/hrc_pilot/fixture_surface_placement.py'), Path('src/hrc_pilot/human_support_targets.py')]
    hashes = {str(p): sha256(p.read_bytes()).hexdigest() for p in sources}
    reference = '--human-source' in sys.argv and sys.argv[sys.argv.index('--human-source') + 1] == 'reference'
    entry = 'scripts/run_joint_activity.py' if reference else 'scripts/run_bounded_joint_activity.py'
    try:
        with fixture_executor_override():
            runpy.run_path(entry, run_name='__main__')
    finally:
        layout = output / 'workspace_layout.json'
        if layout.exists() and FixtureAreaHumanExecutor.registered_areas is not None:
            value = json.loads(layout.read_text())
            value['placement_areas'] = FixtureAreaHumanExecutor.registered_areas
            value['fixture_surface_contract'] = CONTRACT
            layout.write_text(json.dumps(value, ensure_ascii=False, indent=2))
        for name in ['provenance.json', 'observation_adapter_provenance.json']:
            path = output / name
            if not path.exists():
                continue
            value = json.loads(path.read_text())
            value['human_fixture_surface_contract'] = CONTRACT
            value['human_support_targets'] = 'actual_collision_geometry_cabinet_top_v1'
            value['fixture_surface_scope'] = '只兑现模型已选家具表面并返回实际拒绝；不读取评分或选择替代策略。'
            value['source_sha256'].update(hashes)
            value['source_files_changed_during_run'].extend(str(p) for p in sources if sha256(p.read_bytes()).hexdigest() != hashes[str(p)])
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2))
