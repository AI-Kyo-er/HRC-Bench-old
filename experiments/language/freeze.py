"""生成冻结case；配对由稳定ID的领域、结构、variant确定。"""
import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path
from experiments.language.environment import DOMAINS, STRUCTURES, build_case


def freeze(root):
    root.mkdir(parents=True, exist_ok=True)
    for split in ('dev', 'formal'):
        cases = [build_case(domain, structure, variant, split, partner_accepts)
                 for domain in DOMAINS
                 for structure in (STRUCTURES[:-1] if split == 'dev' else STRUCTURES)
                 for variant in ((0,) if split == 'dev' else (0, 1))
                 for partner_accepts in ((True,) if split == 'dev' else (True,False))]
        path = root / f'{split}.jsonl'
        path.write_text(''.join(json.dumps(case, ensure_ascii=False, sort_keys=True)+'\n' for case in cases))
    receipt = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (root/'dev.jsonl',root/'formal.jsonl')}
    (root/'freeze.json').write_text(json.dumps({'protocol_version': '2.1', 'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
        'revision_reason':'目标变体与伙伴接受/拒绝轴独立交叉；2.0草案绑定，不保留作实验输入。', 'hashes': receipt,
        'dev_instances':12,'formal_instances':60,'heldout_structure':'nested_reentry',
        'frozen_before_dev_inference':True},indent=2)+'\n')


if __name__ == '__main__':
    freeze(Path('experiments/language/cases'))
