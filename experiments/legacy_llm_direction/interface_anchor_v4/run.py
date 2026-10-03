"""预先冻结七种格式样例的事后诊断，固定12个多物品full-history输入。"""
import argparse
import copy
import json
from pathlib import Path

from experiments.model_scale_v4.backend import ConfigurableLocalModel
from experiments.model_scale_v4.run import gpu_preflight
from experiments.physical.protocol import parse, SYSTEM
from experiments.physical.run import ROOT, sha, save
from experiments.physical_v3_2.progress import public_progress

RESULT = ROOT / 'results/interface_anchor_v4'
FREEZE = ROOT / 'experiments/interface_anchor_v4/cases/freeze.json'
OLD_SOURCE = ROOT / 'results/physical_v3_2/raw/dev/calls.json'
ORIGINAL_EXAMPLE = '示例：选择把green独立绕行放到right，输出{"choice":"careful_green_right"}。\n'
SOURCE_NAMES = ['experiments/interface_anchor_v4/run.py', 'experiments/model_scale_v4/backend.py',
                'experiments/model_scale_v4/run.py', 'experiments/language/backend.py',
                'experiments/physical/protocol.py', 'experiments/physical_v3_2/progress.py']
MODEL = {'model_id': 'Qwen/Qwen2.5-3B-Instruct',
         'revision': 'aa8e72537993ba99e69dfaafa59ed015b17504d1',
         'path': str((ROOT / 'models/Qwen2.5-3B-Instruct').resolve()),
         'total_weights_bytes': 6171926992}


def source_hashes():
    return {name: sha(ROOT / name) for name in SOURCE_NAMES}


def variants():
    if SYSTEM.count(ORIGINAL_EXAMPLE) != 1:
        raise RuntimeError('冻结SYSTEM具体示例与已核验行不符。')
    result = []
    for item in ('red', 'blue', 'green'):
        for target in ('left', 'right'):
            replacement = f'示例：选择把{item}独立绕行放到{target}，输出{{"choice":"careful_{item}_{target}"}}。\n'
            result.append({'id': f'example_{item}_{target}', 'example_item': item,
                           'example_target': target,
                           'system': SYSTEM.replace(ORIGINAL_EXAMPLE, replacement, 1)})
    result.append({'id': 'format_only', 'example_item': None, 'example_target': None,
                   'system': SYSTEM.replace(ORIGINAL_EXAMPLE, '输出格式：{"choice":"候选ID"}。\n', 1)})
    return result


def freeze():
    if FREEZE.exists():
        raise RuntimeError('锚定诊断已冻结，禁止覆盖。')
    old = [r for r in json.loads(OLD_SOURCE.read_text()) if r['view'] == 'full_history']
    if len(old) != 12 or any(r['messages'][0]['content'] != SYSTEM for r in old):
        raise RuntimeError('既有12条full-history输入不符合冻结SYSTEM。')
    rows = [{'id': r['case']['id'], 'messages': copy.deepcopy(r['messages']),
             'allowed': r['case']['allowed_progress_choices'],
             'menu': r['case']['observation']['candidates'],
             'old_choice': r['choice'], 'old_acceptable': r['progress_choice']}
            for r in old]
    save(FREEZE, {'version': 'post-hoc-anchor-v4.0', 'model': MODEL,
                  'variants': variants(), 'fixtures': rows, 'calls': 84,
                  'source_sha256': source_hashes(), 'old_source_sha256': sha(OLD_SOURCE),
                  'protocol': '仅改变一个SYSTEM样例行，用户观察/20候选/评分逐字保持；所有7版本报告，不选择最好提示重算旧实验。',
                  'limits': '事后接口锚定诊断，不是结构留出；format_only移除示例语义并改变token长度，不能归因单一词token。'})
    print('冻结锚定诊断84调用', sha(FREEZE), flush=True)


