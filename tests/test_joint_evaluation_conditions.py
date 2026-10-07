import importlib.util
from pathlib import Path


def test_candidate_matrix_covers_the_original_scope_without_replaying_identical_human_actions():
    path=Path(__file__).resolve().parents[1]/'scripts/prepare_joint_evaluation.py'
    spec=importlib.util.spec_from_file_location('joint_evaluation',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rows=module.condition_rows()
    assert len(rows)==72 and len({r['sample_id'] for r in rows})==72
    assert len({r['activity'] for r in rows})==3 and len({r['situation'] for r in rows})==6
    assert {r['init_state_id'] for r in rows}=={4,5}
    for r in rows:
        group=[s for s in rows if all(s[k]==r[k] for k in ['activity','situation','init_state_id'])]
        assert len(group)==2 and len({s['seed'] for s in group})==1 and len({s['profile'] for s in group})==1
        assert all(s['protocol_status']=='candidate_not_frozen' for s in group)
