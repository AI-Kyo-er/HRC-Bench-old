from copy import deepcopy

from hrc_pilot.activity_private_context import ACTIVITY_CUES,specialize_private_context
from hrc_pilot.joint_situations import SITUATIONS


def test_activity_facts_preserve_sampling_and_do_not_overwrite_policy_decisions():
    for activity in ACTIVITY_CUES:
        for situation in SITUATIONS.values():
            source=situation.sample(62);original=deepcopy(source)
            result=specialize_private_context(source,activity)
            assert source==original
            assert result['initial_presence']==source['initial_presence']
            assert [c['time_s'] for c in result['private_cues']]==[c['time_s'] for c in source['private_cues']]
            assert all(c['source']=='external_private_information_not_action_command' for c in result['private_cues'])
            assert not {'action','destination','intent','policy','score'}.intersection(result)
    snack=specialize_private_context(SITUATIONS['change_use'].sample(62),'snack_service')
    drink=specialize_private_context(SITUATIONS['change_use'].sample(62),'drink_storage')
    assert 'akita_black_bowl_1' in snack['private_cues'][0]['text'] and 'plate_1' in snack['private_cues'][0]['text']
    assert 'wine_bottle_1' in drink['private_cues'][0]['text']
    assert snack['private_cues'][0]['text']!=drink['private_cues'][0]['text']
