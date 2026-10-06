from hrc_pilot.continuous import HumanCommand
from hrc_pilot.native_action_validation import command_feedback


def test_object_name_used_as_unavailable_region_returns_specific_rejection():
    feedback=command_feedback({'intent':'push','object_id':'bowl','destination':'plate'},HumanCommand('observe'),
                              {'plate':(0,0,0),'bowl':(1,0,0)}, {'near_human':(0,1,0)})
    assert feedback['status']=='rejected'
    assert feedback['errors']==['unknown_destination_region']
    assert feedback['accepted']['intent']=='observe'
    assert feedback['currently_valid_destination_regions']==['near_human']
    assert 'recommended_action' not in feedback


def test_valid_but_unhelpful_command_is_not_overridden_by_task_role():
    command=HumanCommand('push','bowl','near_human')
    feedback=command_feedback({'intent':'push','object_id':'bowl','destination':'near_human'},command,
                              {'plate':(0,0,0),'bowl':(1,0,0)},{'near_human':(0,1,0)})
    assert feedback['status']=='accepted' and not feedback['errors']
    assert feedback['accepted']['object_id']=='bowl'