def evaluate(output):
    frozen = json.loads(FREEZE.read_text())
    if frozen['source_sha256'] != source_hashes() or frozen['old_source_sha256'] != sha(OLD_SOURCE):
        raise RuntimeError('锚定诊断代码或旧输入发生改变。')
    preflight = gpu_preflight(frozen['model'])
    save(output / 'gpu_preflight.json', preflight)
    print('GPU检查通过', json.dumps(preflight, ensure_ascii=False), flush=True)
    spec = frozen['model']
    model = ConfigurableLocalModel(spec['path'], spec['model_id'], spec['revision'])
    rows = []
    for variant in frozen['variants']:
        for fixture in frozen['fixtures']:
            msg = copy.deepcopy(fixture['messages'])
            msg[0]['content'] = variant['system']
            prediction = model.predict(msg)
            choice, error = parse(prediction['response'], fixture['menu'])
            tokens = choice.split('_') if choice and choice not in ('request_clear', 'yield') else []
            item = tokens[1] if len(tokens) == 3 else None
            target = tokens[2] if len(tokens) == 3 else None
            progress = public_progress(json.loads(msg[1]['content']))
            row = {'variant': variant['id'], 'fixture': fixture['id'], 'messages': msg,
                   'prediction': prediction, 'choice': choice, 'parse_error': error,
                   'acceptable': choice in fixture['allowed'],
                   'selected_item': item, 'selected_target': target,
                   'selected_completed_item': item in progress['done_under_public_goals'],
                   'wrong_destination': item is not None and target != progress['current_goals_from_public_history'][item],
                   'matches_example_item': item == variant['example_item'] if variant['example_item'] else None,
                   'matches_example_target': target == variant['example_target'] if variant['example_target'] else None,
                   'old_choice': fixture['old_choice'], 'old_acceptable': fixture['old_acceptable']}
            rows.append(row)
            print(variant['id'], fixture['id'], choice, row['acceptable'], flush=True)
            save(output / 'calls.json', rows)
    summaries = {}
    for variant in frozen['variants']:
        subset = [r for r in rows if r['variant'] == variant['id']]
        distribution = {}
        for row in subset:
            distribution[row['choice'] or 'parse_error'] = distribution.get(row['choice'] or 'parse_error', 0) + 1
        summaries[variant['id']] = {'acceptable': sum(r['acceptable'] for r in subset), 'total': len(subset),
            'matches_example_item': sum(bool(r['matches_example_item']) for r in subset) if variant['example_item'] else None,
            'matches_example_target': sum(bool(r['matches_example_target']) for r in subset) if variant['example_target'] else None,
            'selected_completed_item': sum(r['selected_completed_item'] for r in subset),
            'wrong_destination': sum(r['wrong_destination'] for r in subset),
            'parse_errors': sum(r['parse_error'] is not None for r in subset), 'choice_distribution': distribution}
    original = [r for r in rows if r['variant'] == 'example_green_right']
    summary = {'variants': summaries, 'calls': len(rows), 'model': model.metadata(),
               'generation_hit_limit': sum(r['prediction']['generation_hit_limit'] for r in rows),
               'original_repeat': {'same_choice': sum(r['choice'] == r['old_choice'] for r in original),
                                    'same_acceptable': sum(r['acceptable'] == r['old_acceptable'] for r in original),
                                    'old_acceptable': sum(r['old_acceptable'] for r in original), 'total': len(original)},
               'gpu_preflight': preflight, 'freeze_sha256': sha(FREEZE),
               'source_sha256': source_hashes(), 'interpretation': frozen['limits']}
    save(output / 'summary.json', summary)
    save(RESULT / 'summary.json', summary)
    pairs = []
    for fixture in frozen['fixtures']:
        variants_for_case = [r for r in rows if r['fixture'] == fixture['id']]
        pairs.append({'fixture': fixture['id'], 'old_choice': fixture['old_choice'],
                       'choices': {r['variant']: r['choice'] for r in variants_for_case},
                       'acceptable': {r['variant']: r['acceptable'] for r in variants_for_case}})
    save(RESULT / 'paired_changes.json', pairs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('freeze', 'evaluate'))
    parser.add_argument('--output-dir', type=Path, default=RESULT / 'raw/evaluation')
    args = parser.parse_args()
    if args.stage == 'freeze':
        freeze()
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if any(args.output_dir.iterdir()):
            raise RuntimeError('输出目录非空，禁止覆盖。')
        evaluate(args.output_dir)


if __name__ == '__main__':
    main()
