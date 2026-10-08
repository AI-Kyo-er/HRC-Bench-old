"""下一版人输出的有限文本协议；不改变动作选择或修复已有失败。"""
from copy import deepcopy
import json


TEXT_LIMITS={'intention':256,'participation':128,'reason':512,'memory':256,'text':512}


def bounded_output_schema(schema):
    """仅限制自由字符串；工具名、动作、对象及目标枚举保持原样。"""
    result=deepcopy(schema)
    def visit(node,field=None):
        if isinstance(node,list):
            for child in node:visit(child,field)
        elif isinstance(node,dict):
            kinds=node.get('type',[]);kinds=[kinds] if isinstance(kinds,str) else kinds
            if 'string' in kinds and 'enum' not in node and 'const' not in node:
                limit=TEXT_LIMITS.get(field,512)
                node['maxLength']=min(node.get('maxLength',limit),limit)
            for key,value in node.items():
                if key=='properties':
                    for name,child in value.items():visit(child,name)
                elif key in {'anyOf','oneOf','allOf','items'}:visit(value,field)
    visit(result)
    return result


def failed_turn_history_content(row):
    """返回实际生成失败和回退事实；原始重复文本继续保留在研究记录。"""
    if not row.get('parse_error') or row.get('selected_tool_call') is not None:
        raise ValueError('只处理没有有效工具调用的已记录生成失败')
    choice=row['choice']
    if choice['action']!='wait' or choice.get('message'):
        raise ValueError('实际回退不是无公开消息的wait，不能替它编造历史')
    return json.dumps({'decision_id':row['decision_id'],'time_s':row['time_s'],
        'tool_generation_status':'invalid','parse_error':row['parse_error'],
        'recorded_backend_fallback':'wait','public_message_sent':False,
        'scope':'没有有效的新工具调用；wait延续原运动，不代表人自主决定继续或暂停。'
                '失败原文保留供研究审阅，不作为已发出的公开纠正。'},ensure_ascii=False)
