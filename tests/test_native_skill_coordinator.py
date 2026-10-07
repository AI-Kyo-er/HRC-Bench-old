import pytest
from hrc_pilot.native_skill_coordinator import native_operation,encode_selected_operation


def test_native_skill_encoder_preserves_neural_hold_and_rejects_extra_motion_tool():
    operation=native_operation('put the cream cheese in the bowl\nShared activity: prepare together')
    held,error,record=encode_selected_operation('{"mode":"hold","message":"Please provide the bowl."}',operation)
    assert held['mode']=='hold' and error is None and record['model_selected_operation'] is None
    chosen,error,record=encode_selected_operation('{"mode":"execute","instruction":"put cream cheese in bowl"}',operation)
    assert chosen['instruction']==operation and record['generated_instruction']=='put cream cheese in bowl'
    rejected,error,_=encode_selected_operation('{"mode":"move_ee","delta_xyz_m":[0,0,0.1]}',operation)
    assert error=='unsupported_direct_motion' and rejected['mode']=='hold'
    with pytest.raises(ValueError):native_operation('implicit human task only')
