"""将已核对的报告正文完整排版为离线HTML；不读取或修改实验业务源。"""
import argparse
import hashlib
import html
import os
import re
from pathlib import Path

import markdown
from bs4 import BeautifulSoup

SKILL = Path('/home/sieniw/.codex/skills/markdown-work-report')

CSS = r'''
:root{color-scheme:light;--bg:#f5f6f8;--paper:#fff;--ink:#182132;--muted:#596478;--line:#dce2eb;--accent:#225cb8;--soft:#eaf1ff;--warning:#8b4a00;--warning-bg:#fff4df}
:root.dark{color-scheme:dark;--bg:#101722;--paper:#192332;--ink:#edf1f8;--muted:#b0bdcf;--line:#344156;--accent:#9fc4ff;--soft:#213553;--warning:#ffd497;--warning-bg:#352b20}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:2rem}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.8 system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
a{color:var(--accent);text-underline-offset:.2em}a:hover{text-decoration-thickness:2px}button,input,select{font:inherit;color:inherit}button,select{cursor:pointer}button{background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:.4rem .8rem}button:hover{background:var(--soft)}:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
.report-shell{max-width:1460px;margin:auto;padding:32px;display:grid;grid-template-columns:220px minmax(0,1fr);gap:32px}.toc{position:sticky;top:28px;align-self:start;max-height:calc(100vh - 56px);overflow:auto;font-size:14px}.toc strong{display:block;margin-bottom:12px}.toc a{display:block;text-decoration:none;padding:6px 8px;border-left:2px solid transparent;color:var(--muted)}.toc a:hover,.toc a.active{background:var(--soft);color:var(--accent);border-left-color:var(--accent)}
main{min-width:0}.actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center;justify-content:flex-end;margin-bottom:20px}.status{color:var(--warning);background:var(--warning-bg);border:1px solid var(--line);padding:7px 14px;border-radius:8px;font-weight:700;display:inline-block}.eyebrow{font-size:14px;color:var(--muted);margin-top:18px}h1{font-size:clamp(28px,4vw,43px);line-height:1.25;margin:12px 0 20px;letter-spacing:-.02em}h2{font-size:24px;line-height:1.45;margin:0 0 20px}h3{font-size:20px}p{margin:0 0 16px}blockquote{margin:0 0 28px;border-left:4px solid var(--accent);background:var(--soft);padding:18px 22px;border-radius:0 8px 8px 0}blockquote p:last-child{margin:0}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:24px 0}.metric-card{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:18px}.metric-card small{display:block;color:var(--muted)}.metric-card strong{display:block;font-size:28px;line-height:1.4;margin:6px 0}.section-card{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:28px;margin:22px 0}.section-card details>summary{font-size:24px;font-weight:700;cursor:pointer;line-height:1.45;margin-bottom:18px}.section-card details:not([open])>summary{margin-bottom:0}.section-card li{margin-bottom:10px}.section-card ol,.section-card ul{padding-left:24px}
code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.88em;overflow-wrap:anywhere;word-break:break-word;padding:.12em .35em;background:var(--soft);border-radius:4px}pre{overflow:auto;background:var(--soft);border-radius:8px;padding:18px;position:relative}pre code{padding:0}.copy-btn{position:absolute;right:8px;top:8px;font-size:12px}.kw{color:var(--accent);font-weight:700}
.table-tools{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:16px 0 10px}.table-tools label{font-size:14px;color:var(--muted)}.table-tools input{flex:1;min-width:190px;padding:9px 12px;background:var(--paper);border:1px solid var(--line);border-radius:8px}.table-tools select{max-width:100%;padding:9px;background:var(--paper);border:1px solid var(--line);border-radius:8px}.table-count{font-size:13px;color:var(--muted)}.table-wrap{width:100%;max-width:100%;overflow-x:auto;border:1px solid var(--line);border-radius:8px}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.7}table.experiments{min-width:960px}table.structure{min-width:650px}th,td{padding:13px 14px;vertical-align:top;text-align:left;border-bottom:1px solid var(--line)}thead{background:var(--soft)}thead th{font-weight:700}th button{border:0;padding:0;background:transparent;text-align:left;font-weight:700}tbody tr:last-child td{border-bottom:0}tbody tr:hover{background:var(--soft)}td:first-child{font-weight:600}table.experiments td:nth-child(2){width:19%}table.experiments td:nth-child(3){width:32%}table.experiments td:nth-child(4){width:23%}td[hidden],tr[hidden]{display:none}footer{font-size:13px;color:var(--muted);padding:24px 0 50px;overflow-wrap:anywhere}
@media(max-width:1000px){.report-shell{grid-template-columns:1fr;padding:20px;gap:10px}.toc{position:relative;top:0;max-height:none;display:flex;gap:4px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:12px}.toc strong{width:100%;margin-bottom:0}.toc a{padding:4px 8px;font-size:12px;border-left:0}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.section-card{padding:22px}}
@media(max-width:520px){body{font-size:15px}.report-shell{padding:12px}.section-card{padding:18px 14px}.actions{justify-content:flex-start}.metrics{gap:8px}.metric-card{padding:14px}.metric-card strong{font-size:25px}.table-tools{display:block}.table-tools input,.table-tools select{width:100%;margin:6px 0;min-width:0}blockquote{padding:16px}.section-card details>summary,h2{font-size:21px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.no-print,.toc,.actions,.table-tools{display:none!important}:root,:root.dark{--bg:#fff;--paper:#fff;--ink:#000;--muted:#333;--line:#aaa;--accent:#000;--soft:#fff;--warning:#000;--warning-bg:#fff}body{font-size:10pt}.report-shell{display:block;padding:0;max-width:none}.section-card{border:0;padding:10px 0;border-radius:0}.metrics{grid-template-columns:repeat(4,1fr)}h1{font-size:24pt}h2,.section-card details>summary{font-size:15pt}.table-wrap{overflow:visible;border:0}table.experiments,table.structure{min-width:0;table-layout:fixed;font-size:8pt}th,td{padding:5px;overflow-wrap:anywhere}thead{display:table-header-group}tr{break-inside:avoid}tr[hidden]{display:table-row!important}.section-card details:not([open])>*:not(summary){display:block!important}a{color:#000}.status{border:1px solid #000}footer{padding-bottom:0}}
'''

