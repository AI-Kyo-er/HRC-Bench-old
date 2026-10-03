"""仅修复用户目录迁移产生的本地链接，保留正文、对话及历史校验回执。"""
import hashlib
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import markdown
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / '.codex/codex-gen-content'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def destination(href):
    path = unquote(urlsplit(href).path)
    name = Path(path).name
    for group in ('results', 'experiments'):
        if re.search(r'(?:^|/)' + group + r'(?:/|$)', path):
            rem = re.split(r'(?:^|/)' + group + r'(?:/|$)', path, maxsplit=1)[-1]
            candidate = ROOT / group / rem
            if candidate.exists():
                return candidate
    if (BASE / 'mds' / name).is_file():
        return BASE / 'mds' / name
    if name in ('idea.md', 'idea-conversation.md') and (ROOT / '.codex/mds' / name).is_file():
        return ROOT / '.codex/mds' / name
    if (BASE / 'reports' / name).is_file():
        return BASE / 'reports' / name
    if path.endswith('data1/sieniwgroup/sieniw'):
        return Path('/data1/sieniwgroup/sieniw')
    return None


def main():
    files = list((BASE / 'mds').glob('*.md')) + [
        BASE / 'reports/report_实验阶段快照_20261003_165341.md',
        BASE / 'reports/html/report_实验阶段快照_20261003_165341.html',
        ROOT / '.codex/mds/idea.md']
    conversation = ROOT / '.codex/mds/idea-conversation.md'
    legacy_receipt = BASE / 'reports/report_实验阶段快照_20261003_165341_validation.json'
    protected = {str(p.relative_to(ROOT)): digest(p) for p in (conversation, legacy_receipt)}
    modified = []
    unresolved = []
    for file in files:
        before = file.read_text()
        before_sha = digest(file)
        soup = BeautifulSoup(before if file.suffix == '.html' else markdown.markdown(before, extensions=['tables']), 'html.parser')
        mapping = {}
        for a in soup.find_all('a', href=True):
            old = a['href']
            url = urlsplit(old)
            if url.scheme or url.netloc or not url.path or (file.parent / unquote(url.path)).resolve().exists():
                continue
            target = destination(old)
            if target is None or not target.exists():
                unresolved.append(dict(file=str(file.relative_to(ROOT)), href=old))
                continue
            new = os.path.relpath(target, file.parent)
            if url.fragment:
                new += '#' + url.fragment
            if url.query:
                raise ValueError('未授权处理带查询参数的本地路径')
            mapping[old] = new
        after = before
        changes = []
        for old, new in mapping.items():
            old_marker = f'href="{html.escape(old, quote=True)}"' if file.suffix == '.html' else '](' + old + ')'
            new_marker = f'href="{html.escape(new, quote=True)}"' if file.suffix == '.html' else '](' + new + ')'
            count = after.count(old_marker)
            assert count > 0, (file, old)
            after = after.replace(old_marker, new_marker)
            changes.append(dict(old=old, new=new, occurrences=count))
        if after != before:
            # 每个差异都由指定href/Markdown目的地址替换构成，不重序列化HTML或修改正文。
            expected = after
            for change in reversed(changes):
                old, new = change['old'], change['new']
                marker = f'href="{html.escape(new, quote=True)}"' if file.suffix == '.html' else '](' + new + ')'
                previous = f'href="{html.escape(old, quote=True)}"' if file.suffix == '.html' else '](' + old + ')'
                expected = expected.replace(marker, previous)
            assert expected == before
            assert digest(file) == before_sha, '其他编辑者同时修改了文档，未写入'
            file.write_text(after)
            modified.append(dict(file=str(file.relative_to(ROOT)), before_sha256=before_sha,
                                 after_sha256=digest(file), links=changes))
    assert protected == {name: digest(ROOT / name) for name in protected}
    receipt = dict(modified_files=modified, total_link_replacements=sum(c['occurrences'] for f in modified for c in f['links']),
                   unresolved=unresolved, only_link_targets_changed=True, protected_files_unchanged=protected,
                   script_sha256=digest(Path(__file__)),
                   historical_validation_note='旧验证JSON及旧HTML内正文SHA保留原值，对应原制作时点产物；本回执只重新核对迁移后的链接，不覆盖旧实验事实或声称旧SHA匹配修链后的文件。',
                   no_old_skill_or_generator_invoked=True, no_experiment_source_or_runtime_changes=True)
    (BASE / 'reports/目录迁移链接核验_20261003.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(files=len(modified), replacements=receipt['total_link_replacements'], unresolved=unresolved), ensure_ascii=False))


if __name__ == '__main__':
    main()
