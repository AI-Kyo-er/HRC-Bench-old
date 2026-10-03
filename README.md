# Human-robot Progressively Rebalanced Collaboration Benchmark

当前实现是 **VC + 配套 Genesis 分支的第一版具身 pilot demo**。一名带动画的模拟人与一台 Franka 机械臂在桌面工作空间中整理两个杯子，测试交互历史、理解更新和伙伴可用性如何影响后续合作。

研究对象是共同活动如何在指导、协作和干预交织时被重新组织。时长和模式切换次数不是第一版的主要变量；理解更新也可以发生在物体和人体动作尚未改变时。

- [实验设计、接口与运行说明](experiments/pilot_v1/README.md)
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