JS = r'''
(()=>{
const root=document.documentElement;
const theme=document.getElementById('theme-toggle');
theme.addEventListener('click',()=>{const dark=root.classList.toggle('dark');theme.setAttribute('aria-pressed',String(dark));try{localStorage.setItem('report-theme',dark?'dark':'light')}catch(_){}});
document.getElementById('print-report').addEventListener('click',()=>window.print());
document.querySelectorAll('table[data-sortable]').forEach(table=>{
 const body=table.tBodies[0],query=document.querySelector('[data-table-filter="'+table.id+'"]'),stage=document.querySelector('[data-table-stage="'+table.id+'"]'),count=document.querySelector('[data-table-count="'+table.id+'"]');
 const filter=()=>{let n=0;const q=(query?.value||'').trim().toLocaleLowerCase('zh-CN'),s=stage?.value||'';[...body.rows].forEach(row=>{row.hidden=!(row.textContent.toLocaleLowerCase('zh-CN').includes(q)&&(!s||row.dataset.stage===s));if(!row.hidden)n++});if(count)count.textContent='显示 '+n+' / '+body.rows.length+' 条';};
 query?.addEventListener('input',filter);stage?.addEventListener('change',filter);
 table.querySelectorAll('thead button').forEach((button,i)=>{let asc=true;button.addEventListener('click',()=>{const rows=[...body.rows];rows.sort((a,b)=>a.cells[i].textContent.trim().localeCompare(b.cells[i].textContent.trim(),'zh-CN',{numeric:true})*(asc?1:-1));table.querySelectorAll('th').forEach(th=>th.removeAttribute('aria-sort'));button.closest('th').setAttribute('aria-sort',asc?'ascending':'descending');rows.forEach(row=>body.appendChild(row));asc=!asc;filter()})});filter();
});
document.querySelectorAll('pre>code').forEach(code=>{const button=document.createElement('button');button.type='button';button.className='copy-btn no-print';button.textContent='复制';button.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(code.textContent);button.textContent='已复制'}catch(_){button.textContent='请手动复制'}setTimeout(()=>button.textContent='复制',1600)});code.parentElement.appendChild(button)});
const details=[...document.querySelectorAll('details')];let openBeforePrint=[];
addEventListener('beforeprint',()=>{openBeforePrint=details.map(d=>d.open);details.forEach(d=>d.open=true)});
addEventListener('afterprint',()=>details.forEach((d,i)=>d.open=openBeforePrint[i]??d.open));
const links=[...document.querySelectorAll('.toc a')];
if('IntersectionObserver' in window){const observer=new IntersectionObserver(entries=>{entries.forEach(e=>{if(e.isIntersecting)links.forEach(a=>a.classList.toggle('active',a.hash==='#'+e.target.id))})},{rootMargin:'-5% 0px -70% 0px'});links.forEach(a=>{const el=document.getElementById(a.hash.slice(1));if(el)observer.observe(el)})}
document.querySelectorAll('.toc a').forEach(a=>a.addEventListener('click',()=>{const target=document.getElementById(a.hash.slice(1));const d=target?.querySelector('details');if(d)d.open=true}));
})();
'''


