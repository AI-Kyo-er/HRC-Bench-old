import pytest
from hrc_pilot.human_contribution_contract import contribution_interface,parse_contribution


def test_absent_speech_does_not_discard_the_selected_action_or_change_its_target():
    raw='{"action":"relocate","object_id":"wine","destination":"staging","message":null,"message_kind":null,"memory":null}'
    choice,receipt=parse_contribution(raw,{'wine':[0,0,1]},{'staging':[0,0,1]})
    assert choice['action']=='relocate' and choice['destination']=='staging' and choice['message']==''
    assert set(receipt['normalized_auxiliary_fields'])=={'message','memory','message_kind'}
    with pytest.raises(ValueError,match='区域不存在'):
        parse_contribution(raw.replace('staging','rack'),{'wine':[]},{'staging':[]})
    with pytest.raises(ValueError,match='非法人动作'):
        parse_contribution('{"action":"finish_for_robot","message":null}',{}, {})


def test_interface_does_not_invent_fixture_support_or_a_next_action():
    scene={'objects_xyz':{'wine':[],'rack':[]},'regions_xyz':{'wine_personal':[],'rack_home':[],'drink_staging':[]},
           'action_interface':{'relocate_can_buffer_owned_object':True}}
    interface=contribution_interface(scene)
    by_id={r['destination_id']:r['meaning'] for r in interface['destination_choices']}
    assert 'not a promise' in by_id['rack_home']
    assert 'release a bottle' in by_id['drink_staging']
    assert 'rack' not in by_id and 'next_action' not in interface


def test_return_with_selected_relocation_is_executable_but_old_contract_and_departure_remain_distinct():
    raw='{"presence_choice":"return_to_work","action":"relocate","object_id":"cream","destination":"drawer"}'
    with pytest.raises(ValueError,match='冲突'):
        parse_contribution(raw,{'cream':[]},{'drawer':[]})
    choice,_=parse_contribution(raw,{'cream':[]},{'drawer':[]},schema_version=5)
    assert choice['action']=='relocate' and choice['object_id']=='cream' and choice['destination']=='drawer'
    with pytest.raises(ValueError,match='冲突'):
        parse_contribution(raw.replace('return_to_work','step_aside'),{'cream':[]},{'drawer':[]},schema_version=5)
    with pytest.raises(ValueError,match='物品不存在'):
        parse_contribution(raw,{}, {'drawer':[]},schema_version=5)
