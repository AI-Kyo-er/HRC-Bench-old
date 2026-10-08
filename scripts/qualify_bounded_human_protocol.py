#!/usr/bin/env python3
"""离线重放已失败前缀，检验下一版长度语法；不运行NN或修复旧输出。"""
import argparse
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path

from lmformatenforcer import JsonSchemaParser

from hrc_pilot.bounded_human_protocol import bounded_output_schema,failed_turn_history_content


def replay(schema,output):
    parser=JsonSchemaParser(schema)
    for index,char in enumerate(output):
        allowed=parser.get_allowed_characters()
        if char not in allowed:
            return {'accepted_prefix_characters':index,'first_disallowed_character':char,
                'allowed_characters_at_boundary':allowed,'can_end':parser.can_end()}
        parser=parser.add_character(char)
    return {'accepted_prefix_characters':len(output),'first_disallowed_character':None,
            'can_end':parser.can_end()}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True)
    parser.add_argument('--time-s',type=float,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    source=args.input_dir/'episode/human_policy_io.jsonl'
    lines=[line for line in source.read_text().splitlines() if line.strip()]
    index=next(i for i,line in enumerate(lines) if json.loads(line)['time_s']==args.time_s)
    line=lines[index];row=json.loads(line);schema=row['output_json_schema']
    if not row.get('parse_error'):raise ValueError('本核查只重放失败记录')
    bounded=bounded_output_schema(schema)
    result={'status':'offline_schema_prefix_check_not_neural_qualification',
        'run':args.input_dir.name,'source_file':'episode/human_policy_io.jsonl',
        'nonempty_record_index':index,'record_text_sha256':sha256(line.encode()).hexdigest(),
        'original_parse_error':row['parse_error'],
        'actual_whole_generated_token_count':len(row['whole_generated_token_ids']),
        'original_prefix':replay(schema,row['actual_generated_json']),
        'bounded_prefix':replay(bounded,row['actual_generated_json']),
        'bounded_schema':bounded,'failed_turn_history_content':failed_turn_history_content(row),
        'lmformatenforcer_version':importlib.metadata.version('lm-format-enforcer'),
        'analysis_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'protocol_sha256':sha256(Path('src/hrc_pilot/bounded_human_protocol.py').read_bytes()).hexdigest(),
        'scope':'仅证明同一重复前缀在有限文本语法下不再允许继续；未生成新有效工具调用，'
                '未改变旧决定/公开交流/执行，也未认证下一版伙伴或动作效果。'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:result[k] for k in ['status','original_parse_error',
        'actual_whole_generated_token_count','original_prefix','bounded_prefix']},ensure_ascii=False))
