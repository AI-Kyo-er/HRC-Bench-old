"""只读核验冻结物理诊断，并输出小摘要、代表原始调用和视频。"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from .run import ROOT, sha, save


def audit_episode(path):
    calls = json.loads((path / 'decisions.json').read_text())
    ticks = 0
    contacts = {'robot_partner_ticks': 0, 'robot_partner_max_force': 0,
                'finger_object_ticks': 0, 'object_partner_ticks': 0,
                'robot_partner_phases': {}}
    for line in gzip.open(path / 'ticks.jsonl.gz', 'rt'):
        state = json.loads(line)
        ticks += 1
        rs = [c for c in state['contacts'] if {c['body_a'], c['body_b']} == {1, 11}]
        if rs:
            contacts['robot_partner_ticks'] += 1
            contacts['robot_partner_max_force'] = max(contacts['robot_partner_max_force'],
                                                       max(c['normal_force'] for c in rs))
            phase = state['phase']
            contacts['robot_partner_phases'][phase] = contacts['robot_partner_phases'].get(phase, 0) + 1
        contacts['finger_object_ticks'] += int(any(
            (c['body_a'] == 1 and c['body_b'] in (2, 3, 4) and c['link_a'] in (9, 10)) or
            (c['body_b'] == 1 and c['body_a'] in (2, 3, 4) and c['link_b'] in (9, 10))
            for c in state['contacts']))
        contacts['object_partner_ticks'] += int(any(
            11 in (c['body_a'], c['body_b']) and any(x in (2, 3, 4) for x in (c['body_a'], c['body_b']))
            for c in state['contacts']))
    rejections = {}
    actions = {}
    partner = []
    for call in calls:
        result = call['result']
        choice = result['choice']
        kind = choice.split('_')[0] if choice else 'parse_error'
        actions[kind] = actions.get(kind, 0) + 1
        if not result['valid']:
            reason = result['feedback']
            rejections[reason] = rejections.get(reason, 0) + 1
        if 'partner_motion' in result:
            partner.append(result['partner_motion'])
    return {'ticks': ticks, 'contacts': contacts, 'protocol_rejections': rejections,
            'action_types': actions, 'partner_motions': partner,
            'ticks_sha256': sha(path / 'ticks.jsonl.gz'),
            'decisions_sha256': sha(path / 'decisions.json'),
            'summary_sha256': sha(path / 'summary.json')}


def visuals(path, output):
    from PIL import Image, ImageDraw
    import imageio.v2 as imageio
    files = sorted((path / 'frames').glob('*.png'))
    if not files:
        return
    canvas = Image.new('RGB', (960, 540), 'white')
    for index, f in enumerate([files[round(i * (len(files) - 1) / 5)] for i in range(6)]):
        frame = Image.open(f)
        frame.thumbnail((320, 240))
        x, y = index % 3 * 320, index // 3 * 270
        canvas.paste(frame, (x, y))
        ImageDraw.Draw(canvas).text((x + 5, y + 242), f.name, fill='black')
    canvas.save(output / 'contact_sheet.png')
    with imageio.get_writer(output / 'rollout.mp4', fps=5, codec='libx264', macro_block_size=16) as writer:
        for f in files:
            writer.append_data(imageio.imread(f))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT / 'results/physical_v3')
    args = parser.parse_args()
    audit = {}
    representative = {}
    for policy in ('reference', 'model'):
        summary = json.loads((args.root / f'formal_{policy}_summary.json').read_text())
        audit[policy] = {}
        successful, failed = [], []
        for record in summary['records']:
            case_id = record['case']['id']
            path = args.root / 'raw' / f'formal_{policy}' / case_id
            audit[policy][case_id] = audit_episode(path)
            (successful if record['success'] else failed).append(path)
            if (path / 'frames').exists():
                visuals(path, path)
        chosen = [paths[0] for paths in (successful, failed) if paths]
        representative[policy] = [{
            'case_id': path.name, 'summary': json.loads((path / 'summary.json').read_text()),
            'decisions': json.loads((path / 'decisions.json').read_text())}
            for path in chosen]
    save(args.root / 'trajectory_audit.json', audit)
    save(args.root / 'representative_calls.json', representative)
    save(args.root / 'execution_receipt.json', {
        'freeze_sha256': sha(ROOT / 'experiments/physical/cases/freeze.json'),
        'summaries_sha256': {str(p.relative_to(ROOT)): sha(p) for p in
                             (args.root / 'formal_reference_summary.json', args.root / 'formal_model_summary.json')},
        'audit_sha256': sha(args.root / 'trajectory_audit.json'),
        'analysis_source_sha256': sha(Path(__file__)),
        'interpretation': '物理完成、协议拒绝、实际接触、未执行的安全前提拒绝分开；接触不是自动判为任务失败。'
    })


if __name__ == '__main__':
    main()
