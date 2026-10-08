"""下一版只读场景测量：载荷随人携带时不宣称离手，不选择贡献。"""
from .joint_world import observable_world


def observable_carried_world(record, regions, drawer=None):
    """保留v4可重建性，生成尚未接入当前批次的v5测量。"""
    world=observable_world(record,regions,drawer,measurement_version=4)
    objects=world['public_scene_measurements']['objects']
    carried={name for name,state in objects.items() if state['human_carried']}
    for name in carried:
        world['released_object_support_contacts'][name]=[]
    invalid_prefixes=tuple(f'{name} is released and has support contact with ' for name in carried)
    world['current_measured_fact_sentences']=[
        text for text in world['current_measured_fact_sentences']
        if not invalid_prefixes or not text.startswith(invalid_prefixes)]
    world['measurement_version']=5
    return world
