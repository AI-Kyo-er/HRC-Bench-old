"""核对离线案例解释的原始记录锚点；不自动判断语义或生成协作分数。"""
from hashlib import sha256
import json
from pathlib import Path


def pointer_value(value, pointer):
    if pointer == '':
        return value
    if not pointer.startswith('/'):
        raise ValueError('证据 pointer 必须是 JSON Pointer')
    for part in pointer[1:].split('/'):
        key = part.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def verify_review(root):
    root = Path(root).resolve()
    review_path = root / 'public_request_response_review.json'
    review_bytes = review_path.read_bytes()
    review = json.loads(review_bytes)
    if review.get('review_type') != 'assistant_review_of_saved_records_not_human_study':
        raise ValueError('本核查仅用于明确标识的保存记录助手审阅')
    if review.get('formal_benchmark_score') is not None:
        raise ValueError('案例证据锚点核查不能认证正式协作评分')
    for name in ['interaction_verification.json', 'independent_video_verification.json']:
        if json.loads((root / name).read_text()).get('status') != 'verified':
            raise ValueError('案例尚未完成独立输入／执行／视频核验：' + name)
    if not (root / 'summary.json').exists():
        raise ValueError('案例缺少完整终态结果')
    findings = review.get('findings', [])
    if not findings:
        raise ValueError('案例解释缺少原始证据锚点')
    sources = {}
    verified = []
    for finding in findings:
        if not finding.get('interpretation') or not finding.get('evidence'):
            raise ValueError('每项解释必须有文本及原始证据')
        anchors = []
        for anchor in finding['evidence']:
            relative = Path(anchor['file'])
            path = (root / relative).resolve()
            if relative.is_absolute() or not path.is_relative_to(root):
                raise ValueError('证据路径必须在本运行目录内')
            if relative.as_posix() not in sources:
                raw = path.read_bytes()
                value = ([json.loads(line) for line in raw.decode().splitlines() if line.strip()]
                         if path.suffix == '.jsonl' else json.loads(raw))
                sources[relative.as_posix()] = {'sha256': sha256(raw).hexdigest(), 'value': value}
            source = sources[relative.as_posix()]
            value = source['value']
            if 'row' in anchor:
                if path.suffix != '.jsonl' or not isinstance(anchor['row'], int) or anchor['row'] < 0:
                    raise ValueError('row 是 JSONL 非空记录的零起始索引')
                value = value[anchor['row']]
            actual = pointer_value(value, anchor['pointer'])
            # Python会把True与1视为相等；证据中的事实布尔值不能这样混同。
            actual_json=json.dumps(actual, sort_keys=True, allow_nan=False)
            expected_json=json.dumps(anchor['equals'], sort_keys=True, allow_nan=False)
            if actual_json != expected_json:
                raise ValueError('解释引用与原始记录不符：' + json.dumps(anchor, ensure_ascii=False))
            anchors.append({**anchor, 'source_sha256': source['sha256']})
        verified.append({'interpretation': finding['interpretation'], 'evidence': anchors})
    return {
        'status': 'evidence_anchors_verified',
        'review_sha256': sha256(review_bytes).hexdigest(),
        'source_sha256': {name: entry['sha256'] for name, entry in sources.items()},
        'findings': verified,
        'semantic_validity': 'assistant_interpretation_not_independently_validated',
        'formal_benchmark_score': None,
        'interpretation': '只核对引用记录、值和文件版本，不认证解释正确、真人拟真或cobalance。',
    }
