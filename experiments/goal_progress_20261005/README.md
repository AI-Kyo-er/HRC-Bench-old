# Goal 进展总报告

浏览器打开 [index.html](index.html)。页面按研究推进顺序介绍 12 个阶段，并提供已有 HTML、真实 Genesis 视频、观察、动作、轨迹、事件与实现文件的链接。

这是截至生成时的结果快照。本次只整理既有记录，没有运行模型、仿真、训练或修改主实验实现。旧版本和复用前缀不作为独立样本累计；评分使用各目录当时的 `task_success`。

- [evidence.json](evidence.json)：目录清单、来源代码提交和已读取汇总/复核记录的 SHA256。
- [report_verification.json](report_verification.json)：本页链接、筛选、视频元数据、移动布局和浏览器错误检查。
- [preview-desktop.png](preview-desktop.png)、[preview-mobile.png](preview-mobile.png)：页面预览。

仅更新本目录的页面和快照：

```bash
python experiments/goal_progress_20261005/build_report.py
```

重新生成后应重新核查页面；已有 `report_verification.json` 与截图不会自动更新。静态页面无 CDN 或网络字体，视频、日志与代码通过仓库内相对链接引用，需保留 `results/` 指向数据盘的软链接。

报告明确区分：规则协作机制、真实 VLA 动作闭环、尚未完成的联合 HRC 验证；真实渲染与运动学吸附不等于真实接触抓取。
