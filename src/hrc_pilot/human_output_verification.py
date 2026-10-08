"""核对有效调用或已记录的真实生成失败；失败回退不是模型策略。"""
import json

from jsonschema import validate

from .constrained_human_decision import PREFIX,parse_constrained_decision


INVALID_TOOL_FALLBACK={'action':'wait','message':'','message_kind':'notice',
    'intention':'','participation':'','reason':'工具调用非法，保留现场等待下一次人决策。','memory':''}


def verify_recorded_constrained_output(row,scene):
    if row['caller_prefix']!=PREFIX or row['caller_suffix']!='\n</tool_call>':
        raise ValueError('调用封装与已声明的贡献接口不同')
    if row['raw_output']!=row['caller_prefix']+row['actual_generated_json']+row['caller_suffix']:
        raise ValueError('原始输出与实际生成JSON不一致')
    if row['parse_error'] is None:
        validate(json.loads(row['actual_generated_json']),row['output_json_schema'])
        return {'status':'valid_json_schema','recorded_generation_failure':False}
    try:
        parse_constrained_decision(row['raw_output'],scene)
    except (ValueError,TypeError,KeyError) as error:
        if str(error)!=row['parse_error']:raise ValueError('生成失败标签与重放解析错误不同')
    else:raise ValueError('输出可成功解析，不能伪标为生成失败')
    if row['choice']!=INVALID_TOOL_FALLBACK or row['selected_tool_call'] is not None:
        raise ValueError('无效工具调用必须保留实际无公开消息的回退，不得冒充自主策略')
    if row.get('contribution_normalization') is not None:
        raise ValueError('无效调用不能宣称已经归一化为有效贡献')
    return {'status':'recorded_generation_failure_verified','recorded_generation_failure':True,
            'parse_error':row['parse_error'],'policy_choice_valid':False}
