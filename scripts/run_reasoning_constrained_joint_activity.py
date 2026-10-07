#!/usr/bin/env python3
"""自然人贡献／交流接口，实际支持面和同一真实机器人运行时。"""
from hashlib import sha256
import json
from pathlib import Path
import sys

import run_joint_activity as runtime
from hrc_pilot.reasoning_constrained_human import ReasoningConstrainedHumanPolicy
from hrc_pilot.pausable_human_executor import PausableHumanExecutor
from hrc_pilot.human_support_targets import update_human_support_targets


if __name__=='__main__':
    import lmformatenforcer,interegular
    sources=[Path(__file__),*[Path('src/hrc_pilot')/name for name in
        ['reasoning_constrained_human.py','thinking_schema_filter.py','constrained_human_decision.py','pausable_human_executor.py','human_decision_policy.py','human_decision_interface.py','human_support_targets.py',
         'contribution_human_executor.py','settled_placement_human.py','tool_joint_human.py',
         'reasoning_joint_human.py','contribution_joint_human.py','human_contribution_contract.py',
         'semantic_joint_human.py','intent_observation.py']]]
    for package in (lmformatenforcer,interegular):sources.extend(sorted(Path(package.__file__).parent.rglob('*.py')))
    hashes={str(p):sha256(p.read_bytes()).hexdigest() for p in sources}
    output=Path(sys.argv[sys.argv.index('--output-dir')+1])
    original_update=runtime.update_joint_regions
    def update_regions(env,regions):
        result=original_update(env,regions)
        update_human_support_targets(env,regions)
        return result
    runtime.JointHumanPolicy=ReasoningConstrainedHumanPolicy
    runtime.KinematicHuman=PausableHumanExecutor
    runtime.update_joint_regions=update_regions
    original_augment=runtime.augment_contact_human
    def augment(env,*args,**kwargs):
        update_human_support_targets(env,kwargs['public_regions'])
        return original_augment(env,*args,**kwargs)
    runtime.augment_contact_human=augment
    try:runtime.main()
    finally:
        changed=[str(p) for p in sources if sha256(p.read_bytes()).hexdigest()!=hashes[str(p)]]
        adapter={'human_observation_encoding':'intent_semantic_agent_dialogue_v3',
            'human_policy_interface':'reasoning_then_schema_constrained_decision_v1',
            'human_contribution_schema_version':10,'human_thinking_enabled':True,'human_generation_token_limit':4096,
            'human_reasoning_token_limit':1536,
            'human_decoder':'lm-format-enforcer-0.11.3', 'human_caller_frame':'explicit_tool_envelope_v1',
            'human_support_targets':'actual_collision_geometry_cabinet_top_v1',
            'human_placement_contract':'atomic_place_object_v1','source_sha256':hashes,'source_files_changed_during_run':changed}
        if output.is_dir():(output/'observation_adapter_provenance.json').write_text(json.dumps(adapter,ensure_ascii=False,indent=2))
        if (output/'provenance.json').is_file():
            provenance=json.loads((output/'provenance.json').read_text())
            provenance.update({k:v for k,v in adapter.items() if k not in {'source_sha256','source_files_changed_during_run'}})
            provenance['source_sha256'].update(hashes);provenance['source_files_changed_during_run'].extend(changed)
            (output/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
