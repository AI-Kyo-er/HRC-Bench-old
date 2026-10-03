"""跨模型中性格式的限定事后对照；只替换已固定format_only一行。"""
import argparse
import copy
import json
from pathlib import Path

from experiments.interface_anchor_v4.run import variants
from experiments.local_vl_v4.backend import LocalTextVL
from experiments.local_vl_v4.run import SOURCES as VL_SOURCES, summarize
from experiments.model_scale_v4.run import classify, gpu_preflight
from experiments.physical.protocol import parse
from experiments.physical.run import ROOT, save, sha

RESULT = ROOT / 'results/neutral_vl_v4'
FREEZE = ROOT / 'experiments/neutral_vl_v4/cases/freeze.json'
BASELINE = ROOT / 'experiments/local_vl_v4/cases/freeze.json'
RECEIPT = ROOT / 'results/local_vl_v4/local_weights_receipt.json'
SOURCES = VL_SOURCES + ['experiments/interface_anchor_v4/run.py', 'experiments/neutral_vl_v4/run.py']


def source_hashes():
    return {name: sha(ROOT / name) for name in SOURCES}


def neutral_records():
    records = copy.deepcopy(json.loads(BASELINE.read_text())['records'])
    neutral = next(v['system'] for v in variants() if v['id'] == 'format_only')
    for row in records:
        row['messages'][0]['content'] = neutral
    return records


def freeze():
    if FREEZE.exists():
        raise RuntimeError('中性VL版本已冻结，禁止覆盖。')
    old = json.loads(BASELINE.read_text())
    frozen = {'version': 'neutral-vl-text-v4.0', 'records': neutral_records(),
        'model_spec': old['model_spec'], 'generation': old['generation'], 'gate': old['gate'],
        'source_sha256': source_hashes(), 'baseline_freeze_sha256': sha(BASELINE),
        'weights_receipt_sha256': sha(RECEIPT),
        'original_calls_sha256': old['original_calls_sha256'],
        'interpretation': '限定事后中性格式对照，仅复用3B已固定format_only一行，不选择最佳示例。旧VL40结果保留；同16/16+全历史12/12门槛，若仍未通过本轮停止改提示；若通过仍需独立新输入/安全控制验证，不立即作结构归因。'}
    save(FREEZE, frozen)
    print('中性VL40冻结', sha(FREEZE), flush=True)


def evaluate(output, model_path):
    frozen = json.loads(FREEZE.read_text())
    receipt = json.loads(RECEIPT.read_text())
    if frozen['source_sha256'] != source_hashes() or sha(BASELINE) != frozen['baseline_freeze_sha256']:
        raise RuntimeError('代码或原VL冻结变化。')
    if sha(RECEIPT) != frozen['weights_receipt_sha256'] or model_path.resolve() != Path(receipt['path']).resolve():
        raise RuntimeError('权重回执或模型路径变化。')
    for name, digest in frozen['original_calls_sha256'].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('旧调用变化。')
    for name, item in receipt['files'].items():
        if (model_path / name).stat().st_size != item['bytes'] or sha(model_path / name) != item['sha256']:
            raise RuntimeError('本地权重/config SHA变化：' + name)
    preflight = gpu_preflight(frozen['model_spec'])
    save(output / 'gpu_preflight.json', preflight)
    print('GPU检查通过', json.dumps(preflight, ensure_ascii=False), flush=True)
    model = LocalTextVL(model_path, frozen['model_spec']['model_id'], None)
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
    summary.update(freeze_sha256=sha(FREEZE), source_sha256=source_hashes(),
                   baseline_freeze_sha256=sha(BASELINE))
    save(output / 'summary.json', summary)
    save(RESULT / 'basic_summary.json', summary)
    baseline_rows = json.loads((ROOT / 'results/local_vl_v4/raw/basic/calls.json').read_text())
    pairs = [{'id': new['record']['id'], 'view': new['record']['view'],
        'original_choice': old['choice'], 'neutral_choice': new['choice'],
        'original_acceptable': old['acceptable'], 'neutral_acceptable': new['acceptable'],
        'choice_changed': old['choice'] != new['choice']}
        for old, new in zip(baseline_rows, rows)]
    save(RESULT / 'paired_changes.json', pairs)
    print('中性VL基础结果', json.dumps(summary['groups'], ensure_ascii=False),
          '门槛通过', summary['gate_passed'], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('freeze', 'evaluate'))
    args = parser.parse_args()
    if args.stage == 'freeze':
        freeze()
    else:
        output = RESULT / 'raw/basic'
        output.mkdir(parents=True, exist_ok=True)
        if any(output.iterdir()):
            raise RuntimeError('禁止覆盖旧尝试。')
        evaluate(output, ROOT / 'models/Qwen2.5-VL-7B-Instruct')


if __name__ == '__main__':
    main()
