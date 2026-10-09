"""真实Sim执行层资格：固定提供／占位请求，Robot固定保持，不计模型协作。"""
from hashlib import sha256
import json
from pathlib import Path
import runpy
import sys


class CabinetOccupiedReference:
    def __init__(self, activity, **kwargs):
        self.activity=activity;self.stage='prepare';self.pending=None;self.decisions=[]

    @property
    def robot_permission(self):
        return False  # 此执行资格只有明确记录的reference_scheduler_hold，不调用π。

    def decide(self, scene, robot_contribution):
        feedback=scene['own_execution'];receipt=feedback.get('last_receipt')
        choice={'action':'wait','object_id':None,'destination':None,'message':'','message_kind':'notice',
                'intention':'fixed_executor_qualification','participation':'reference',
                'reason':'固定几何／连续执行资格；不是神经人或机器人协作成绩。','memory':''}
        if self.stage=='prepare' and self.pending is None:
            choice.update(action='relocate',object_id='wine_bottle_1',destination='wine_bottle_1_on_cabinet',
                          message='Fixed qualification: provide wine on the cabinet.')
            self.pending=len(self.decisions)
        elif self.stage=='prepare' and self.pending in feedback['completed_requests']:
            self.stage='occupied_request';self.pending=len(self.decisions)
            choice.update(action='relocate',object_id='plate_1',destination='plate_1_on_cabinet',
                          message='Fixed qualification: request plate placement on the same occupied surface.')
        elif self.stage=='occupied_request' and receipt and receipt['request_id']==self.pending and not receipt['accepted']:
            self.stage='rejected';choice['message']='Fixed qualification: refusal retained; no alternative goal selected.'
        row={'decision_id':len(self.decisions),'time_s':scene['time_s'],'private_input':{'scene':scene},
             'choice':choice,'raw_output':'','parse_error':None,'action_source':'fixed_feasibility_reference',
             'neural_inferences':0,'reference_stage':self.stage}
        self.decisions.append(row)
        return row


if __name__=='__main__':
    if '--human-source' not in sys.argv or sys.argv[sys.argv.index('--human-source')+1]!='reference':
        raise ValueError('固定执行资格必须明确reference，不作为神经策略')
    if '--activity' not in sys.argv or sys.argv[sys.argv.index('--activity')+1]!='drink_storage':
        raise ValueError('该资格使用已保留的饮品场景')
    import hrc_pilot.joint_reference as references
    original=references.JointReference;references.JointReference=CabinetOccupiedReference
    output=Path(sys.argv[sys.argv.index('--output-dir')+1]);source=Path(__file__)
    digest=sha256(source.read_bytes()).hexdigest()
    try:runpy.run_path('scripts/run_fixture_joint_activity.py',run_name='__main__')
    finally:
        references.JointReference=original
        path=output/'provenance.json'
        if path.exists():
            value=json.loads(path.read_text())
            value['reference_qualification']='fixed_cabinet_provision_and_occupied_plate_request_v1'
            value['source_sha256'][str(source)]=digest
            if sha256(source.read_bytes()).hexdigest()!=digest:value['source_files_changed_during_run'].append(str(source))
            path.write_text(json.dumps(value,ensure_ascii=False,indent=2))
