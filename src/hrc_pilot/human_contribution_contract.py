"""人贡献接口的参数语义与空辅助字段处理；不选择下一贡献或推断私人目标。"""
from copy import deepcopy
import json

from .joint_human_policy import MESSAGE_KINDS,parse_choice


def contribution_interface(scene):
    regions=scene['regions_xyz'];objects=scene['objects_xyz']
    destinations=[]
    for name in regions:
        if name.endswith('_personal'):
            meaning='Declared human-side table location for this item; can be used as an owned-item buffer.'
        elif name.endswith('_home'):
            meaning='Initial measured location marker; not a promise of placement on or inside its namesake object.'
        elif name=='drink_staging':meaning='Table position at which the human can release a bottle for partner access.'
        elif name=='serving_ready':meaning='Declared table position for releasing a serving container.'
        elif name=='snack_delivery':meaning='Declared receiving or delivery table position.'
        elif name=='drawer_storage':meaning='Measured drawer-interior placement location; current accessibility is separately observed.'
        else:meaning='Declared workspace location marker.'
        destinations.append({'destination_id':name,'meaning':meaning})
    return {'actor':'human','one_current_contribution':True,'object_ids':list(objects),
        'destination_choices':destinations,
        'actions':{
            'pick':'Approach and hold object_id. Does not ask the robot to pick it.',
            'place':'Move the currently held item to destination_id and release it.',
            'relocate':'Pick object_id, move it to destination_id, release and retreat.',
            'message':'Publish the selected text to the partner; does not mean the motion is complete.',
            'wait':'Keep the current motion or holding; does not automatically perform a future plan.',
            'away':'Move away from the work edge.', 'return':'Return to the work edge.',
            'point':'Point to object_id without moving it.', 'move_hand':'Move hand to an explicit permitted XYZ target.',
        },
        'empty_optional_message':'null or omitted means no public utterance, not an invalid policy action.',
        'boundary':'Object identifiers and destination identifiers are distinct. No automatic mapping from an unsupported fixture target to a different location.',
        'auto_buffer_owned_item':bool(scene['action_interface'].get('relocate_can_buffer_owned_object'))}


def parse_contribution(raw,objects,regions):
    text=raw.rsplit('</think>',1)[-1].strip()
    original=json.loads(text[text.index('{'):text.rindex('}')+1]);value=deepcopy(original)
    normalized=[]
    for field in ['message','memory']:
        if value.get(field) is None:
            value[field]='';normalized.append(field)
    kind=value.get('message_kind','notice')
    if not isinstance(kind,str) or kind not in MESSAGE_KINDS:
        value['declared_message_kind']=kind;value['message_kind']='notice';normalized.append('message_kind')
    choice=parse_choice(json.dumps(value,ensure_ascii=False),objects,regions,schema_version=2)
    return choice,{'normalized_auxiliary_fields':normalized,
        'interpretation':'Only absent speech/memory and logging tags are normalized; action, object and destination remain the actual neural selection.'}
