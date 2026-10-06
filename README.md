# Human-robot Progressively Rebalanced Collaboration Benchmark

当前仓库同时包含 **VC + 配套 Genesis 的 v1 具身 pilot** 和 **HRC-Continuous v2 持续协作运行时**。v2 将人和机器人放在同一时间轴内逐 tick 推进，用可组合场景、动作块和公开观测测试合作如何随双方行为变化而重新组织。

研究对象是共同活动如何在指导、协作和干预交织时被重新组织。时长和模式切换次数不是第一版的主要变量；理解更新也可以发生在物体和人体动作尚未改变时。

- [实验设计、接口与运行说明](experiments/pilot_v1/README.md)
- [持续运行时、六类场景与当前边界](experiments/continuous_v2/README.md)
- [v2 实验设计与数据契约](experiments/continuous_v2/design.md)
- [已经生成的正式展示页](results/pilot_v1/formal/index.html)
- [v2 六场景报告与轨迹动画](results/continuous_v2/formal_v6/index.html)
- [v2 三种伙伴配对报告与轨迹动画](results/continuous_v2/paired_v8/index.html)
- [v2 Genesis 六场景报告（含真实 Sim 视频）](results/continuous_v2/genesis_v10/index.html)
- [v2 Genesis 三种伙伴条件报告（18 个 episode，含真实 Sim 视频）](results/continuous_v2/genesis_paired_v10/index.html)
- [v2 九类任务族动态伙伴正式报告（9 条真实 Sim 视频、9/9 时间轴核验）](results/continuous_v2/task_catalog_genesis_v2/index.html)
- [历史反事实 Genesis 报告（含真实 Sim 视频）](results/continuous_v2/history_counterfactual_genesis_v1/index.html)
- [v2 Genesis 验证记录](experiments/continuous_v2/genesis_validation.md)
- [运行脚本](scripts/run_pilot_demo.sh)

所有环境、第三方仓库、资产、缓存和结果实际存储在 `/data1/sieniwgroup/sieniw/projects/HRC-Bench/`，通过软链接访问。此前的 `legacy_llm_direction` 内容保留归档状态。

日常查看和运行使用仓库内的 `results/pilot_v1/`、`results/continuous_v2/`。
它们是指向数据盘对应目录的软链接，报告、动画及原始记录都从这些入口访问。
新工作区若缺少 v2 入口，可在仓库根目录执行：

```bash
ln -s /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2 results/continuous_v2
```

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
  --output-dir results/continuous_v2/formal
```

这次 v2 报告验证的是连续协议、动态伙伴和独立记录逻辑；参考报告使用
`ContinuousWorld`，Genesis 报告使用 VC/Genesis 逐 tick 后端。两者都不把手写
伙伴或 `GreedyPublicPolicy` 的成功率当作模型结果；Genesis 仍采用运动学夹持和
 Avatar 拿放抽象，真实接触安全、训练后的 VLA/WLA 推理和真人协作仍需后续实现。

重要 Genesis 实验的正式报告以运行时非空 `demo.mp4` 作为产物门槛，并在
`replay_verification.json` 中记录视频覆盖率。新运行还保存 `video_timeline.json`，
用于把真实 Sim 视频与 benchmark 时间和事件逐帧联动；旧快照若只有视频仍可播放，
但会明确标出缺少时间轴。`ContinuousWorld` 是参考后端，不要求真实 Sim 视频。

正式实验结束后还必须独立执行真实视频核验，确认 MP4 能完整解码、帧数 / FPS / 尺寸
有效。新运行应同时保存逐帧时间轴，以便把视频和事件精确对齐：

```bash
PYTHONPATH=src .venv-vc-pilot/bin/python scripts/verify_genesis_videos.py \
  --input-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/my_genesis_run
```

命令在结果根目录写入 `video_verification.json`，任一 episode 缺视频、无法解码或
时间轴不一致都会以失败退出；旧运行缺少时间轴时会标记警告但仍核验视频本身。
需要把时间轴缺失也作为正式门槛时，加上 `--require-timeline`。HTML 报告将真实 Sim
视频放在轨迹画布之前，并显示每条 episode 的核验状态；轨迹画布仍用于逐 tick 事件
审计，不能代替 Sim 视频。

需要把某次运行作为重要实验时，显式使用 `--experiment-tier important`（或快捷选项
`--important`）。该等级只允许 `--backend genesis`，并把每个 episode 的运行时
`demo.mp4` 作为报告生成门槛；参考后端适合快速探索，不会被误当成重要实验的视觉证据：

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --output-dir results/continuous_v2/important_demo \
  --backend genesis --experiment-tier important --suite --count-per-condition 1
```

