from copy import deepcopy

import pytest

from hrc_pilot.contribution_observations import contribution_observations


def scene():
    return {
        'time_s': 4., 'objects_xyz': {'food': [0., 0., 1.]},
        'regions_xyz': {'delivery': [0., 0., .9]},
        'own_execution': {'completed_requests': [], 'cancelled_requests': []},
        'relation_targets': {'food__in__bowl': {
            'object_id': 'food', 'reference_object_id': 'bowl'}},
        'measured_world': {
            'public_scene_measurements': {'objects': {'food': {
                'human_carried': True, 'released_from_hands': False}}},
            'public_relation_summary': {'reference_relations': {
                'bowl': {'observed_supported_items': []}}}},
    }


def decision(destination):
    return {'decision_id': 0, 'time_s': 0., 'choice': {
        'action': 'relocate', 'object_id': 'food', 'destination': destination}}


def test_near_destination_does_not_claim_release_or_task_completion():
    source = scene(); before = deepcopy(source)
    result = contribution_observations(decision('delivery'), source)
    assert result['xy_distance_to_selected_named_position_m'] == 0.
    assert result['object_measurement']['released_from_hands'] is False
    assert 'task_success' not in result
    assert source == before


def test_request_completion_and_current_support_are_independent():
    source = scene(); source['own_execution']['completed_requests'] = [0]
    result = contribution_observations(decision('food__in__bowl'), source)
    assert result['completion_id_recorded'] is True
    assert result['support_with_selected_reference_observed'] is False
    source['own_execution']['cancelled_requests'] = [0]
    assert contribution_observations(decision('delivery'), source)['cancellation_id_recorded'] is True


def test_missing_contact_evidence_stays_unknown_and_future_is_rejected():
    source = scene(); source['measured_world']['public_relation_summary'] = {}
    assert contribution_observations(decision('food__in__bowl'), source)['support_with_selected_reference_observed'] is None
    source['time_s'] = -1.
    with pytest.raises(ValueError):contribution_observations(decision('delivery'), source)
