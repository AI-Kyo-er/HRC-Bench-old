"""公共可观察场景的完整物体测量；不读取活动目标、私有需要或成功标签。"""
from itertools import permutations

import numpy as np

from .libero_native import perceived_object_contacts


def public_scene_measurements(record,movable_object_ids):
    positions={}
    for name,value in record['objects'].items():
        xyz=np.asarray(value,dtype=float)
        if xyz.shape!=(3,) or not np.isfinite(xyz).all():raise ValueError('物体位置须为有限三维测量')
        positions[name]=xyz
    movable=list(movable_object_ids)
    if len(set(movable))!=len(movable) or not set(movable).issubset(positions):
        raise ValueError('可移动物品标识须唯一且来自实际场景')
    execution=record['human_execution']
    owned=set(execution.get('carried_objects',[]))
    if execution.get('held_object'):owned.add(execution['held_object'])
    if not owned.issubset(positions):raise ValueError('实际持物记录引用了未知对象')
    contacts_available='contacts' in record
    contacts=perceived_object_contacts(record) if contacts_available else {}
    objects={}
    for name,xyz in positions.items():
        contact=contacts.get(name)
        robot_contact=contact['robot_hand_contact'] if contact else None
        objects[name]={'xyz_m':xyz.tolist(),'human_carried':name in owned,
            'robot_gripper_contact':robot_contact,
            'contact_entities':contact['contact_entities'] if contact else None,
            'released_from_hands':(name not in owned and not robot_contact) if contacts_available else None}
    relations={}
    for source,reference in permutations(movable,2):
        delta=positions[source]-positions[reference]
        relations[source+'__relative_to__'+reference]={
            'source_object_id':source,'reference_object_id':reference,
            'source_minus_reference_xyz_m':delta.tolist(),
            'xy_distance_m':float(np.linalg.norm(delta[:2])),
            'contact_observed':reference in contacts[source]['contact_entities'] if contacts_available else None}
    return {'source':'actual_simulated_public_geometry_and_contact_not_task_score',
        'contact_measurement_available':contacts_available,'objects':objects,'relative_object_measurements':relations,
        'scope':'理想公共场景测量，非视觉模型推断；接触、相对位置和离手不等于完整包含、准备好、分工或活动完成。'}
