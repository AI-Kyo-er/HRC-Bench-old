import importlib.util
from pathlib import Path
from types import SimpleNamespace


spec=importlib.util.spec_from_file_location('fixture_qualification',
    Path(__file__).parents[1]/'scripts/run_fixture_surface_qualification.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def observation(time, completed=(), receipt=None):
    return {'time_s':time,'own_execution':{'completed_requests':list(completed),'last_receipt':receipt}}


def test_accepted_second_placement_completes_export_contract_and_never_enables_vla():
    reference=module.CabinetOccupiedReference(SimpleNamespace(key='drink_storage'))
    assert reference.finish_targets['drink_storage']==('plate_1','plate_1_on_cabinet')
    assert reference.decide(observation(0),False)['choice']['object_id']=='wine_bottle_1'
    assert reference.decide(observation(16,[0]),False)['choice']['object_id']=='plate_1'
    reference.decide(observation(32,[0,1]),False)
    assert reference.stage=='done' and reference.robot_permission is False


def test_rejection_preserves_original_request_without_alternative_or_vla():
    reference=module.CabinetOccupiedReference(SimpleNamespace(key='drink_storage'))
    reference.decide(observation(0),False);reference.decide(observation(16,[0]),False)
    row=reference.decide(observation(20,[0],{'request_id':1,'accepted':False}),False)
    assert reference.stage=='rejected' and row['choice']['action']=='wait'
    assert row['choice']['object_id'] is None and reference.robot_permission is False
