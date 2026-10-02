"""40条既有冻结输入的本地规模参照；不修改提示、候选或集合评分。"""
import argparse
import copy
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

from experiments.physical.protocol import parse
from experiments.physical.run import ROOT, sha, save
from experiments.physical_v3_2.progress import public_progress

RESULT = ROOT / 'results/model_scale_v4'
FREEZE = ROOT / 'experiments/model_scale_v4/cases/freeze.json'
SPEC = RESULT / 'model_spec.json'
SOURCES = ['experiments/model_scale_v4/backend.py', 'experiments/model_scale_v4/run.py',
           'experiments/model_scale_v4/download.py', 'experiments/language/backend.py',
           'experiments/physical/protocol.py', 'experiments/physical_v3_2/progress.py']


def source_hashes():
    return {name: sha(ROOT / name) for name in SOURCES}


def build_records():
    calibration_path = ROOT / 'results/physical_v3/raw/calibration_v3_1/calls.json'
    progress_path = ROOT / 'results/physical_v3_2/raw/dev/calls.json'
    calibration = json.loads(calibration_path.read_text())
    progress = json.loads(progress_path.read_text())
    records = []
    for row in calibration:
        records.append({'id': 'single_' + row['id'], 'suite': 'single', 'mode': row['mode'],
            'view': 'single', 'messages': copy.deepcopy(row['messages']), 'menu': row['menu'],
            'allowed': row['allowed'], 'reference_3b_choice': row['choice'],
            'reference_3b_acceptable': row['acceptable']})
    for row in progress:
        records.append({'id': 'multi_' + row['case']['id'] + '_' + row['view'],
            'suite': 'multi', 'view': row['view'], 'completed_item': row['case']['completed_item'],
            'messages': copy.deepcopy(row['messages']), 'menu': row['case']['observation']['candidates'],
            'allowed': row['case']['allowed_progress_choices'],
            'reference_3b_choice': row['choice'], 'reference_3b_acceptable': row['progress_choice']})
    if len(calibration) != 16 or len(progress) != 24:
        raise RuntimeError('输入数量不符合既有冻结16+24调用。')
    return records, {str(p.relative_to(ROOT)): sha(p) for p in (calibration_path, progress_path)}


def freeze():
    if FREEZE.exists():
        raise RuntimeError('规模参照已冻结，禁止覆盖。')
    records, old_files = build_records()
    spec = json.loads(SPEC.read_text())
    save(FREEZE, {'version': 'model-scale-v4.0', 'model_spec': spec, 'model_spec_sha256': sha(SPEC),
        'records': records, 'source_sha256': source_hashes(), 'original_calls_sha256': old_files,
        'original_freezes_sha256': {name: sha(ROOT / name) for name in
             ('experiments/physical/cases/freeze.json', 'experiments/physical_v3_2/cases/dev_freeze.json')},
        'gate': {'single': {'required': 16, 'total': 16},
                 'multi_full_history': {'required': 12, 'total': 12},
                 'meaning': '小集工程门槛；不是统计能力或交互组合能力证明。未全过先诊断，不扩大formal。'},
        'generation': {'seed': 0, 'do_sample': False, 'max_new_tokens': 96,
                       'dtype': 'bfloat16', 'attention': 'sdpa', 'batch_size': 1},
        'interpretation': '原始3B结果仅作描述参照，未独立复跑；同系列大小并非单因素随机因果比较。'})
    print('冻结40条原始输入', sha(FREEZE), flush=True)


def classify(record, choice, error):
    if error:
        return ['parse_or_unknown_choice']
    if choice in record['allowed']:
        return []
    if record['suite'] == 'single':
        if record['mode'] == 'yield':
            return ['yield_requirement_ignored']
        if choice in ('request_clear', 'yield'):
            return ['coordination_instead_of_placement']
        allowed_goals = {x.rsplit('_', 1)[-1] for x in record['allowed'] if '_' in x}
        result = []
        if choice.rsplit('_', 1)[-1] not in allowed_goals:
            result.append('wrong_destination')
        if record['mode'] == 'refusal' and not choice.startswith('careful_'):
            result.append('refusal_alternative_not_used')
        if not result:
            result.append('unsupported_action_mode')
        return result
    progress = public_progress(json.loads(record['messages'][1]['content']))
    if choice in ('request_clear', 'yield'):
        return ['coordination_instead_of_progress']
    mode, item, destination = choice.split('_')
    result = []
    if item in progress['done_under_public_goals']:
        result.append('already_completed_item')
    if destination != progress['current_goals_from_public_history'][item]:
        result.append('wrong_destination')
    if mode == 'assisted' and not progress['accepted_clearance_help']:
        result.append('unaccepted_assistance')
    return result or ['other_nonprogress']


