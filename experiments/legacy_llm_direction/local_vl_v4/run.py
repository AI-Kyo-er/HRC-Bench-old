"""独立VL纯文本40输入基础参照，禁止改变既有提示/候选/集合评分。"""
import argparse
import copy
import datetime
import json
from pathlib import Path

from experiments.model_scale_v4.run import classify, gpu_preflight, SOURCES as OLD_SOURCES
from experiments.physical.protocol import parse
from experiments.physical.run import ROOT, sha, save

RESULT = ROOT / 'results/local_vl_v4'
FREEZE = ROOT / 'experiments/local_vl_v4/cases/freeze.json'
OLD_FREEZE = ROOT / 'experiments/model_scale_v4/cases/freeze.json'
MODEL_ID = 'Qwen/Qwen2.5-VL-7B-Instruct'
SOURCES = list(dict.fromkeys(OLD_SOURCES + ['experiments/model_scale_v4/run.py',
    'experiments/local_vl_v4/backend.py', 'experiments/local_vl_v4/run.py']))


def source_hashes():
    return {name: sha(ROOT / name) for name in SOURCES}


def frozen_records():
    return copy.deepcopy(json.loads(OLD_FREEZE.read_text())['records'])


def prepare(model_path):
    if FREEZE.exists():
        raise RuntimeError('VL已冻结，禁止覆盖。')
    from transformers import AutoTokenizer, Qwen2_5_VLForConditionalGeneration
    directory = model_path.resolve()
    config = json.loads((directory / 'config.json').read_text())
    index = json.loads((directory / 'model.safetensors.index.json').read_text())
    weights = sorted(set(index['weight_map'].values()))
    if config['model_type'] != 'qwen2_5_vl' or len(weights) != 5:
        raise RuntimeError('本地VL配置或分片数量不符。')
    files = weights + ['config.json', 'generation_config.json', 'model.safetensors.index.json',
        'tokenizer_config.json', 'tokenizer.json', 'vocab.json', 'merges.txt', 'chat_template.json',
        'preprocessor_config.json', 'configuration.json', '.mv', '.msc']
    hashes = {}
    for name in files:
        hashes[name] = {'bytes': (directory / name).stat().st_size, 'sha256': sha(directory / name)}
        print('本地只读SHA完成', name, hashes[name]['sha256'], flush=True)
    # .mv仅有master和创建时间，无不可变HF snapshot/commit来源证据；不编造revision。
    receipt = {'model_id': MODEL_ID, 'revision': None, 'revision_status': 'unknown',
        'path': str(directory), 'source': '既有用户本地缓存；.mv标记Revision:master，不能据此恢复HF固定commit',
        'local_mv_text': (directory / '.mv').read_text(), 'files': hashes,
        'official_hf_hash_match_verified': False, 'read_only_original_cache': True,
        'total_weights_bytes': sum(hashes[name]['bytes'] for name in weights),
        'model_config': config, 'prepared_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    records = frozen_records()
    tokenizer = AutoTokenizer.from_pretrained(directory, local_files_only=True)
    token_lengths = []
    for record in records:
        inputs = tokenizer.apply_chat_template(record['messages'], tokenize=True,
            add_generation_prompt=True, return_tensors='pt', return_dict=True)
        if set(inputs) != {'input_ids', 'attention_mask'}:
            raise RuntimeError('出现非纯文本输入。')
        token_lengths.append(int(inputs['input_ids'].shape[1]))
    receipt['api_check'] = {'class': Qwen2_5_VLForConditionalGeneration.__name__,
        'records': len(records), 'max_input_tokens': max(token_lengths),
        'input_keys': ['input_ids', 'attention_mask']}
    save(RESULT / 'local_weights_receipt.json', receipt)
    old = json.loads(OLD_FREEZE.read_text())
    save(FREEZE, {'version': 'local-vl-text-v4.0', 'records': records,
        'model_spec': {'model_id': MODEL_ID, 'revision': None,
                       'total_weights_bytes': receipt['total_weights_bytes']},
        'source_sha256': source_hashes(), 'original_freeze_sha256': sha(OLD_FREEZE),
        'weights_receipt_sha256': sha(RESULT / 'local_weights_receipt.json'),
        'original_calls_sha256': old['original_calls_sha256'],
        'generation': old['generation'], 'gate': old['gate'],
        'interpretation': '不同架构/训练VL的独立纯文本基线，不是模型规模单因素因果；没有图像，不评估视觉能力。固定16/16单动作和12/12全历史工程门槛；未知权重revision以全SHA识别。'})
    print('VL40输入冻结', sha(FREEZE), flush=True)


def summarize(rows, metadata, preflight, frozen):
    groups = {}
    for view in ('single', 'full_history', 'public_progress_aid'):
        subset = [r for r in rows if r['record']['view'] == view]
        errors = {}
        for row in subset:
            for error in row['errors']:
                errors[error] = errors.get(error, 0) + 1
        groups[view] = {'acceptable': sum(r['acceptable'] for r in subset), 'total': len(subset),
            'reference_3b_acceptable': sum(r['record']['reference_3b_acceptable'] for r in subset),
            'parse_errors': sum(r['parse_error'] is not None for r in subset), 'errors': errors}
    return {'groups': groups, 'gate_passed': groups['single']['acceptable'] == 16 and
        groups['full_history']['acceptable'] == 12, 'model': metadata, 'gpu_preflight': preflight,
        'generation_hit_limit': sum(r['prediction']['generation_hit_limit'] for r in rows),
        'freeze_sha256': sha(FREEZE), 'source_sha256': source_hashes(),
        'weights_receipt_sha256': frozen['weights_receipt_sha256'],
        'interpretation': frozen['interpretation']}


def evaluate(output, model_path):
    from .backend import LocalTextVL
    frozen = json.loads(FREEZE.read_text())
    receipt = json.loads((RESULT / 'local_weights_receipt.json').read_text())
    if source_hashes() != frozen['source_sha256'] or sha(OLD_FREEZE) != frozen['original_freeze_sha256']:
        raise RuntimeError('代码/原冻结变化。')
    if sha(RESULT / 'local_weights_receipt.json') != frozen['weights_receipt_sha256']:
        raise RuntimeError('权重核验回执变化。')
    if model_path.resolve() != Path(receipt['path']).resolve():
        raise RuntimeError('模型路径不符。')
    for name, digest in frozen['original_calls_sha256'].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('旧调用输入变化。')
    for name, record in receipt['files'].items():
        if (model_path / name).stat().st_size != record['bytes'] or sha(model_path / name) != record['sha256']:
            raise RuntimeError('本地权重/config SHA变化：' + name)
    preflight = gpu_preflight(frozen['model_spec'])
    save(output / 'gpu_preflight.json', preflight)
    print('GPU检查通过', json.dumps(preflight, ensure_ascii=False), flush=True)
    model = LocalTextVL(model_path, MODEL_ID, None)
    rows = []
    for record in frozen['records']:
        prediction = model.predict(record['messages'])
        choice, error = parse(prediction['response'], record['menu'])
        row = {'record': copy.deepcopy(record), 'prediction': prediction, 'choice': choice,
               'parse_error': error, 'acceptable': choice in record['allowed'],
               'errors': classify(record, choice, error)}
        rows.append(row)
        save(output / 'calls.json', rows)
        print(len(rows), record['id'], choice, row['acceptable'], row['errors'], flush=True)
    summary = summarize(rows, model.metadata(), preflight, frozen)
    save(output / 'summary.json', summary)
    save(RESULT / 'basic_summary.json', summary)
    print('VL基础结果', json.dumps(summary['groups'], ensure_ascii=False),
          '门槛通过', summary['gate_passed'], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('prepare', 'evaluate'))
    parser.add_argument('--model-path', type=Path, default=ROOT / 'models/Qwen2.5-VL-7B-Instruct')
    parser.add_argument('--output-dir', type=Path, default=RESULT / 'raw/basic')
    args = parser.parse_args()
    if args.stage == 'prepare':
        prepare(args.model_path)
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if any(args.output_dir.iterdir()):
            raise RuntimeError('禁止覆盖既有尝试。')
        evaluate(args.output_dir, args.model_path)


if __name__ == '__main__':
    main()
