# Human-robot Progressively Rebalanced Collaboration Benchmark

当前仓库同时包含 **VC + 配套 Genesis 的 v1 具身 pilot** 和 **HRC-Continuous v2 持续协作运行时**。v2 将人和机器人放在同一时间轴内逐 tick 推进，用可组合场景、动作块和公开观测测试合作如何随双方行为变化而重新组织。

研究对象是共同活动如何在指导、协作和干预交织时被重新组织。时长和模式切换次数不是第一版的主要变量；理解更新也可以发生在物体和人体动作尚未改变时。

- [实验设计、接口与运行说明](experiments/pilot_v1/README.md)
- [持续运行时、六类场景与当前边界](experiments/continuous_v2/README.md)
- [v2 实验设计与数据契约](experiments/continuous_v2/design.md)
- [已经生成的正式展示页](results/pilot_v1/formal/index.html)
- [运行脚本](scripts/run_pilot_demo.sh)

所有环境、第三方仓库、资产、缓存和结果实际存储在 `/data1/sieniwgroup/sieniw/projects/HRC-Bench/`，通过软链接访问。此前的 `legacy_llm_direction` 内容保留归档状态。

## 运行

在仓库根目录执行：

```bash
bash scripts/setup_vc_pilot.sh
bash scripts/run_pilot_demo.sh
```

运行前程序使用 `nvidia-smi` 检查所选 GPU 的空闲显存。启动脚本指定 GPU 0；若该卡不足 4 GB，程序会停止并说明原因。需要切换 GPU 时修改脚本中的 `CUDA_VISIBLE_DEVICES`。首次运行包括内核编译，耗时比后续运行长。

默认脚本输出到 `results/pilot_v1/demo/`，已完成的验证结果在 `results/pilot_v1/formal/`。程序拒绝覆盖非空输出目录；重复运行请在启动脚本中设置新的输出路径。

这是一版**机制与工程验证**：使用手写策略、仿真语义几何观测和运动学抓取抽象。它尚未评测训练后的基础模型，也不验证接触力、真实抓握、人体安全或真人协作效果。

v2 的参考运行可直接生成 HTML 报告：

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/formal
```

这次 v2 报告验证的是连续协议、动态伙伴和独立记录逻辑；它使用 `ContinuousWorld` 参考后端，不把参考伙伴的成功率当作模型结果。`continuous_genesis.py` 和 `VCWorkspace` 已提供逐 tick Genesis 接缝，完整六场景 Genesis 资产、真实 VLA/WLA 推理和接触安全评测仍需后续实现。

v2 不是把更多分支写进固定状态机：`generate_scenarios` 生成可改变布局、分工和伙伴条件的任务实例，伙伴根据公开进度和当前占用响应，策略通过 `ModelPolicy` 接入 VLA/WLA。每个 episode 产生可按目录和稳定文件名配对的 `scenario.json`、公开观测、策略输入输出、轨迹、事件和独立指标；当前 `GreedyPublicPolicy` 只是协议基线，Genesis 仍需完成真实接触动力学和完整场景验证后，才能用于先进模型的正式排行榜。

可以用 `--suite` 生成 isolated、matched_serial、compositional 和 held_out 结构条件，并用 `--partner-mode fixed_replay|reactive|adaptive` 做伙伴信息边界对照。held-out 的依赖关系写在每个 episode 的 `scenario.json` 中，不依赖 `manifest.json`。
