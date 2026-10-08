"""把自己选择的贡献与随后真实测量相连；不评分共同任务或选择下一动作。"""
from copy import deepcopy
import math


def contribution_observations(decision, scene):
    choice = decision['choice']
    obj = choice.get('object_id')
    execution = scene['own_execution']
    measured = scene['measured_world'].get('public_scene_measurements', {})
    objects = measured.get('objects', {})
    result = {
        'decision_id': decision['decision_id'],
        'selected_at_s': decision['time_s'],
        'observed_at_s': scene['time_s'],
        'selected_action': choice['action'],
        'selected_object_id': obj,
        'selected_destination': choice.get('destination'),
        'completion_id_recorded': decision['decision_id'] in execution.get('completed_requests', []),
        'cancellation_id_recorded': decision['decision_id'] in execution.get('cancelled_requests', []),
        'object_measurement': deepcopy(objects.get(obj)),
        'scope': '自己已选贡献的当前事实；请求ID缺失不等于失败，完成ID不等于共同任务成功。不读取评分、未来事件或选择下一策略。',
    }
    if scene['time_s'] < decision['time_s']:
        raise ValueError('不能用选择之前的观测作为随后结果')
    destination = choice.get('destination')
    relation = scene.get('relation_targets', {}).get(destination)
    if relation is not None:
        if relation['object_id'] != obj:
            raise ValueError('所选物品与关系目标不一致')
        reference = relation['reference_object_id']
        summary = scene['measured_world'].get('public_relation_summary', {}).get('reference_relations', {})
        support = summary.get(reference, {}).get('observed_supported_items')
        result['selected_reference_object_id'] = reference
        result['support_with_selected_reference_observed'] = (
            None if support is None else any(item['object_id'] == obj for item in support))
        result['relation_measurement_scope'] = '接触与位置的支撑摘要，不是完整容器包含或整体目标评分。'
    elif destination in scene['regions_xyz'] and obj in scene['objects_xyz']:
        result['xy_distance_to_selected_named_position_m'] = math.dist(
            scene['objects_xyz'][obj][:2], scene['regions_xyz'][destination][:2])
        result['named_position_measurement_scope'] = '命名坐标的水平距离，不单独表示已经放下或放好。'
    return result