def build(md, dest):
    text = md.read_text(encoding='utf-8')
    content = BeautifulSoup(markdown.markdown(text, extensions=['tables', 'fenced_code']), 'html.parser')
    title = content.h1.get_text()
    content.h1.decompose()
    # Markdown的相对证据链接以其自身目录为基准，HTML下移一级后重新定位。
    for a in content.find_all('a', href=True):
        href = a['href']
        if not re.match(r'^[a-z]+:|^#', href):
            a['href'] = os.path.relpath((md.parent / href).resolve(), dest.parent.resolve())
    for code in content.find_all('code'):
        if code.parent.name == 'pre':
            continue
        label = code.get_text()
        candidates = [label, 'results/' + label, '.codex/mds/' + label]
        root = md.parents[2]
        match = next((root / x for x in candidates if (root / x).exists()), None)
        if match is not None:
            a = content.new_tag('a', href=os.path.relpath(match, dest.parent.resolve()))
            code.wrap(a)
    tables = content.find_all('table')
    assert len(tables) == 2 and len(tables[0].tbody.find_all('tr')) == 26
    for n, table in enumerate(tables):
        table['id'] = 'experiment-table' if n == 0 else 'structure-table'
        table['class'] = 'experiments' if n == 0 else 'structure'
        table['data-sortable'] = ''
        for th in table.thead.find_all('th'):
            button = content.new_tag('button', type='button', title='点击排序')
            for child in list(th.contents):
                button.append(child.extract())
            th.append(button)
        if n == 0:
            for i, tr in enumerate(table.tbody.find_all('tr'), 1):
                tr['data-stage'] = 'early' if i <= 8 else 'interface' if i <= 17 else 'sustained'
        wrap = content.new_tag('div', attrs={'class': 'table-wrap', 'tabindex': '0', 'role': 'region', 'aria-label': '实验索引表' if n == 0 else '六类结构证据表'})
        table.wrap(wrap)
        tools = BeautifulSoup(f'<div class="table-tools no-print"><label for="search-{n}">搜索</label><input id="search-{n}" type="search" data-table-filter="{table["id"]}" placeholder="输入模型、轮次、结果或关键词…"><span class="table-count" data-table-count="{table["id"]}" role="status" aria-live="polite"></span></div>', 'html.parser').div
        if n == 0:
            select = BeautifulSoup(f'<select data-table-stage="{table["id"]}" aria-label="按研究阶段筛选"><option value="">全部26轮</option><option value="early">01–08：早期开发</option><option value="interface">09–17：接口与参照</option><option value="sustained">18–26：持续活动</option></select>', 'html.parser').find('select')
            tools.insert(2, select)
        wrap.insert_before(tools)
    chunks = []
    current = []
    headings = []
    for child in list(content.children):
        if getattr(child, 'name', None) == 'h2':
            if current:
                chunks.append(current)
            current = [child]
        else:
            current.append(child)
    if current:
        chunks.append(current)
    sections = []
    intro = ''
    for chunk in chunks:
        heading = next((x for x in chunk if getattr(x, 'name', None) == 'h2'), None)
        if heading is None:
            intro += ''.join(map(str, chunk))
            continue
        i = len(headings) + 1
        label = heading.get_text()
        headings.append((f'section-{i}', label))
        body = ''.join(str(x) for x in chunk if x is not heading)
        if label in ('原始六类结构目前覆盖到哪里', '验证情况与产物', '风险、结论边界与后续建议'):
            section = f'<details open><summary>{html.escape(label)}</summary>{body}</details>'
        else:
            section = str(heading) + body
        sections.append(f'<section class="section-card" id="section-{i}">{section}</section>')
    template = (SKILL / 'assets/html-report-template.html').read_text()
    head = template.split('<body', 1)[0]
    head = re.sub(r'<script\b[^>]*>.*?</script>', '', head, flags=re.S)
    head = re.sub(r'<link\b[^>]*>', '', head)
    head = re.sub(r'<style>.*?</style>', '<style>' + CSS + '</style>', head, flags=re.S)
    description = '截至2026年10月3日16:54的第1–26轮实验快照；当前批次仍运行，终止不等于任务成功。'
    head = head.replace('{{REPORT_TITLE}}', html.escape(title)).replace('{{REPORT_DESCRIPTION}}', html.escape(description))
    initialization = '''<script>try{if(localStorage.getItem('report-theme')==='dark'||(!localStorage.getItem('report-theme')&&matchMedia('(prefers-color-scheme:dark)').matches))document.documentElement.classList.add('dark')}catch(_){}</script>'''
    head = head.replace('</head>', initialization + '</head>')
    toc = ''.join(f'<a href="#{key}">{html.escape(label)}</a>' for key, label in headings)
    digest = hashlib.sha256(md.read_bytes()).hexdigest()
    cards = [('已归档轮次', '25轮', '第26轮继续执行'), ('已终止回合', '38 / 80', '16局部 + 22完整；非成功数'), ('局部审计', '16 / 16', '安全成功14；全部安全16'), ('完整阶段审计', '8 / 64', '任务0；安全5；非全量成绩')]
    metrics = ''.join(f'<div class="metric-card"><small>{a}</small><strong>{b}</strong><small>{c}</small></div>' for a, b, c in cards)
    document = head + f'''<body>
<div class="report-shell"><nav class="toc no-print" aria-label="报告目录"><strong>报告目录</strong>{toc}</nav><main>
<div class="actions no-print"><a href="../{html.escape(md.name)}" download>下载配套Markdown</a><button id="theme-toggle" type="button" aria-pressed="false">切换明暗</button><button id="print-report" type="button">打印 / 存为PDF</button></div>
<header><span class="status">阶段快照 · 当前实验进行中</span><p class="eyebrow">HRC-Bench · 2026年10月3日16:54（北京时间）</p><h1>{html.escape(title)}</h1></header>
{intro}<div class="metrics" aria-label="固定快照摘要">{metrics}</div>{''.join(sections)}
<footer>正文完整来自配套Markdown；页面基于markdown-work-report模板生成，无外部脚本、字体或网络依赖。<br>正文SHA256：<code>{digest}</code></footer>
</main></div><script>{JS}</script></body></html>'''
    assert '{{' not in document
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(document, encoding='utf-8')
    print(dest)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('markdown', type=Path)
    p.add_argument('html', type=Path)
    args = p.parse_args()
    build(args.markdown.resolve(), args.html.resolve())
