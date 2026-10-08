#!/usr/bin/env python3
"""固定人贡献检查关系执行和真实VLA退让，绝非正式动态人或协调成绩。"""
from hashlib import sha256
import json
from pathlib import Path
import sys

import run_joint_activity as runtime
from hrc_pilot.human_relation_targets import update_human_relation_targets
from hrc_pilot.human_support_targets import update_human_support_targets
from hrc_pilot.relation_human_executor import RelationHumanExecutor


class RelationCheckReference:
    def __init__(self,activity):
        self.activity=activity;self.decisions=[];self.pending=None;self.stage='fill'

    def decide(self,scene,unused_robot_goal):
        done=scene['own_execution']['completed_requests']
        if self.pending is not None and self.pending in done:
            self.stage={'fill':'serve','serve':'done'}[self.stage];self.pending=None
        choice={'action':'wait','message':'','message_kind':'notice','intention':'fixed_relation_execution_check',
                'participation':'reference','reason':'固定资格检查，不代表动态人策略。','memory':''}
        if self.stage!='done' and self.pending is None:
            obj,dest={'fill':('cream_cheese_1','cream_cheese_1__in__akita_black_bowl_1'),
                      'serve':('akita_black_bowl_1','akita_black_bowl_1__on__plate_1')}[self.stage]
            choice.update(action='relocate',object_id=obj,destination=dest,
                          message=f'Execution check: placing {obj} at {dest}.')
            self.pending=len(self.decisions)
        row={'decision_id':len(self.decisions),'time_s':scene['time_s'],'private_input':{'scene':scene},
             'choice':choice,'raw_output':'','parse_error':None,'action_source':'fixed_relation_execution_reference',
             'neural_inferences':0,'reference_stage':self.stage}
        self.decisions.append(row);return row

    @property
    def robot_permission(self):return True


def main():
    sources=[Path(__file__),Path('src/hrc_pilot/human_relation_targets.py'),Path('src/hrc_pilot/relation_human_executor.py'),
             Path('src/hrc_pilot/human_support_targets.py'),Path('src/hrc_pilot/contribution_human_executor.py'),
             Path('src/hrc_pilot/settled_placement_human.py'),Path('src/hrc_pilot/pausable_human_executor.py')]
    hashes={str(p):sha256(p.read_bytes()).hexdigest() for p in sources}
    output=Path(sys.argv[sys.argv.index('--output-dir')+1])
    original_update=runtime.update_joint_regions
    def update(env,regions):
        value=original_update(env,regions);update_human_support_targets(env,regions)
        update_human_relation_targets(env,regions);return value
    runtime.update_joint_regions=update;runtime.KinematicHuman=RelationHumanExecutor
    runtime.JointReference=RelationCheckReference
    original_augment=runtime.augment_contact_human
    def augment(env,*args,**kwargs):
        update(env,kwargs['public_regions']);return original_augment(env,*args,**kwargs)
    runtime.augment_contact_human=augment
    try:runtime.main()
    finally:
        if (output/'provenance.json').exists():
            p=json.loads((output/'provenance.json').read_text())
            p.update(role='fixed_execution_qualification_not_dynamic_collaboration',
                     human_relation_targets='measured_reference_collision_surface_v1',
                     human_request_state='actor_and_active_motion_v2')
            p['source_sha256'].update(hashes)
            p['source_files_changed_during_run'].extend(str(q) for q in sources if sha256(q.read_bytes()).hexdigest()!=hashes[str(q)])
            (output/'provenance.json').write_text(json.dumps(p,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
