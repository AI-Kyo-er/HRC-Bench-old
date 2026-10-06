"""公开动作接口的拒绝反馈；不替模型选择任务或合法替代动作。"""


def command_feedback(request, accepted, objects, regions, *, valid_intents=None):
    intent=request.get('intent','observe')
    errors=[]
    valid_intents=valid_intents or ['push','observe','yield','away','return']
    if intent not in valid_intents:
        errors.append('unsupported_intent')
    if intent in {'push','grasp','place'}:
        if request.get('object_id') not in objects:errors.append('unknown_object_id')
        if intent in {'push','place'} and request.get('destination') not in regions:errors.append('unknown_destination_region')
    return {'source':'public_executor_command_validation','requested':{
                'intent':intent,'object_id':request.get('object_id'),'destination':request.get('destination')},
            'accepted':{'intent':accepted.intent,'object_id':accepted.object_id,'destination':accepted.destination},
            'status':'rejected' if errors else 'accepted','errors':errors,
            'valid_intents':list(valid_intents),
            'currently_visible_object_ids':list(objects),'currently_valid_destination_regions':list(regions),
            'interpretation':'拒绝只说明接口参数无效；未自动选择替代动作，也不证明任务完成。'}
