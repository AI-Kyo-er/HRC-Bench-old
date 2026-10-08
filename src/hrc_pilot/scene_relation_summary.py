"""将公开物体关系转为可读事实；不输出活动完成、可取用评分或下一动作。"""
from .human_relation_targets import RELATION_AFFORDANCES


def scene_relation_summary(measurement,affordances=RELATION_AFFORDANCES):
    summaries={};sentences=[]
    known=measurement['contact_measurement_available']
    for reference in affordances:
        if reference not in measurement['objects']:continue
        items=[]
        if known:
            for relation in measurement['relative_object_measurements'].values():
                if relation['reference_object_id']!=reference:continue
                above=relation['source_minus_reference_xyz_m'][2]>=0
                if relation['contact_observed'] and above and relation['xy_distance_m']<.03:
                    obj=relation['source_object_id'];state=measurement['objects'][obj]
                    items.append({'object_id':obj,'human_carried':state['human_carried'],
                                  'robot_gripper_contact':state['robot_gripper_contact'],
                                  'released_from_hands':state['released_from_hands']})
        summaries[reference]={'observed_supported_items':items if known else None,
            'reference_human_carried':measurement['objects'][reference]['human_carried'],
            'relation_scope':'中心相近、源在参考上方且有实际接触；不是完整容器包含或活动完成。'}
        if not known:sentences.append(f'Support relations for {reference} are unknown because contact observations are unavailable.')
        elif not items:sentences.append(f'No item currently has an observed support relation with {reference}.')
        else:
            for item in items:
                sentences.append(f'{item["object_id"]} currently has contact and centre alignment above {reference}; '
                    f'human-carried={item["human_carried"]}, robot-finger-contact={item["robot_gripper_contact"]}. '
                    'This is not a completion declaration.')
    return {'source':'public_contact_and_relative_position_summary',
            'reference_relations':summaries,'fact_sentences':sentences,
            'scope':'理想公共感知的语义摘要，不是任务判定、私人意图或正确下一贡献。'}
