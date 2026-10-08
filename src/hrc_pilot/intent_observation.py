"""给人意图策略的语义观测：真实测量与伙伴话语分开，不提供评分或下一步策略。"""
ERROR_FACTS={
    'destination_not_physically_accessible':'The requested destination is not physically accessible now.',
    'holding_a_different_object':'The last contribution was rejected because the single hand was holding another object.',
    'already_holding_an_object':'The last pick was rejected because the hand was already holding an object.',
    'no_held_object':'The last placement was rejected because no object was held.',
    'object_in_robot_gripper_contact':'The requested object currently has robot gripper contact; the human executor did not take it.',
    'no_public_buffer_for_owned_object':'There is no declared public buffer for the currently held object.',
}


def intent_observation(scene):
    execution=scene['own_execution'];world=scene['measured_world']
    receipt=execution.get('last_receipt') or {}
    error=receipt.get('error')
    result = {
        'time_s':scene['time_s'],
        'measured_current_facts':list(world.get('current_measured_fact_sentences',[])),
        'object_ids':list(scene['objects_xyz']),
        'named_destinations':list(scene['regions_xyz']),
        'own_execution':{
            'held_object':execution['held_object'],'phase':execution['phase'],
            'completed_request_ids':execution.get('completed_requests',[]),
            'current_request_id':execution.get('active_request_id'),
            'last_request_accepted':receipt.get('accepted'),
            'last_rejection_fact':ERROR_FACTS.get(error,error),
            'last_rejection_code':error,
        },
        'measured_support_contacts':world.get('released_object_support_contacts',{}),
        'near_named_regions':world.get('near_named_regions',{}),
        'drawer_measurement':world.get('drawer'),
        'robot_actual_movement':scene.get('robot_motion',{}),
        'public_partner_statements_not_execution_facts':scene['public_dialogue'],
        'private_context':scene['private_context'],
        'private_initial_situation':scene.get('private_initial_situation'),
        'action_interface':scene['action_interface'],
        'public_robot_operation_inputs':scene.get('public_robot_operation_inputs',{}),
        'interpretation':'Measurements and own execution are current facts; partner statements and generated memories may be wrong. No task score or prescribed next action.',
    }
    if execution.get('request_state_version')==2:
        result['own_execution'].update(
            actor='human',current_request_id=execution['active_motion_request_id'],
            last_motion_request_id=execution['last_motion_request_id'],
            last_received_request_id=execution['last_received_request_id'],
            motion_in_progress=execution['motion_in_progress'],
            cancelled_request_ids=execution.get('cancelled_requests',[]))
    return result
