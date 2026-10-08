#!/usr/bin/env python3
"""检查真实Sim报告链接、手机布局、视频加载／播放／拖动及HTTP Range。"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def verify(url, output):
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':375,'height':812});page.set_default_timeout(20000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(url)
        if page.evaluate('document.documentElement.scrollWidth')>375:raise ValueError('手机页面水平溢出')
        links=page.locator('a').evaluate_all('(xs)=>xs.map(x=>x.href)')
        broken=[link for link in links if not page.request.get(link).ok]
        if broken:raise ValueError('失效链接：'+str(broken))
        graphics=page.locator('img').all()
        for graphic in graphics:
            graphic.scroll_into_view_if_needed()
            page.wait_for_function('(g)=>g.complete&&g.naturalWidth>0',arg=graphic.element_handle())
        videos=page.locator('video').all();checks=[]
        for video in videos:
            video.scroll_into_view_if_needed()
            video.evaluate('(v)=>{v.preload="auto";v.load()}')
            handle=video.element_handle()
            page.wait_for_function('(v)=>v.readyState>=2',arg=handle)
            duration=video.evaluate('(v)=>v.duration')
            seek=min(31,duration/2)
            video.evaluate('(v,t)=>{v.currentTime=t}',seek)
            page.wait_for_function('([v,t])=>Math.abs(v.currentTime-t)<.1&&!v.seeking',arg=[handle,seek])
            video.evaluate('(v)=>v.play()');page.wait_for_timeout(350)
            if video.evaluate('(v)=>v.currentTime')<=seek:raise ValueError('视频未实际播放')
            video.evaluate('(v)=>v.pause()')
            src=video.evaluate('(v)=>v.src')
            response=page.request.get(src,headers={'Range':'bytes=0-99'})
            if response.status!=206 or len(response.body())!=100:raise ValueError('视频Range失败')
            caption_check=None
            if video.locator('track').count():
                video.evaluate('(v)=>{v.textTracks[0].mode="showing"}')
                page.wait_for_function('(v)=>v.textTracks[0].activeCues&&v.textTracks[0].activeCues.length>0',arg=handle)
                track=video.locator('track').first
                caption_response=page.request.get(track.evaluate('(t)=>t.src'))
                if not caption_response.ok or not caption_response.text().startswith('WEBVTT'):
                    raise ValueError('研究字幕无法加载')
                caption_check={'active_at_seek_s':seek,'showing':True,'webvtt_loaded':True}
            inspection_check=None
            panel=video.locator('xpath=ancestor::section').locator('.episode-inspector')
            if panel.count():
                panel_handle=panel.element_handle()
                page.wait_for_function('(p)=>p.dataset.inspectionState==="ready"',arg=panel_handle)
                inspection_url=panel.evaluate('(p)=>new URL(p.dataset.inspection,document.baseURI).href')
                inspection=page.request.get(inspection_url).json()
                selector=panel.locator('.inspection-seek')
                options=selector.locator('option').count()
                if not options:raise ValueError('审阅视图没有可定位的决策')
                selector.select_option(index=options//2)
                target=float(selector.input_value())
                page.wait_for_function('([v,t])=>Math.abs(v.currentTime-t)<.1&&!v.seeking',arg=[handle,target])
                expected=next(row for row in reversed(inspection['video_frames']) if row['video_time_s']<=target)
                page.wait_for_function('([p,t])=>Math.abs(Number(p.dataset.benchmarkTime)-t)<1e-6',
                                       arg=[panel_handle,expected['benchmark_time_s']])
                human=inspection['human_decisions'][expected['human_decision_row']]
                need=(human.get('private_agenda') or {}).get('current_need','本方法未记录私人需要')
                if panel.locator('[data-view="human-need"]').inner_text()!=need:
                    raise ValueError('视频所显示的私人需要与对应时刻实际记录不符')
                if page.evaluate('document.documentElement.scrollWidth')>375:
                    raise ValueError('加载审阅视图后手机页面水平溢出')
                inspection_check={'video_seek_s':target,'benchmark_time_s':expected['benchmark_time_s'],
                                  'decision_selector_worked':True,'need_matches_saved_record':True}
            checks.append({'src':src,'duration_s':duration,'play_seek_passed':True,'range_status':206,
                           'research_caption':caption_check,'research_inspection':inspection_check})
        if errors:raise ValueError('页面JS错误：'+str(errors))
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps({'status':'verified','videos':len(videos),'links_checked':len(links),
             'loaded_figures':len(graphics),
             'mobile_width':375,'javascript_errors':errors,'video_checks':checks},ensure_ascii=False,indent=2))
        browser.close();print(f'verified {len(videos)} videos and {len(links)} links')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8123/experiments/joint_feasibility_20261007/index.html')
    parser.add_argument('--output',type=Path,default=Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/joint_report_browser_20261008/verification_final.json'))
    args=parser.parse_args();verify(args.url,args.output)
