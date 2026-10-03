"""独立长文阅读页：仅排版给定Markdown，不使用旧报告技能或模板。"""
import argparse
import hashlib
import html
import json
import re
import subprocess
import tempfile
from pathlib import Path

import markdown
from bs4 import BeautifulSoup

CSS = '''
:root{color-scheme:light;--paper:#fff;--bg:#f6f7f9;--ink:#202633;--muted:#596374;--line:#dfe3eb;--link:#215ab4;--code:#eef2f8}
:root.dark{color-scheme:dark;--paper:#171e29;--bg:#101620;--ink:#e8edf5;--muted:#b1bdcf;--line:#354154;--link:#9dbfff;--code:#253247}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;color:var(--ink);background:var(--bg);font:17px/1.95 system-ui,-apple-system,"Microsoft YaHei",sans-serif}a{color:var(--link);text-underline-offset:.2em;overflow-wrap:anywhere}a:hover{text-decoration-thickness:2px}button{font:inherit;font-size:14px;color:var(--ink);background:var(--paper);border:1px solid var(--line);border-radius:6px;padding:5px 12px;cursor:pointer}:focus-visible{outline:3px solid var(--link);outline-offset:3px}
.layout{display:grid;grid-template-columns:235px minmax(0,800px);gap:36px;max-width:1160px;padding:36px 24px;margin:auto}.toc{position:sticky;top:24px;align-self:start;max-height:calc(100vh - 48px);overflow-y:auto;font-size:13px;line-height:1.6}.toc strong{display:block;margin-bottom:12px}.toc a{display:block;color:var(--muted);text-decoration:none;padding:5px 8px;border-left:2px solid transparent}.toc a:hover{border-color:var(--link);color:var(--link)}article{min-width:0;background:var(--paper);padding:36px 40px;border:1px solid var(--line);border-radius:8px}.tools{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:28px;font-size:14px}.reading-note{font-size:13px;color:var(--muted);margin:0 0 16px}h1{font-size:32px;line-height:1.45;margin:0 0 28px}h2{font-size:25px;line-height:1.55;margin:48px 0 22px;padding-top:24px;border-top:1px solid var(--line)}h3{font-size:20px;line-height:1.6;margin:28px 0 16px}h4{font-size:18px;margin:24px 0 12px}p{margin:0 0 20px}li{margin-bottom:10px}ul,ol{padding-left:26px}blockquote{margin:24px 0;padding:14px 20px;border-left:3px solid var(--link);background:var(--code)}blockquote p:last-child{margin:0}code{font: .88em/1.7 ui-monospace,Consolas,monospace;overflow-wrap:anywhere;background:var(--code);border-radius:3px;padding:2px 4px}pre{padding:16px;overflow:auto;background:var(--code);border-radius:6px}pre code{padding:0}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.7}th,td{border:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}.table-scroll{overflow:auto;max-width:100%}footer{font-size:12px;color:var(--muted);margin-top:48px;padding-top:20px;border-top:1px solid var(--line);overflow-wrap:anywhere}img{max-width:100%;height:auto}
@media(max-width:950px){.layout{grid-template-columns:1fr;max-width:840px;padding:20px 14px;gap:20px}.toc{position:relative;top:0;max-height:none;columns:2;column-gap:24px;border-bottom:1px solid var(--line);padding-bottom:16px}.toc strong{column-span:all}.toc a{break-inside:avoid}article{padding:28px}}
@media(max-width:520px){body{font-size:16px;line-height:1.9}.layout{padding:12px 8px}.toc{columns:1;max-height:320px;overflow:auto}article{padding:24px 18px}h1{font-size:27px}h2{font-size:23px}h3{font-size:19px}.tools{gap:8px}table{font-size:13px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{.toc,.tools,.reading-note{display:none!important}:root,:root.dark{--paper:#fff;--bg:#fff;--ink:#000;--muted:#333;--line:#aaa;--link:#000;--code:#fff}body{font-size:10.5pt;line-height:1.7}.layout{display:block;padding:0;max-width:none}article{border:0;padding:0}h1{font-size:22pt}h2{font-size:16pt;break-after:avoid;margin-top:24pt}h3{font-size:13pt;break-after:avoid}p,li{orphans:3;widows:3}pre{white-space:pre-wrap;overflow-wrap:anywhere}.table-scroll{overflow:visible}table{table-layout:fixed;font-size:8pt}td,th{overflow-wrap:anywhere}thead{display:table-header-group}tr{break-inside:avoid}}
'''

