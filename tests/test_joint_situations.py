from hrc_pilot.joint_situations import SITUATIONS


def test_situation_sampling_is_reproducible_information_not_action_routing():
    assert set(SITUATIONS)=={'join','leave_return','change_use','detour','correction','robot_request'}
    for situation in SITUATIONS.values():
        sample=situation.sample(3)
        assert sample==situation.sample(3)
        assert all('action' not in cue and 'intent' not in cue and 'destination' not in cue for cue in sample['private_cues'])
    assert SITUATIONS['join'].sample(3)['initial_presence']=='aside'
    assert len(SITUATIONS['leave_return'].sample(3)['private_cues'])==2
