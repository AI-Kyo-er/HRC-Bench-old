import json
import pytest

from hrc_pilot.robot_skill_bank import SKILLS,encode_skill_selection


def test_public_skill_selection_can_change_destination_and_does_not_force_original_skill():
    raw=json.dumps({'mode':'execute','skill_id':'bottle_on_cabinet','message':'Keeping it accessible.'})
    decision,error,record=encode_skill_selection(raw,SKILLS)
    assert error is None and decision['instruction']=='put the wine bottle on top of the cabinet'
    assert record['model_selected_skill_id']=='bottle_on_cabinet'
    held,error,record=encode_skill_selection('{"mode":"hold","message":"Do you want to keep the bottle?"}',SKILLS)
    assert held['mode']=='hold' and error is None and record['model_selected_skill_id'] is None
    for raw in ['{"mode":"execute","skill_id":"hidden_solution"}',
                '{"mode":"execute","instruction":"put wine on rack"}',
                '{"mode":"move_ee","delta_xyz_m":[0,0,0.1]}']:
        rejected,error,record=encode_skill_selection(raw,SKILLS)
        assert error and rejected['mode']=='hold' and record['model_selected_skill_id'] is None


def test_skills_match_installed_primary_task_definitions():
    # 用已检出的官方BDDL验证公开指令，不宣称这些指令在新初态必成功。
    import importlib.util
    spec=importlib.util.find_spec('libero.libero')
    if spec is None:pytest.skip('当前环境没有官方LIBERO任务定义')
    from libero.libero import benchmark
    suite=benchmark.get_benchmark_dict()['libero_goal']()
    public_languages={suite.get_task(i).language for i in range(suite.n_tasks)}
    assert set(SKILLS.values()).issubset(public_languages)