JS = '''
(()=>{const root=document.documentElement,button=document.getElementById('theme');button.setAttribute('aria-pressed',String(root.classList.contains('dark')));button.addEventListener('click',()=>{const dark=root.classList.toggle('dark');button.setAttribute('aria-pressed',String(dark));try{localStorage.setItem('explanation-theme',dark?'dark':'light')}catch(_){}});document.getElementById('print').addEventListener('click',()=>window.print())})();
'''


def normalized_text(soup):
    return re.sub(r'\s+', '', soup.get_text(' ', strip=True))


def render(source, target):
    raw = source.read_text(encoding='utf-8')
    converted = markdown.markdown(raw, extensions=['tables', 'fenced_code'])
    body = BeautifulSoup(converted, 'html.parser')
    assert body.h1 is not None, '正文需包含一级标题'
    title = body.h1.get_text()
    original_text = normalized_text(body)
    toc = []
    for i, heading in enumerate(body.find_all(re.compile(r'^h[1-6]$')), 1):
        heading['id'] = heading.get('id', f'section-{i:03d}')
        if heading.name == 'h2':
            toc.append((heading['id'], heading.get_text()))
    for table in body.find_all('table'):
        wrapper = body.new_tag('div', attrs={'class': 'table-scroll'})
        table.wrap(wrapper)
    assert normalized_text(body) == original_text
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    navigation = ''.join(f'<a href="#{html.escape(key, quote=True)}">{html.escape(text)}</a>' for key, text in toc)
    initialization = "try{if(localStorage.getItem('explanation-theme')==='dark'||(!localStorage.getItem('explanation-theme')&&matchMedia('(prefers-color-scheme:dark)').matches))document.documentElement.classList.add('dark')}catch(_){}"
    document = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)}</title><meta name="description" content="逐轮说明实验目的、实际做法、证据与研究方向边界。"><style>{CSS}</style><script>{initialization}</script></head>
<body><div class="layout"><nav class="toc" aria-label="章节目录"><strong>章节目录 · 点击跳转</strong>{navigation}</nav><article><div class="tools"><a href="{html.escape(source.name, quote=True)}" download>下载同内容Markdown</a><button id="theme" type="button" aria-pressed="false">切换明暗</button><button id="print" type="button">打印 / 存为PDF</button></div><p class="reading-note">逐项说明 · 全文展开阅读</p><div id="report-body">{body}</div><footer>全文来自同目录Markdown；独立离线阅读页，无外部脚本或字体依赖。<br>正文SHA256：<code>{digest}</code></footer></article></div><script>{JS}</script></body></html>'''
    target.write_text(document, encoding='utf-8')
    page = BeautifulSoup(document, 'html.parser')
    assert normalized_text(page.select_one('#report-body')) == original_text
    links = []
    broken = []
    for a in page.find_all('a', href=True):
        href = a['href']
        if href.startswith('#'):
            assert page.find(id=href[1:]) is not None
        elif not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', href):
            name = href.split('#', 1)[0]
            if name:
                resolved = (target.parent / name).resolve()
                links.append(str(resolved))
                if not resolved.exists():
                    broken.append(href)
    assert not page.find('script', src=True) and not page.find('link', href=True)
    for script in page.find_all('script'):
        with tempfile.NamedTemporaryFile('w', suffix='.js', encoding='utf-8') as handle:
            handle.write(script.get_text());handle.flush()
            subprocess.run(['node', '--check', handle.name], check=True)
    receipt = dict(source=str(source), html=str(target),
                   source_sha256=digest, html_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                   renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   full_body_text_identical=True, all_content_default_expanded=True,
                   toc_sections=len(toc), local_links=len(links), broken_local_links=broken,
                   valid_internal_anchors=True, inline_js_syntax_passed=True,
                   no_external_runtime_dependencies=True, no_old_skill_template_or_script_used=True,
                   browser_validation_performed=False,
                   validation_limitation='仅静态正文、链接、锚点、CSS配置与JS语法核验；无可用浏览器，未声称桌面/手机交互或打印预览实测。')
    target.with_suffix('.validation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    assert not broken, f'本地链接缺失：{broken}'
    print(target)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('markdown', type=Path)
    parser.add_argument('html', type=Path)
    args = parser.parse_args()
    assert args.markdown.resolve().parent == args.html.resolve().parent
    render(args.markdown.resolve(), args.html.resolve())
