#!/usr/bin/env python3
"""统一活动使命、实际能力域、关系事实及持续私人的共同活动入口。"""
from hashlib import sha256
import json
from pathlib import Path
import sys

import run_joint_activity as runtime
import run_private_agenda_joint_activity as agenda_runtime
import hrc_pilot.relation_human_executor as relation_runtime
from hrc_pilot.contract_human_executor import ContractHumanExecutor


def main():
    required=['--interaction-contract','--human-complete-observation','--human-relational-targets','--robot-skill-bank']
    if any(flag not in sys.argv for flag in required):raise ValueError('统一契约要求显式使命、完整观测、关系目标和操作库')
    sources=[Path(__file__),Path('src/hrc_pilot/contract_human_executor.py'),
             Path('src/hrc_pilot/scene_relation_summary.py')]
    hashes={str(p):sha256(p.read_bytes()).hexdigest() for p in sources}
    output=Path(sys.argv[sys.argv.index('--output-dir')+1])
    original=runtime.observable_world
    def observable(record,regions,drawer=None,**kwargs):
        return original(record,regions,drawer,measurement_version=4)
    runtime.observable_world=observable
    relation_runtime.RelationHumanExecutor=ContractHumanExecutor
    try:agenda_runtime.main()
    finally:
        adapter_path=output/'observation_adapter_provenance.json'
        if adapter_path.exists():
            adapter=json.loads(adapter_path.read_text())
            adapter.update(world_measurement_version=4,
                           human_perception_contract='public_semantic_relations_and_geometry_v1',
                           human_actuation_domain='actual_movable_objects_and_bounded_pickup_v1')
            adapter['source_sha256'].update(hashes)
            adapter['source_files_changed_during_run'].extend(str(q) for q in sources if sha256(q.read_bytes()).hexdigest()!=hashes[str(q)])
            adapter_path.write_text(json.dumps(adapter,ensure_ascii=False,indent=2))
        if (output/'provenance.json').exists():
            p=json.loads((output/'provenance.json').read_text())
            p.update(activity_contract='joint_mission_and_information_asymmetry_v1',
                     human_actuation_domain='actual_movable_objects_and_bounded_pickup_v1',
                     world_measurement_version=4,
                     human_perception_contract='public_semantic_relations_and_geometry_v1',
                     native_goal_scope='original_manipulation_probe_not_whole_activity_score')
            p['source_sha256'].update(hashes)
            p['source_files_changed_during_run'].extend(str(q) for q in sources if sha256(q.read_bytes()).hexdigest()!=hashes[str(q)])
            (output/'provenance.json').write_text(json.dumps(p,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
