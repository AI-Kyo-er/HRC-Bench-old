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
- [真实接触、生成式伙伴与模型适配进展（2026-10-06，含真实 Sim 视频）](experiments/dynamic_contact_20261006/index.html)
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

连续 benchmark、原生 OpenPI、恢复、关节校准、历史诊断和 Dataset 的 Genesis
入口都会在生成 HTML 前自动逐 episode 解码视频，严格核对帧数、FPS、尺寸与时间轴。
核验失败会保存失败详情并阻止生成正式报告。也可以独立复核已经保存的结果：

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

2026-10-06 新增 `--robot-grasp-model friction_contact`，原生模型入口默认采用它：机器人只能提交底层
关节动作，操作对象为受重力和碰撞影响的自由刚体；双指摩擦抓取与稳定释放由实际
物理状态核查。保存 `contacts.jsonl`、`robot_control.jsonl`、`physics_contract.json`
和 `motion_verification.json`。人体选项 `--human-manipulation-model auto` 在该后端使用
`articulated_contact_hand`，以关节受力完成持握与释放；人物显示采用动作数据和躯干 IK。
可显式选择旧 `avatar_kinematic_attachment` 执行器复盘历史。新的接触手已通过连续性
与显示手腕对齐检查，仍是简化代理，不能宣称完整人体动力学或真人效度。
三类 π0.5 + Qwen 实测、基础操作 Dataset 和执行边界均已保存；
具体设置、视频、贡献归属与未完成项见[本阶段报告](experiments/dynamic_contact_20261006/index.html)。

原生 OpenPI 入口现在支持 `--scenes`、`--task-catalog`、`--scenario-dir` 与 `--seeds`，
并可使用本地 Qwen 生成式伙伴。使用已有本地权重时可复现以下诊断：

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  .venv-vc-pilot/bin/python scripts/run_openpi_benchmark.py \
  --robot-grasp-model friction_contact --partner-mode qwen_llm \
  --human-persona cooperative --scenes relay concurrent_overlay robot_induced_rebalance \
  --ticks 300 --resolution 640 --render-stride 4 \
  --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/new_contact_run
```

先按 [OpenPI 服务说明](experiments/continuous_v2/README.md)启动独立模型服务。
Genesis 与 Qwen3-14B 组合预估需要约 36 GB 空闲显存，程序会按本地权重文件大小
核查；OpenPI 单独使用另一张 GPU。本轮 VC 环境增加 `transformers==4.57.1` 和
`accelerate==1.10.1`，来自清华 PyPI 镜像。模型与数据集仍只允许从中国大陆镜像或
本土服务获取，禁止通过 VPN 下载；本轮未新增下载模型或数据。

实际接触示范 Dataset 包含双相机、本体状态及下一物理控制步的动作目标。
它使用输入 stem 匹配 `_wrist.png`、`.state.npy`、`.action.npy`，不使用配对 manifest。
[按文件名加载的接口](experiments/continuous_v2/physical_frame_dataset.py)输出带有效时段
的 `15×8` 动作块；这些是数据生成教师示范，已用于一次实际 π0.5 LoRA 域适配训练。
训练 400 步，仅更新约 5000 万个 LoRA 参数，保留官方 DROID 归一化与动作标度。
固定 16 个 dev 样本上的 loss 从 1.674 降到 0.031；独立红、蓝、绿闭环测试为 0/3，
没有合法接触搬运贡献。拟合示范和实际操作能力分别报告，不能把训练下降称为 HRC 提升。
训练记录在 [results/contact_training/pi05_lora_v1](results/contact_training/pi05_lora_v1/summary.json)，
评测的真实视频见 [基本操作报告](results/continuous_v2/pi05_lora_atom_evaluation/index.html)。

训练入口是 `bash scripts/run_contact_lora.sh`，会拒绝覆盖已有权重/记录目录；
重跑前改脚本中的输出目录，并用 `nvidia-smi` 确认 GPU 3 的空闲显存至少能容纳
约 32 GB 的训练分配。权重保存在共享 models 目录，训练记录与缓存位于项目数据盘。
训练时只解析已有本地文件/缓存，不隐式下载模型。
启动前先用 `nvidia-smi` 确认独立 GPU 至少有约 20 GB 空闲显存。例如使用 GPU 2：

```bash
CUDA_VISIBLE_DEVICES=2 XLA_PYTHON_CLIENT_MEM_FRACTION=0.4 PYTHONPATH=src:. \
  OPENPI_DATA_HOME=/data1/sieniwgroup/sieniw/models/Physical-Intelligence/openpi-cache \
  HF_HUB_OFFLINE=1 .venv-openpi/bin/python scripts/serve_openpi_droid.py --contact-lora \
  --checkpoint /data1/sieniwgroup/sieniw/models/HRC-Bench/pi05_droid_contact_lora_v1/400
```

生成式伙伴新增带时间的公开观察历史，以及 Qwen 自己生成的解释和经验记忆；
每次决定检索最近 12 条经验，完整内容保存到 `human_memory.jsonl`。
这属于单 episode 内的生成式记忆，尚不是跨活动长期记忆，也没有真人校准或效用消融证据。
独立基本操作可选 `--partner-mode observing`，用于隔离人的接管行为。

```bash
CUDA_VISIBLE_DEVICES=3 PYTHONPATH=src:. .venv-vc-pilot/bin/python \
  scripts/collect_contact_demonstrations.py \
  --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/new_contact_demonstrations
```

`generate_scenarios` 生成可改变布局、分工和伙伴条件的任务实例，策略通过 `ExternalPolicyAdapter` 接入模型。每个 episode 产生可按目录和稳定文件名配对的 `scenario.json`、公开观测、策略输入输出、轨迹、事件和独立指标；`GreedyPublicPolicy` 只是协议基线。摩擦接触后端已实际运行，但模型基础操作、任务覆盖和研究效度尚未达到正式排行榜要求。

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