def gpu_preflight(spec):
    visible = os.environ.get('CUDA_VISIBLE_DEVICES', '')
    if not visible.isdigit():
        raise RuntimeError('必须通过CUDA_VISIBLE_DEVICES指定唯一物理GPU编号。')
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw = subprocess.check_output(['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used,memory.free',
                                  '--format=csv,noheader,nounits'], text=True)
    rows = [r.split(',') for r in raw.strip().splitlines()]
    selected = next(r for r in rows if int(r[0].strip()) == int(visible))
    # BF16权重 + 3GiB用于短输入KV、prefill、CUDA上下文与裕量；禁止自动量化/分卡。
    required = math.ceil((spec['total_weights_bytes'] + 3 * 1024**3) / 1024**2)
    result = {'checked_utc': timestamp, 'physical_gpu': int(visible), 'name': selected[1].strip(),
              'memory_total_mib': int(selected[2]), 'memory_used_mib': int(selected[3]),
              'memory_free_mib': int(selected[4]), 'required_free_mib': required,
              'estimate_basis': 'official BF16 shard bytes + 3GiB; frozen input <=1153tokens, output<=96'}
    if result['memory_free_mib'] < required:
        raise RuntimeError(json.dumps({'reason': '所选GPU显存不足，未加载模型。', 'preflight': result}, ensure_ascii=False))
    return result


def evaluate(output, model_path):
    from .backend import ConfigurableLocalModel
    frozen = json.loads(FREEZE.read_text())
    if frozen['source_sha256'] != source_hashes() or frozen['model_spec_sha256'] != sha(SPEC):
        raise RuntimeError('代码或模型规格与冻结不一致。')
    for name, digest in frozen['original_calls_sha256'].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('旧原始输入发生变化。')
    spec = frozen['model_spec']
    download = json.loads((RESULT / 'download_receipt.json').read_text())
    if not download['all_weights_match_official'] or download['revision'] != spec['revision']:
        raise RuntimeError('权重来源/版本校验未通过。')
    if Path(model_path).resolve() != Path(download['path']).resolve():
        raise RuntimeError('模型路径与已验证权重目录不同。')
    preflight = gpu_preflight(spec)
    save(output / 'gpu_preflight.json', preflight)
    print('GPU检查通过', json.dumps(preflight, ensure_ascii=False), flush=True)
    model = ConfigurableLocalModel(model_path, spec['model_id'], spec['revision'])
    rows = []
    for record in frozen['records']:
        prediction = model.predict(record['messages'])
        choice, error = parse(prediction['response'], record['menu'])
        row = {'record': record, 'prediction': prediction, 'choice': choice,
               'parse_error': error, 'acceptable': choice in record['allowed'],
               'errors': classify(record, choice, error)}
        rows.append(row)
        print(record['id'], choice, row['acceptable'], row['errors'], flush=True)
        save(output / 'calls.json', rows)
    groups = {}
    for name, subset in [('single', [r for r in rows if r['record']['suite'] == 'single'])] + [
        (view, [r for r in rows if r['record']['suite'] == 'multi' and r['record']['view'] == view])
        for view in ('full_history', 'public_progress_aid')]:
        errors = {}
        for row in subset:
            for error in row['errors']:
                errors[error] = errors.get(error, 0) + 1
        groups[name] = {'acceptable': sum(r['acceptable'] for r in subset), 'total': len(subset),
            'reference_3b_acceptable': sum(r['record']['reference_3b_acceptable'] for r in subset),
            'parse_errors': sum(r['parse_error'] is not None for r in subset), 'errors': errors}
    summary = {'groups': groups, 'gate_passed': groups['single']['acceptable'] == 16 and
                groups['full_history']['acceptable'] == 12,
               'generation_hit_limit': sum(r['prediction']['generation_hit_limit'] for r in rows),
               'model': model.metadata(), 'gpu_preflight': preflight,
               'freeze_sha256': sha(FREEZE), 'source_sha256': source_hashes(),
               'download_receipt_sha256': sha(RESULT / 'download_receipt.json'),
               'interpretation': frozen['interpretation']}
    save(output / 'summary.json', summary)
    save(RESULT / 'basic_summary.json', summary)
    print('基础结果', json.dumps(groups, ensure_ascii=False), '门槛通过', summary['gate_passed'], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('freeze', 'evaluate'))
    parser.add_argument('--model-path', type=Path)
    parser.add_argument('--output-dir', type=Path, default=RESULT / 'raw/basic')
    args = parser.parse_args()
    if args.stage == 'freeze':
        freeze()
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if any(args.output_dir.iterdir()):
            raise RuntimeError('输出目录非空，禁止覆盖先前尝试。')
        spec = json.loads(SPEC.read_text())
        model_path = args.model_path or ROOT / 'models' / spec['model_id'].split('/')[-1]
        evaluate(args.output_dir, model_path)


if __name__ == '__main__':
    main()
