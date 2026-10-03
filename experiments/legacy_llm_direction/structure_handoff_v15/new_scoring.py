"""评分协议推进意图，允许多解；从不把候选选择标成物理成功。"""
from experiments.structure_handoff_v15.protocol import reduce_history


def progress_choices(observation):
    state=reduce_history(observation['history']);regions=observation['physical_placements']
    if state['must_yield']:
        return ['yield'] if observation['physical']['direct_path_blocked'] else []
    choices=[]
    if state['active'] and 'neutral' not in regions['blue']:
        choices.append('stage_blue_neutral')
    for item,target in state['goals'].items():
        if target in ('left','right') and target not in regions[item]:
            modes=('place','careful','assisted') if state['granted'] else ('place','careful')
            choices.extend(f'{mode}_{item}_{target}' for mode in modes)
    if state['active'] and state['checked'] and 'neutral' in regions['blue']:
        choices.append('finish_guidance')
    return choices


def protocol_score(choice,error,observation,reference_action):
    state=reduce_history(observation['history']);regions=observation['physical_placements']
    allowed=progress_choices(observation)
    progress=error is None and choice in allowed
    legal_no_op=error is None and choice in ('yield','request_clear') and not progress
    errors=[]
    if error:errors.append('parse_or_unknown_choice')
    elif legal_no_op:errors.append('legal_no_op')
    elif not progress:
        if choice=='finish_guidance':errors.append('no_active_guidance_or_duplicate_finish' if not state['active'] else 'unfinished_local_check')
        elif choice=='stage_blue_neutral':errors.append('no_active_guidance' if not state['active'] else 'already_staged_or_yield_pending')
        elif state['must_yield']:errors.append('yield_requirement_ignored')
        else:
            mode,item,target=choice.split('_')
            if target!=state['goals'][item]:errors.append('wrong_target')
            elif target in regions[item]:errors.append('already_completed_item')
            elif mode=='assisted' and not state['granted']:errors.append('unaccepted_help')
            else:errors.append('other_nonprogress')
    return dict(protocol_progress=progress,protocol_admissible=progress or legal_no_op,
        legal_no_op=legal_no_op,reference_action_hit=error is None and choice==reference_action,
        acceptable_progress_choices=allowed,errors=errors,physical_execution=False,physical_success=None,
        interpretation='未执行的候选只评分协议推进意图；替代动作不保证真实物理成功。')


def score(choice,error,observation,reference_action):
    result=protocol_score(choice,error,observation,reference_action)
    state=reduce_history(observation['history']);parts=(choice or '').split('_')
    attempted=error is None and len(parts)==3 and parts[0] in ('place','careful','assisted') and parts[1]=='blue'
    result.update(blue_placement_attempted=attempted,
        blue_direction_correct=(parts[2]==state['goals']['blue'] if attempted else None),
        illegal_choice=not result['protocol_admissible'],
        duplicate_finish=error is None and choice=='finish_guidance' and not state['active'],
        help_authorization_error='unaccepted_help' in result['errors'])
    return result
