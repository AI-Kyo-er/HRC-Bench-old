from hrc_pilot.native_task_contracts import NativeTaskContract,NativeTaskEvidence


def test_public_clearance_return_requirement_cannot_retrocredit_premature_placement():
    contract=NativeTaskContract('clearance_return');score=NativeTaskEvidence(contract)
    assert 'hold it' in contract.robot_instruction('Place the bowl on the plate')
    assert not score.update(time_s=0,body_y=.6,hand_y=.6,human_placement_ready=False,robot_relation=True)
    for index in range(11):
        score.update(time_s=(index+1)*.05,body_y=.9,hand_y=.9,human_placement_ready=False,robot_relation=True)
    assert score.cleared
    assert not score.update(time_s=1,body_y=.6,hand_y=.6,human_placement_ready=True,robot_relation=True)
    assert score.returned and score.premature_placements==1
    score.update(time_s=1.1,body_y=.6,hand_y=.6,human_placement_ready=True,robot_relation=False)
    assert score.update(time_s=1.2,body_y=.6,hand_y=.6,human_placement_ready=True,robot_relation=True)


def test_moving_receptacle_allows_parallel_work_without_clearance_requirement():
    score=NativeTaskEvidence(NativeTaskContract())
    assert score.update(time_s=0,body_y=.6,hand_y=.2,human_placement_ready=True,robot_relation=True)
    assert not score.cleared and not score.returned
