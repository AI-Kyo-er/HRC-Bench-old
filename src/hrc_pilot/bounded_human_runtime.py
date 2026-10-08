"""有限文本与真实失败反馈的运行适配；不路由贡献或约定。"""
from contextlib import contextmanager
from copy import deepcopy
import json

from .bounded_human_protocol import TEXT_LIMITS,bounded_output_schema,failed_turn_history_content
from .human_output_verification import INVALID_TOOL_FALLBACK


PROTOCOL='bounded_text_and_failure_feedback_v1'
HISTORY_ENCODING='actual_generation_status_v1'


def protocol_enabled(provenance):
    protocol=provenance.get('human_output_protocol')
    history=provenance.get('human_failed_history_encoding')
    if protocol is None and history is None:return False
    if protocol!=PROTOCOL or history!=HISTORY_ENCODING or provenance.get('human_text_limits')!=TEXT_LIMITS:
        raise ValueError('未知或不完整的人输出／失败反馈协议')
    return True


def failure_aware_tool_payload(payload,history):
    result=deepcopy(payload);recent=history[-4:]
    assistant=[m for m in result['messages'] if m['role']=='assistant']
    if len(assistant)!=len(recent):raise ValueError('历史助手消息须与实际决定逐条对应')
    for row,message in zip(recent,assistant):
        if row.get('parse_error') is None:continue
        if message.get('content')!=row['raw_output'] or message.get('tool_calls'):
            raise ValueError('失败历史与原始模型输出不对应')
        message['content']=failed_turn_history_content(row)
    return result


def failure_aware_agenda_request(request,history):
    result=deepcopy(request);recent=history[-4:]
    records=result['recent_choices_and_actual_feedback']
    if len(records)!=len(recent):raise ValueError('意图层历史与已记录决定不对应')
    for record,row in zip(records,recent):
        if record['decision_id']!=row['decision_id']:raise ValueError('历史决定标识不对应')
        record['contribution_generation_status']=(
            'valid_tool_call' if row.get('parse_error') is None else 'invalid_generation_backend_wait')
        record['contribution_parse_error']=row.get('parse_error')
        record['contribution_status_scope']='实际生成状态；回退动作不代表人的自主策略，不选择下一贡献。'
    return result


@contextmanager
def bounded_runtime_overrides():
    import hrc_pilot.reasoning_constrained_human as reasoning
    import hrc_pilot.tool_joint_human as tools
    import hrc_pilot.private_agenda_human as agenda
    originals=(reasoning.constrained_tool,reasoning.decision_json_schema,tools.tool_model_input,
        agenda.agenda_request,reasoning.ReasoningConstrainedHumanPolicy.decide)
    def bounded_tool(scene):
        value=deepcopy(originals[0](scene))
        value['function']['parameters']=bounded_output_schema(value['function']['parameters'])
        return value
    def payload(system,request,history,scene):
        return failure_aware_tool_payload(originals[2](system,request,history,scene),history)
    def agenda_request(scene,activity,profile,previous,history):
        return failure_aware_agenda_request(originals[3](scene,activity,profile,previous,history),history)
    def decide(policy,scene):
        row=originals[4](policy,scene)
        if row['parse_error'] is None:
            from jsonschema import validate,ValidationError
            try:validate(row['selected_tool_call'],row['output_json_schema'])
            except ValidationError as error:
                row.update(parse_error=str(error),choice=deepcopy(INVALID_TOOL_FALLBACK),
                    selected_tool_call=None,contribution_normalization=None)
        return row
    reasoning.constrained_tool=bounded_tool
    reasoning.decision_json_schema=lambda scene:bounded_output_schema(originals[1](scene))
    tools.tool_model_input=payload;agenda.agenda_request=agenda_request
    reasoning.ReasoningConstrainedHumanPolicy.decide=decide
    try:yield
    finally:
        (reasoning.constrained_tool,reasoning.decision_json_schema,tools.tool_model_input,
            agenda.agenda_request,reasoning.ReasoningConstrainedHumanPolicy.decide)=originals