重要实验默认在任务结束后继续录制 `1.5` 秒，并让每个搬运阶段至少持续
`0.2` 秒，避免成功动作在视频中瞬间消失。需要调整时可使用
`--video-settle-seconds` 和 `--minimum-transfer-phase-seconds`；这些值会写入
`provenance.json`，便于复现实验。

v2 不是把更多分支写进固定状态机：`generate_scenarios` 生成可改变布局、分工和伙伴条件的任务实例，伙伴根据公开进度和当前占用响应，策略通过 `ExternalPolicyAdapter` 接入 VLA/WLA。每个 episode 产生可按目录和稳定文件名配对的 `scenario.json`、公开观测、策略输入输出、轨迹、事件和独立指标；当前 `GreedyPublicPolicy` 只是协议基线，Genesis 仍需完成真实接触动力学和完整场景验证后，才能用于先进模型的正式排行榜。

可以先生成一个按 `train/dev/test` 结构划分的数据集，再用同一批场景批量评测模型：

```bash
PYTHONPATH=src python scripts/run_hrc_dataset.py generate \
  --output /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/continuous_v1 \
  --count-per-condition 10 --repeats 3

PYTHONPATH=src python scripts/run_hrc_dataset.py evaluate \
  --dataset /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/continuous_v1 \
  --output /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v1/my_model \
  --policy my_adapter:make_policy --split test
```

Dataset 生成和评测也可选择 Genesis 后端：

```bash
PYTHONPATH=src python scripts/run_hrc_dataset.py generate \
  --output /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/continuous_genesis \
  --count-per-condition 1 --backend genesis
```

数据集 CLI 在 Genesis（尤其是 `--experiment-tier important`）运行结束后，会自动先解码
每个 episode 的 `demo.mp4`、严格核对 `video_timeline.json`，再生成 `index.html`；核验结果
保存在运行根目录的 `video_verification.json`。任一视频缺失、为空、无法解码或时间轴不一致，
命令会失败并不生成通过状态的报告。这样批量数据集评测和单次 benchmark 使用同一条真实 Sim
视频门槛。

正式扩展基准也可以直接生成九类任务族；`--task-catalog` 会让数据集入口和
连续运行器使用同一套任务定义，每个 episode 仍按稳定的 split/family/name 路径保存：

```bash
PYTHONPATH=src python scripts/run_hrc_dataset.py generate \
  --output /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/continuous_catalog \
  --task-catalog --count-per-family 5 --repeats 3 --partner-mode dynamic
```

也可以用 `--scenario-dir path/to/scenarios` 把自定义的 JSON 活动契约目录直接
生成成同样的数据集；每个文件声明对象、区域、工作项和前置关系，不需要固定事件脚本。

`my_adapter:make_policy` 工厂可以返回实现 `reset()`/`act(observation)` 的策略，或返回用 `ExternalPolicyAdapter` 包装的 `predict(public_observation)` 模型。VLA/WLA 只收到公开 observation，不能读取 `scenario.json` 中的目标和伙伴潜变量；每次调用的动作校验、耗时、原始输出和异常会写入 `policy_io.jsonl`。批量结果会按结构划分、条件、伙伴和策略聚合任务成功、恢复时间、重新分工、冲突率、cobalance 代理指标以及人类信任/依赖变化，并报告多 seed 的 bootstrap 95% 区间。

可以用 `--suite` 生成 isolated、matched_serial、compositional 和 held_out 结构条件，并用 `--partner-mode fixed_replay|reactive|adaptive` 做伙伴信息边界对照。held-out 的依赖关系写在每个 episode 的 `scenario.json` 中，不依赖 `manifest.json`。

要在完全相同的场景实例和 seed 上配对三种伙伴条件，可运行：

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --output-dir results/continuous_v2/paired \
  --suite --count-per-condition 5 --paired
```

运行时会在动作启动后在线采样场景动力学中的延迟或失败；公开的 `action_delayed`、`action_failed`、`reassignment` 等消息会进入下一轮模型决策。这样可以测量机器人是否能承认未完成、求助并与伙伴重新分工，而不依赖固定的第 N 步脚本。
