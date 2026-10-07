import importlib.util
import json
from pathlib import Path


def test_receiver_manipulation_and_other_object_are_described_without_error_score(tmp_path):
    spec=importlib.util.spec_from_file_location('scope_audit',Path(__file__).resolve().parents[1]/'scripts/audit_human_goal_action_scope.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rows=[{'time_s':i*2,'personal_goal_state':{'personal_targets':[{'object_id':'cream','destination':'on:bowl'}]},
        'parsed_decision':{'intent':intent,'object_id':obj,'reason':'自主选择'}}
        for i,(intent,obj) in enumerate([('grasp','bowl'),('grasp','wine'),('observe',None)])]
    (tmp_path/'human_policy_io.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    result=module.audit(tmp_path)
    assert result['decision_counts']=={'current_personal_goal_receiver':1,'other_visible_object':1,'no_object_manipulation_selected':1}
    assert 'success' not in result and 'error_count' not in result
