#!/usr/bin/env python3
"""说明单次真实接口检查及其边界，不展示未执行动作或新Sim视频。"""
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path


if __name__=='__main__':
    root=Path('results/bounded_human_interface_20261009')
    output=Path('experiments/bounded_human_interface_20261009')
    result=json.loads((root/'result.json').read_text());verification=json.loads((root/'verification.json').read_text())
    if verification['status']!='source_and_actual_token_records_verified':raise ValueError('实际token未核对')
    if verification['result_sha256']!=sha256((root/'result.json').read_bytes()).hexdigest():raise ValueError('接口结果已变化')
    if verification['provenance_sha256']!=sha256((root/'provenance.json').read_bytes()).hexdigest():raise ValueError('来源记录已变化')
    provenance=json.loads((root/'provenance.json').read_text())
    choice=result['choice'] or {}
    def link(path,label):return '<a href="'+escape(os.path.relpath(path,output),quote=True)+'">'+escape(label)+'</a>'
    body='<section><h2>为什么做这次检查</h2><p>原饮品实验36秒时，人的意图已转向柜顶立即取用，但贡献层不断重复公开消息，4096个输出token耗尽后JSON仍未结束，纠正未送达。该问题会妨碍真实动态伙伴的测试，需要先验证工具输出能否完整生成。</p><p>本次重放同一保存状态与已生成的私人意图，用Qwen3-32B-AWQ实际生成一次贡献。公开消息和理由上限512字符；意图256、参与128、记忆256。动作、对象及目标选项保持。使用新seed14136及新的工具声明。</p></section>'
    body+='<section><h2>实际结果</h2><p>完整JSON解析'+('通过' if result['parse_error'] is None else '失败：'+escape(result['parse_error']))+'；实际输出'+str(len(result['whole_generated_token_ids']))+'token；生成墙钟'+f'{result["latency_wall_s"]:.2f}'+'秒，模型加载另计'+f'{result["model_load_wall_s"]:.2f}'+'秒。没有强制关闭原生思考。</p>'
    body+='<table><tr><th>人自己的选定贡献</th><th>公开话语</th></tr><tr><td>'+escape(str(choice.get('action','未解析'))+'：'+str(choice.get('object_id',''))+' → '+str(choice.get('destination','')))+'</td><td>'+escape(choice.get('message',''))+'</td></tr></table>'
    body+='<p>选择与话语围绕柜顶立即取用，比原失败输出更完整；仍同时表达自己搬运与请求Robot放置。是否形成有效分工、是否重复操作，需要完整Sim行为证据，不能由解析通过判定。</p></section>'
    body+='<section><h2>与完整Benchmark的关系</h2><p>这是一个贡献层接口样本，继承原方法的意图和过去轨迹。它没有运行新的Sim动作，也没有验证新方法自己的持续历史。单次不同采样与工具声明变化不足以证明因果改善、稳定伙伴或cobalance。正式样本0。</p><p>原三活动批继续原协议；重要Sim实验在完整运行与视频核查后发布。下一步需要在同一世界内验证新的输出协议如何连接动态意图、公开纠正和实际协作。</p><p>'
    body+=link(Path('experiments/candidate_joint_20261009/index.html'),'原三活动的真实Sim报告')+' · '+link(Path('results/candidate_joint_prefix_20261009/drink_correction_delivery_44s.json'),'原失败与公开纠正的来源快照')+'</p></section>'
    body+='<section><h2>来源与复现</h2><p><a href="PROTOCOL.md">设置、信息边界与命令</a> · '+link(root/'result.json','真实模型输入输出与token')+' · '+link(root/'verification.json','独立来源与token核查')+' · '+link(root/'provenance.json','冻结模型、采样与源代码')+'</p><p>输入运行：'+escape(provenance['input_run'])+'，36模拟秒的保存输入；本检查的生成时间为墙钟时间。</p></section>'
    page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>有限文本协议：一次真实模型接口检查</title><style>body{margin:0;background:#edf1f5;color:#182536;font:16px/1.7 system-ui;overflow-wrap:anywhere}main{max-width:1000px;margin:auto;padding:24px}section{background:white;border-radius:12px;padding:22px;margin:18px 0}table{width:100%;border-collapse:collapse;table-layout:fixed}th,td{padding:10px;border:1px solid #d6dde5;text-align:left;vertical-align:top}a{color:#155aa7}@media(max-width:500px){main{padding:10px}section{padding:15px}}</style><main><h1>有限文本协议：一次真实模型接口检查</h1>'+body+'</main></html>'
    (output/'index.html').write_text(page)
    print(json.dumps({'verified_neural_samples':1,'sim_episodes':0,'formal_samples':0}))
