import numpy as np

from hrc_pilot.contribution_human_executor import ContributionHumanExecutor
from test_human_owned_buffer import make_actor


def test_explicit_keep_intent_cancels_the_previous_placement_without_declaring_it_complete():
    actor,data=make_actor(True);actor.__class__=ContributionHumanExecutor
    actor.phase='transfer_raise';actor.active_request=2;actor.transfer_destination='drawer'
    actor.accept_choice({'action':'pick','object_id':'plate'},3)
    assert actor.phase=='idle' and actor.active_request==3 and actor.transfer_destination is None
    assert actor.held=='plate'
    assert actor.completed_requests==[3] and actor.receipts[-1]['effect']=='already_holding_requested_object'


def test_body_return_is_not_complete_just_because_the_hand_is_at_the_target():
    actor,_=make_actor(True);actor.__class__=ContributionHumanExecutor
    actor.phase='return';actor.active_request=4;actor.body_base=np.array([.25,.95]);actor.body_target=np.array([.25,.6])
    actor._complete()
    assert actor.phase=='return' and actor.completed_requests==[]
    actor.body_base=actor.body_target.copy();actor._complete()
    assert actor.completed_requests==[4]
