"""固定36条件，不用配对manifest或根据运行结果增删条件。"""


def cases(stage):
    records = []
    if stage == 'N':
        for initial in ('left', 'right'):
            for reply in ('accepted', 'rejected'):
                for presence in ('stay', 'retain', 'withdraw'):
                    for policy in ('public_ledger_progress', 'conservative_wait'):
                        records.append(dict(
                            id=f'N_{initial}_{reply}_{presence}_{policy}_120',
                            family='N', initial_blue=initial, reply=reply,
                            presence=presence, policy=policy, seed=120))
    elif stage == 'H':
        for initial in ('left', 'right'):
            for reply in ('accepted', 'rejected'):
                records.append(dict(
                    id=f'H_{initial}_{reply}_120', family='H',
                    initial_blue=initial, reply=reply, presence='stay',
                    policy='public_ledger_role', seed=120))
    elif stage == 'C':
        names = (
            'early_request_no_queue', 'duplicate_check_no_restart',
            'move_out_restore', 'withdraw_requires_new_request',
            'initial_early_declaration', 'unfinished_check_declaration',
            'partner_role_wrong_pickup', 'robot_role_wrong_leave')
        for index, name in enumerate(names):
            records.append(dict(
                id=f'C{index}_{name}_120', family='C', control=index,
                initial_blue='left', reply='accepted' if index == 6 else 'rejected',
                presence='retain' if index == 2 else 'withdraw' if index == 3 else 'stay',
                policy='fixed_control', seed=120))
    else:
        raise ValueError('未知预设阶段。')
    return records
