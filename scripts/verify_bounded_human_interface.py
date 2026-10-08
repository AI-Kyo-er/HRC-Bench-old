#!/usr/bin/env python3
"""独立核对有限文本接口的来源、实际输入、token与工具解析。"""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from hrc_pilot.bounded_human_protocol import bounded_output_schema
from hrc_pilot.constrained_human_decision import PREFIX,constrained_tool,decision_json_schema,parse_constrained_decision
from hrc_pilot.reasoning_constrained_human import THINK_PREFIX,reasoning_request


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True)
    parser.add_argument('--source-dir',type=Path,required=True)
    args=parser.parse_args()
    provenance=json.loads((args.input_dir/'provenance.json').read_text())
    result=json.loads((args.input_dir/'result.json').read_text())
    if (args.input_dir/'failure.json').exists():raise ValueError('接口生成已记录运行失败')
    lines=[line for line in (args.source_dir/'episode/human_policy_io.jsonl').read_text().splitlines() if line.strip()]
    line=lines[provenance['source_nonempty_row']]
    assert sha256(line.encode()).hexdigest()==provenance['source_record_sha256']
    assert args.source_dir.name==provenance['input_run']
    source=json.loads(line);scene=source['observation_source_scene']
    expected=deepcopy(source['native_tool_model_input'])
    request=reasoning_request(scene,json.loads(expected['messages'][-1]['content']))
    expected['messages'][-1]['content']=json.dumps(request,ensure_ascii=False,separators=(',',':'))
    tool=constrained_tool(scene);tool['function']['parameters']=bounded_output_schema(tool['function']['parameters'])
    expected['tools']=[tool]
    assert result['model_input']==expected
    assert result['output_json_schema']==bounded_output_schema(decision_json_schema(scene))
    for path,digest in provenance['source_sha256'].items():assert sha256(Path(path).read_bytes()).hexdigest()==digest
    from transformers import AutoTokenizer
    from jsonschema import validate,ValidationError
    tokenizer=AutoTokenizer.from_pretrained(provenance['model'],local_files_only=True,trust_remote_code=True)
    assert sha256(tokenizer.chat_template.encode()).hexdigest()==source['chat_template_sha256']
    encoded=tokenizer.apply_chat_template(expected['messages'],tools=expected['tools'],
        tokenize=True,add_generation_prompt=True,enable_thinking=True)
    encoded+=tokenizer.encode(THINK_PREFIX,add_special_tokens=False)
    assert encoded==result['input_token_ids']
    assert tokenizer.decode(result['actual_generated_token_ids'],skip_special_tokens=True).strip()==result['actual_generated_json']
    whole=result['whole_generated_token_ids'];close=tokenizer.encode('</think>',add_special_tokens=False)
    assert len(close)==1
    index=whole.index(close[0]);prefix=tokenizer.encode(PREFIX,add_special_tokens=False)
    assert whole[:index]==result['reasoning_token_ids']
    assert whole[index+1:index+1+len(prefix)]==prefix
    assert whole[index+1+len(prefix):]==result['actual_generated_token_ids']
    assert tokenizer.decode(whole,skip_special_tokens=False)==result['actual_raw_generated_text']
    assert result['raw_output']==PREFIX+result['actual_generated_json']+'\n</tool_call>'
    if result['parse_error'] is None:
        validate(json.loads(result['actual_generated_json']),result['output_json_schema'])
        choice,normalization,call=parse_constrained_decision(result['raw_output'],scene)
        assert choice==result['choice'] and normalization==result['contribution_normalization']
        assert call==result['selected_tool_call']
    else:
        try:
            validate(json.loads(result['actual_generated_json']),result['output_json_schema'])
            parse_constrained_decision(result['raw_output'],scene)
        except (ValueError,TypeError,KeyError,ValidationError) as error:assert str(error)==result['parse_error']
        else:raise AssertionError('接口失败标签不符合实际输出')
        assert result['choice'] is None and result['selected_tool_call'] is None
    verification={'status':'source_and_actual_token_records_verified',
        'parse_error':result['parse_error'],'neural_inferences':1,'sim_action_execution':False,
        'formal_samples':0,'semantic_validity':'requires_review_not_certified',
        'provenance_sha256':sha256((args.input_dir/'provenance.json').read_bytes()).hexdigest(),
        'result_sha256':sha256((args.input_dir/'result.json').read_bytes()).hexdigest(),
        'verifier_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
    (args.input_dir/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2))
    print(json.dumps(verification,ensure_ascii=False))
