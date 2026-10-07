"""核验正式报告的视频播放、拖动、同步和移动端布局。使用既有本地Chromium。"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent
URL='http://127.0.0.1:8123/experiments/interaction_learning_20261007/index.html'
OUTPUT=Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/interaction_contact_lora_train_20261007/report_browser')


def main():
    OUTPUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--disable-gpu'])
        page=browser.new_page(viewport={'width':1280,'height':900});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        assert page.goto(URL).status==200
        videos=[];sources=page.locator('video').evaluate_all('(vs)=>vs.map(v=>({src:v.src,id:v.id}))')
        assert len(sources)==15
        for index,entry in enumerate(sources):
            v=page.locator('video').nth(index)
            v.evaluate('(v)=>v.closest("details") && (v.closest("details").open=true)')
            v.evaluate('(v)=>{v.muted=true;v.load()}')
            page.wait_for_function('(i)=>document.querySelectorAll("video")[i].readyState>=2',arg=index)
            v.evaluate('(v)=>v.play()')
            page.wait_for_function('(i)=>document.querySelectorAll("video")[i].currentTime>.2',arg=index)
            v.evaluate('(v)=>{v.pause();v.currentTime=37.2}')
            page.wait_for_function('(i)=>Math.abs(document.querySelectorAll("video")[i].currentTime-37.2)<.15 && !document.querySelectorAll("video")[i].seeking && document.querySelectorAll("video")[i].readyState>=2',arg=index)
            duration=v.evaluate('(v)=>v.duration')
            assert duration>=60
            if entry['id']:
                expected='33.20' if entry['id']=='qualification' else '37.20'
                page.wait_for_function('({id,t})=>document.getElementById("state-"+id).textContent.includes("模拟 "+t+"秒")',arg={'id':entry['id'],'t':expected})
            range_response=page.request.get(entry['src'],headers={'Range':'bytes=0-1023'})
            assert range_response.status==206 and len(range_response.body())==1024
            videos.append({'id':entry['id'] or f'teacher_{index}','duration_s':duration,
                'played':True,'seek_37_2_s':True,'nn_state_sync':bool(entry['id']),'range_status':206})
        links=page.locator('a[href]').evaluate_all('(as)=>as.map(a=>a.href)')
        for link in set(links):
            if link.startswith('http://127.0.0.1:8123/'):
                assert page.request.get(link).status==200,link
        page.screenshot(path=str(OUTPUT/'desktop.png'),full_page=True)
        page.set_viewport_size({'width':375,'height':812})
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
        page.screenshot(path=str(OUTPUT/'mobile.png'),full_page=True)
        assert not errors
        browser.close()
    result={'status':'verified','videos':videos,'local_links_checked':len(set(links)),
        'javascript_errors':errors,'mobile_no_horizontal_overflow':True}
    (HERE/'report_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
