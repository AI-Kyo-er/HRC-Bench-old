"""展示保存状态上的接口记录，不把候选选择称为真实执行。"""
from html import escape
import json
from pathlib import Path


def build():
    output=Path('experiments/human_candidate_interface_20261009');root=Path('results/human_candidate_interface_20261009')
    verification=json.loads((root/'interface_verification.json').read_text())
    if verification['status']!='source_and_token_records_verified':raise ValueError('先核对实际来源与token')
    cards=[]
    for item in verification['decisions']:
        record=json.loads((root/(item['stem']+'.json')).read_text());decision=record['candidate_decision']
        source=record['condition']['source_run'];t=record['condition']['time_s']
        cards.append('<section><h2>'+escape(source+' · '+t+'模拟秒')+'</h2><p>候选私人需要：'+escape(decision['private_agenda_inference']['agenda_after']['current_need'])+'</p><p>选择：'+escape(json.dumps(decision['choice'],ensure_ascii=False))+'</p><p>此选择尚未执行；推理墙钟 '+str(round(decision['latency_s'],2))+' 秒。</p><p><a href="../../results/continuous_v2/'+source+'/index.html">原Sim场景与来源视频</a> · <a href="../../results/human_candidate_interface_20261009/'+item['stem']+'.json">实际输入、生成与token记录</a></p></section>')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>更大人策略候选：保存状态接口检查</title><style>body{font:16px/1.7 system-ui;background:#eef2f5;color:#182536;margin:0;overflow-wrap:anywhere}main{max-width:1000px;margin:auto;padding:24px}section{background:white;border-radius:12px;padding:20px;margin:16px 0}a{color:#155aa7}@media(max-width:500px){main{padding:10px}section{padding:15px}}</style><main><h1>更大人策略候选：保存状态接口检查</h1><section><p>三帧真实来源、两阶段生成与工具调用的输入/token已独立核对。历史选择与主观记忆来自原Qwen3-14B，不是候选自己的连续轨迹。只在保存状态上调用候选，没有新Sim动作、协作分数或正式样本。</p><p>点心帧仍提前说已入碗；饮品帧选择清Plate且撤回Rack确认；抽屉帧选择等待确认。前者是未解决的事实表达问题，后两项也不能用未执行选择证明效果。更大模型尚未取得伙伴资格，下一步需要真实闭环。</p><p><a href="PROTOCOL.md">运行前目的与条件</a> · <a href="conditions.csv">三帧条件</a> · <a href="../../results/human_candidate_interface_20261009/interface_verification.json">来源与token核查（不认证语义）</a> · <a href="../area_feedback_20261009/index.html">三活动完整Sim报告</a></p></section>'''+''.join(cards)+'</main></html>'
    (output/'index.html').write_text(page)
    print('已发布三帧接口记录，正式样本0、新Sim行为0')


if __name__=='__main__':build()
