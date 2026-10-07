import csv
from pathlib import Path


def test_predefined_cross_activity_conditions_compare_systems_without_selecting_human_trajectories():
    table=Path(__file__).resolve().parents[1]/'experiments/coherent_joint_20261008/conditions.csv'
    rows=list(csv.DictReader(table.open()))
    assert len(rows)==12 and len({r['run'] for r in rows})==12
    assert len({r['activity'] for r in rows})==3 and len({r['situation'] for r in rows})==6
    for row in rows:
        group=[r for r in rows if r['situation']==row['situation']]
        assert len(group)==2 and {r['system'] for r in group}=={'visual','symbolic'}
        for key in ['activity','profile','initial_human_holding','init_state_id','seed','steps']:
            assert len({r[key] for r in group})==1
        assert all(r['role']=='development_partner_and_coverage_qualification' for r in group)
