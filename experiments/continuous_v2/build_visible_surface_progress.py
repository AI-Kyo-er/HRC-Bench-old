"""从已完成且视频可解码的采集产物生成进度页，不运行仿真或重新评分。"""
from datetime import datetime
from html import escape
import json
from pathlib import Path

from hrc_pilot.video_verification import verify_episode


ROOT = Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/visible_surface_demonstrations')


def main():
    cache_path = ROOT / 'live_video_verification.json'
    cached = json.loads(cache_path.read_text()).get('episodes', []) if cache_path.exists() else []
    checked = {row['episode']: row for row in cached if row['status'] == 'verified'}
    metrics = []
    for path in sorted(ROOT.rglob('metrics.json')):
        try:
            metric = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        episode = path.parent.relative_to(ROOT).as_posix()
        if episode not in checked:
            result = verify_episode(path.parent, ROOT, require_timeline=True)
            if result['status'] != 'verified':
                continue
            checked[episode] = result
        metrics.append((episode, metric))
    successes = sum(row['task_success'] for _, row in metrics)
    all_rows = ''.join(f'<tr><td><a href="{escape(episode)}/demo.mp4">{escape(episode)}</a></td><td>{"完成" if row["task_success"] else "未完成"}</td><td>{row["completion_time_s"]:.1f} 秒</td></tr>'
                       for episode, row in metrics)
    selected = {}
    for episode, row in metrics:
        color = row['scenario'].split('_')[1]
        if color not in selected or row['task_success']:
            selected[color] = (episode, row)
    videos = ''.join(f'<article><h2>{escape(color)} · {escape(row["scenario"])}</h2><p>几何教师真实接触操作；{"完成" if row["task_success"] else "未完成"}。</p><video controls preload="metadata" src="{escape(episode)}/demo.mp4"></video></article>'
                     for color, (episode, row) in selected.items())
    stamp = datetime.now().astimezone().isoformat(timespec='seconds')
    document = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>可见目标区域 · 实际示范采集进度</title><style>body{{margin:auto;max-width:1000px;padding:24px;background:#f1f5f4;color:#182e3e;font-family:system-ui;line-height:1.8;overflow-wrap:anywhere}}article{{padding:20px;background:white;margin:20px 0;border-radius:12px}}video{{width:100%;background:#142430}}table{{width:100%;border-collapse:collapse}}td{{padding:10px;border-bottom:1px solid #ccd8d5}}a{{color:#126b70}}</style>
<h1>可见区域与独立布局的实际示范</h1><p>已核验完成 {len(metrics)}/96 条，实际操作完成 {successes} 条。采集仍在进行，这不是正式数据集总成绩。</p>
<p>蓝色底板表示收纳，绿色底板表示留用。显示范围与评分共用同一几何定义，要求物体完整足迹在区域内，并实际释放、支撑和稳定。
各物体初始位置独立变化且彼此分离；控制来自几何数据教师，没有吸附或控制期坐标搬运。本页用于检查场景和示范质量，不是学习模型或HRC成绩。</p>
<p>未完成运行保留视频，但不导出有效监督。有效样本按输入stem配对双相机、本体状态与速度/实际位置目标，不使用配对manifest。</p>
{videos}<h2>已核验运行</h2><table>{all_rows}</table><p>进度快照：{stamp}。完整批次完成后由采集程序生成正式index.html及严格视频核验。</p></html>'''
    (ROOT / 'progress.html').write_text(document)
    cache_path.write_text(json.dumps({'status':'partial_verified_snapshot','checked_at':stamp,
                                     'episodes':list(checked.values()),'completed_count':len(metrics)},ensure_ascii=False,indent=2))
    print(f'实时快照：{len(metrics)}/96，成功{successes}，真实视频全部核验')


if __name__ == '__main__':
    main()
