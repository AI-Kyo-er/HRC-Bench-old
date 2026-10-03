"""严格状态JSON，不修复/强转/重试；action评分原样复用v12。"""
import json

FIELDS=('outer_blue_destination','guidance_active','current_blue_destination')


def unique_object(pairs):
    if len({key for key,value in pairs})!=len(pairs):raise ValueError('duplicate_keys')
    return dict(pairs)


def forbidden_constant(value):raise ValueError('nonstandard_constant')


def parse_state(response):
    try:value=json.loads(response,object_pairs_hook=unique_object,parse_constant=forbidden_constant)
    except (ValueError,TypeError):return None,'invalid_json_or_duplicate_keys'
    if type(value) is not dict:return None,'object_required'
    if tuple(value)!=FIELDS:return None,'exact_schema_and_key_order_required'
    if type(value['guidance_active']) is not bool:return None,'boolean_type_required'
    for key,allowed in (('outer_blue_destination',('left','right')),('current_blue_destination',('left','right','neutral'))):
        if type(value[key]) is not str or value[key] not in allowed:return None,f'{key}_enum_required'
    return value,None


def score_state(value,error,truth):
    correct={key:error is None and value[key]==truth[key] for key in FIELDS}
    return dict(schema_valid=error is None,field_correct=correct,joint_state_correct=all(correct.values()),
        parse_error=error,physical_execution=False,physical_success=None,
        interpretation='独立state query显式任务报告，不是action的内在知识读出；格式错误按未合法作答计各字段错误。')
