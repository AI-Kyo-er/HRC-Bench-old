"""本地真实模型连续决策轨迹；无外部模型服务。"""
import argparse
import hashlib
import json
import time
from collections import defaultdict
from pathlib import Path
from experiments.language.backend import LocalModel
from experiments.language.environment import Episode, parse_action, SYSTEM

MODEL_ID = 'Qwen/Qwen2.5-3B-Instruct'
REVISION = 'aa8e72537993ba99e69dfaafa59ed015b17504d1'


def evaluate(case, view, model, trace_file):
    episode = Episode(case)
    steps, calls, errors = [], 0, 0
    for step in range(3):
        episode.start_step(step)
        completed = False
        for attempt in range(2):
            messages = episode.messages(view)
            prediction = model.predict(messages)
            action, parse_error = parse_action(prediction['response'])
            allowed = episode.allowed_actions()
            if parse_error:
                errors += 1
                episode.parse_errors += 1
                terminal = True
            else:
                completed, terminal = episode.act(action)
            record = {'case_id':case['id'], 'view':view, 'step':step, 'attempt':attempt,
                      'messages':messages, **prediction, 'parsed_action':action,
                      'parse_error':parse_error, 'reference_allowed_actions':allowed,
                      'step_completed':completed, 'events_after':episode.events.copy()}
            trace_file.write(json.dumps(record,ensure_ascii=False,sort_keys=True)+'\n')
            trace_file.flush()
            calls += 1
            if terminal:
                break
        steps.append(completed)
    return {'case_id':case['id'],'domain':case['domain'],'structure':case['structure'],
            'variant':case['variant'],'view':view,'episode_completed':all(steps),
            'completed_steps':sum(steps),'steps':steps,'calls':calls,'requests':episode.requests,
            'invalid_actions':episode.invalid,'parse_errors':errors,
            'final_public_events':episode.events}


def run(args):
    args.output_dir.mkdir(parents=True,exist_ok=True)
    case_path = Path(f'experiments/language/cases/{args.split}.jsonl')
    cases = [json.loads(line) for line in case_path.read_text().splitlines()]
    receipt = {'split':args.split,'case_sha256':hashlib.sha256(case_path.read_bytes()).hexdigest(),
        'system_prompt_sha256':hashlib.sha256(SYSTEM.encode()).hexdigest(),
        'model_id':MODEL_ID,'revision':REVISION,'start_unix_time':time.time(),
        'oracle_summary_intervention':True,'structural_holdout':'nested_reentry'}
    (args.output_dir/'protocol.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    model = LocalModel(args.model_path)
    rows = []
    with (args.output_dir/'calls.jsonl').open('w') as trace, (args.output_dir/'episodes.jsonl').open('w') as episodes:
        for case in cases:
            for view in ('full_history','oracle_summary'):
                row = evaluate(case,view,model,trace)
                rows.append(row)
                episodes.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n')
                episodes.flush()
                print(case['id'],view,f"steps={row['completed_steps']}/3",f"errors={row['parse_errors']}",flush=True)
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row['structure'],row['view'])].append(row)
    summary = {'instances':len(cases),'model':model.metadata(),'protocol':receipt,
               'aggregates':{f'{k[0]}/{k[1]}':{
                    'episodes':len(v),'episode_completed':sum(x['episode_completed'] for x in v),
                    'completed_steps':sum(x['completed_steps'] for x in v),'total_steps':3*len(v),
                    'calls':sum(x['calls'] for x in v),'requests':sum(x['requests'] for x in v),
                    'invalid_actions':sum(x['invalid_actions'] for x in v),
                    'parse_errors':sum(x['parse_errors'] for x in v)} for k,v in grouped.items()}}
    (args.output_dir/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output_dir.glob('*.json*')}
    (args.output_dir/'checksums.json').write_text(json.dumps(hashes,indent=2)+'\n')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--split',choices=('dev','formal'),required=True)
    parser.add_argument('--model-path',default='models/Qwen2.5-3B-Instruct')
    parser.add_argument('--output-dir',type=Path,required=True)
    run(parser.parse_args())
