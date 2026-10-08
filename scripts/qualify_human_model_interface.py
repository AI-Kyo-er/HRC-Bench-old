"""在保存物理状态上检查真实两阶段人接口；不执行新Sim或宣称协作成绩。"""
import argparse
from copy import deepcopy
import csv
from hashlib import sha256
import json
from pathlib import Path

from hrc_pilot.carried_world_observation import observable_carried_world
from hrc_pilot.contribution_observations import contribution_observations
from hrc_pilot.private_agenda_human import PrivateAgendaHumanPolicy
from hrc_pilot.workspace_contracts import WORKSPACE_CONTRACTS


def rows(path):return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--conditions',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists():raise ValueError('禁止覆盖资格记录')
    table=args.conditions.read_bytes();conditions=list(csv.DictReader(table.decode().splitlines()))
    implementations=[Path(__file__),*[Path('src/hrc_pilot')/name for name in
        ['llm_human.py','private_agenda_human.py','reasoning_constrained_human.py',
         'constrained_human_decision.py','human_decision_interface.py','tool_joint_human.py',
         'human_decision_policy.py','joint_human_policy.py','human_contribution_contract.py',
         'structured_tool_joint_human.py','libero_native.py',
         'carried_world_observation.py','joint_world.py','public_scene_measurements.py',
         'scene_relation_summary.py','intent_observation.py','contribution_observations.py',
         'workspace_contracts.py','thinking_schema_filter.py']]]
    implementation_sha={str(p):sha256(p.read_bytes()).hexdigest() for p in implementations}
    model_receipt_sha=sha256((args.model/'download_receipt.json').read_bytes()).hexdigest()
    args.output_dir.mkdir(parents=True)
    import torch
    shared_model=shared_tokenizer=None
    summaries=[]
    for condition in conditions:
        if args.conditions.read_bytes()!=table:raise ValueError('运行中条件表变化')
        root=Path('results/continuous_v2')/condition['source_run']
        for name in ['interaction_verification.json','independent_video_verification.json']:
            if json.loads((root/name).read_text())['status']!='verified':raise ValueError('来源未完整核验')
        provenance=json.loads((root/'provenance.json').read_text())
        path=root/'episode/human_policy_io.jsonl';original=rows(path)
        index=next(i for i,d in enumerate(original) if d['time_s']==float(condition['time_s']))
        trace_path=root/'episode/trace.jsonl';trace=rows(trace_path)
        def upgrade(row):
            scene=deepcopy(row['observation_source_scene'])
            scene['measured_world']=observable_carried_world(trace[round(row['time_s']*20)],
                                                          scene['regions_xyz'],scene['measured_world']['drawer'])
            return scene
        history=deepcopy(original[:index])
        for old in history:old['observation_source_scene']=upgrade(old)
        scene=upgrade(original[index])
        scene['self_contribution_observations']={str(old['decision_id']):contribution_observations(old,scene)
                                                for old in history[-4:]}
        human=PrivateAgendaHumanPolicy(WORKSPACE_CONTRACTS[provenance['activity']].activity,
            model_path=args.model,profile=provenance['profile'],seed=int(condition['test_seed']))
        if shared_model is None:
            human.prepare();shared_model=human._model;shared_tokenizer=human._tokenizer
            precision=human.inference_precision
        else:
            human._model=shared_model;human._tokenizer=shared_tokenizer;human.inference_precision=precision
        human.decisions=history
        human.private_agenda=deepcopy(history[-1]['private_agenda_inference']['agenda_after']) if history else None
        torch.manual_seed(int(condition['test_seed']))
        stem=condition['source_run']+'_decision_'+str(original[index]['decision_id']).zfill(3)
        try:result=human.decide(scene)
        except Exception as error:
            with (args.output_dir/(stem+'.failure.json')).open('x') as stream:
                json.dump({'error':repr(error),'condition':condition,'scene':scene,
                    'actual_agenda_inferences':human.agenda_inferences,
                    'native_input_token_ids':getattr(human,'_current_token_ids',None),
                    'raw_generated_text':getattr(human,'_raw_generated_text',None)},
                    stream,ensure_ascii=False,indent=2)
            raise
        record={'role':'saved_state_counterfactual_interface_not_closed_loop_or_formal_score',
            'condition':condition,'condition_table_sha256':sha256(table).hexdigest(),
            'source_sha256':{str(p):sha256(p.read_bytes()).hexdigest() for p in [path,trace_path]},
            'model':str(args.model),'inference_precision':precision,
            'model_download_receipt_sha256':model_receipt_sha,
            'implementation_sha256':implementation_sha,
            'source_files_changed_during_call':[str(p) for p in implementations
                if sha256(p.read_bytes()).hexdigest()!=implementation_sha[str(p)]],
            'history_origin':'saved_Qwen3_14B_choices_and_beliefs_not_candidate_own_rollout',
            'world_measurement_version':5,'original_choice_for_review_only':original[index]['choice'],
            'candidate_decision':result,'formal_benchmark_score':None,'new_sim_executed':False}
        with (args.output_dir/(stem+'.json')).open('x') as stream:json.dump(record,stream,ensure_ascii=False,indent=2)
        if record['source_files_changed_during_call']:raise ValueError('运行中实现发生变化，保留记录但拒绝认证')
        summary={'stem':stem,'source_time_s':result['time_s'],'parse_error':result['parse_error'],
            'agenda_parse_error':result['private_agenda_inference']['parse_error'],
            'choice':result['choice'],'latency_s':result['latency_s'],'reasoning_close_forced':result['reasoning_close_forced']}
        summaries.append(summary);print(json.dumps(summary,ensure_ascii=False),flush=True)
        del human
    (args.output_dir/'summary.json').write_text(json.dumps({'role':'interface_qualification_not_policy_effect',
        'decisions':summaries,'formal_samples':0,'new_sim_executed':False},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
