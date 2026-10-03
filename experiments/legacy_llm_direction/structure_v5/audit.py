"""读取原始全tick接触，不把零力/正距离记录删掉；旧缺失距离不补造。"""
import gzip
import json


def contact_audit(path, robot, partner, objects):
    groups = {name: {'ticks': 0, 'records': 0, 'max_normal_force': 0, 'phases': {},
        'missing_distance_records': 0, 'negative_distance_records': 0,
        'near_zero_distance_records': 0, 'positive_distance_records': 0,
        'min_contact_distance': None, 'max_contact_distance': None}
        for name in ('robot_partner', 'object_partner')}
    total = 0
    all_contact_records = 0
    all_missing_distance_records = 0
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            state = json.loads(line)
            total += 1
            all_contact_records += len(state['contacts'])
            all_missing_distance_records += sum('contact_distance' not in c for c in state['contacts'])
            for name, bodies in [('robot_partner', {robot}), ('object_partner', set(objects))]:
                contacts = [c for c in state['contacts'] if
                    (c['body_a'] == partner and c['body_b'] in bodies) or
                    (c['body_b'] == partner and c['body_a'] in bodies)]
                group = groups[name]
                if contacts:
                    group['ticks'] += 1
                    group['phases'][state['phase']] = group['phases'].get(state['phase'], 0) + 1
                for contact in contacts:
                    group['records'] += 1
                    group['max_normal_force'] = max(group['max_normal_force'], contact['normal_force'])
                    distance = contact.get('contact_distance')
                    if distance is None:
                        group['missing_distance_records'] += 1
                    else:
                        key = 'negative_distance_records' if distance < -1e-6 else ('positive_distance_records' if distance > 1e-6 else 'near_zero_distance_records')
                        group[key] += 1
                        group['min_contact_distance'] = distance if group['min_contact_distance'] is None else min(group['min_contact_distance'], distance)
                        group['max_contact_distance'] = distance if group['max_contact_distance'] is None else max(group['max_contact_distance'], distance)
    return {'total_ticks': total, 'all_contact_records': all_contact_records,
            'all_missing_distance_records': all_missing_distance_records, **groups,
            'zero_record_passed': all(g['records'] == 0 for g in groups.values())}
