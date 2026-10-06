# 动态人类与真实接触阶段报告

打开 [index.html](index.html)，可查看实验目的、设置、合法贡献归属、四条真实
Sim 视频和人体跳变核查。该页包含实际运行结果，三条联合运行因人体动作不连续
仅作诊断；研究目标尚未完成。

`build_report.py` 读取数据盘软链接中的原始结果生成 HTML 与 `evidence.json`，
不会运行模型、仿真或改写评分：

```bash
python experiments/dynamic_contact_20261006/build_report.py
```

浏览器核查与截图独立生成；重建页面后需要重新核查。
