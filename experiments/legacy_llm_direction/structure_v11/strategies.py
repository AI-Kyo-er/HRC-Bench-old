"""仅公开history的离线首次返回策略，不执行错误动作或声称整段失败。"""


def first_outer(history):
    return next(e['goals']['blue'] for e in history if e['kind']=='accepted_outer')


def last_proposal(history):
    return next(e['destination'] for e in reversed(history) if e['kind']=='update_proposed')


def outer_ledger(history,restore_snapshot=False):
    target=snapshot=None;pending={}
    for event in history:
        kind=event['kind']
        if kind=='accepted_outer':target=event['goals']['blue']
        elif kind=='update_proposed':pending[event['proposal_id']]=event['destination']
        elif kind=='proposal_reply':
            destination=pending.pop(event['proposal_id'])
            if event['decision']=='accept':target=destination
        elif kind=='accepted_child':snapshot=target
        elif kind=='outer_resumed' and restore_snapshot:target=snapshot
    return target


STRATEGIES={'first_outer':first_outer,'last_proposal':last_proposal,
    'snapshot_restore':lambda h:outer_ledger(h,True),'last_accepted_outer':outer_ledger}
