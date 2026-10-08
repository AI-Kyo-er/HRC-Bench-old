"""独立重建候选接口的源状态、实际token及调用参数，不认证策略语义。"""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path

from jsonschema import validate
from transformers import AutoTokenizer
from hrc_pilot.carried_world_observation import observable_carried_world
from hrc_pilot.constrained_human_decision import parse_constrained_decision
from hrc_pilot.private_agenda_human import parse_agenda


def rows(path):return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def verify(root,table):
    conditions=list(csv.DictReader(table.read_text().splitlines()));results=[];tokenizer=None
    if list(root.glob('*.failure.json')):raise ValueError('存在失败记录，不认证完整接口批')
    for condition in conditions:
        source=Path('results/continuous_v2')/condition['source_run'];original=rows(source/'episode/human_policy_io.jsonl')
        old=next(d for d in original if d['time_s']==float(condition['time_s']))
        stem=condition['source_run']+'_decision_'+str(old['decision_id']).zfill(3)
        path=root/(stem+'.json');record=json.loads(path.read_text());decision=record['candidate_decision']
        assert record['condition']==condition and record['original_choice_for_review_only']==old['choice']
        assert record['condition_table_sha256']==sha256(table.read_bytes()).hexdigest()
        assert not record['source_files_changed_during_call'] and not record['new_sim_executed']
        for name,digest in {**record['source_sha256'],**record['implementation_sha256']}.items():
            assert sha256(Path(name).read_bytes()).hexdigest()==digest
        assert record['model_download_receipt_sha256']==sha256((Path(record['model'])/'download_receipt.json').read_bytes()).hexdigest()
        trace=rows(source/'episode/trace.jsonl');scene=decision['observation_source_scene']
        expected=observable_carried_world(trace[round(decision['time_s']*20)],scene['regions_xyz'],scene['measured_world']['drawer'])
        assert scene['measured_world']==expected and decision['time_s']==old['time_s']
        if tokenizer is None:tokenizer=AutoTokenizer.from_pretrained(record['model'],local_files_only=True)
        assert decision['chat_template_sha256']==sha256(tokenizer.chat_template.encode()).hexdigest()
        agenda=decision['private_agenda_inference'];assert agenda['parse_error'] is None
        assert agenda['decoder']=='lm-format-enforcer-0.11.3'
        assert tokenizer.apply_chat_template(agenda['model_input']['messages'],tokenize=True,
            add_generation_prompt=True,enable_thinking=False)==agenda['input_token_ids']
        assert tokenizer.decode(agenda['generated_token_ids'],skip_special_tokens=True).strip()==agenda['raw_output']
        assert parse_agenda(agenda['raw_output'])==agenda['agenda_after']
        payload=decision['native_tool_model_input']
        encoded=tokenizer.apply_chat_template(payload['messages'],tools=payload['tools'],tokenize=True,
            add_generation_prompt=True,enable_thinking=True)+tokenizer.encode(decision['caller_input_prefix'],add_special_tokens=False)
        assert encoded==decision['native_tool_input_token_ids'] and decision['parse_error'] is None
        whole=decision['whole_generated_token_ids'];close=tokenizer.encode('</think>',add_special_tokens=False)[0]
        index=whole.index(close);prefix=tokenizer.encode(decision['caller_prefix'],add_special_tokens=False)
        assert whole[:index]==decision['reasoning_token_ids'] and whole[index+1:index+1+len(prefix)]==prefix
        assert whole[index+1+len(prefix):]==decision['actual_generated_token_ids']
        assert tokenizer.decode(whole,skip_special_tokens=False)==decision['actual_raw_generated_text']
        assert tokenizer.decode(decision['actual_generated_token_ids'],skip_special_tokens=True).strip()==decision['actual_generated_json']
        validate(json.loads(decision['actual_generated_json']),decision['output_json_schema'])
        choice,normalization,call=parse_constrained_decision(decision['raw_output'],scene)
        assert (choice,normalization,call)==(decision['choice'],decision['contribution_normalization'],decision['selected_tool_call'])
        assert decision['neural_inferences']==2
        results.append({'stem':stem,'record_sha256':sha256(path.read_bytes()).hexdigest(),'actual_neural_inferences':2})
    return {'status':'source_and_token_records_verified','decisions':results,'new_sim_executed':False,
        'semantic_validity':'requires_review_not_certified_by_token_checks','formal_samples':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-dir',type=Path,required=True)
    p.add_argument('--conditions',type=Path,required=True);args=p.parse_args()
    result=verify(args.input_dir,args.conditions)
    (args.input_dir/'interface_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'status':result['status'],'decisions':len(result['decisions'])},ensure_ascii=False))
