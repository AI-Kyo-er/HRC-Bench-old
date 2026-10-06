# 2026-10-06：真实机器人接触与生成式伙伴诊断

Goal 仍 active，不能以这轮结果宣称成熟 Benchmark 完成。

## 实际改变

- 提交 `c67d776`：重要连续、原生模型、恢复、校准、历史实验入口在正式 HTML 前
  强制逐帧解码 MP4 并核对时间轴。7 组现有重要结果、40 条视频全通过。
- 新 `ContactWorkspace`：自由碰撞刚体收纳块、0.1 kg、摩擦 0.8，不绑定机器人，
  不以语义 transfer 或坐标搬运代替关节控制。实际双指受力 + 抬起 + 释放稳定
  0.4 秒才提交机器人贡献。目标速度 1.2 rad/s、每指 0.04 m/s，逐物理步记录
  requested / applied targets。人体仍为 VC 运动学执行器。
- 原生 OpenPI 入口支持多任务、九类目录、自定义 JSON 和多 seed，以及本地 Qwen
  人格选择；不替 π0.5 生成语义搬运、求助或教师动作。公开分工生成英文基础指令，
  私有评测内容不进入机器人模型。
- 修复 Qwen 自己发出的消息重复触发自己推理；伙伴支持返回。语言模型在 Genesis
  之前 prepare，解决 Torch/Triton/setuptools 与 Genesis 的 distutils 导入冲突。
- 接触运行增加 `motion_verification.json`：检测人持握或释放时的物体逐帧跳变，
  以及机器人施加目标的速度。异常记录保留，正式模型聚合排除这些样本。

## 已跑结果

1. `contact_calibration_formal/joint_grasp_calibration`：真实摩擦夹持、抬高约 13 cm、
   释放后稳定在目标区；4.0667 秒活动完成，无机器人 attachment，motion verified。
   教师来自几何，不是训练模型或 HRC 结果；视频和时间轴 verified。
2. `pi05_qwen_contact_benchmark`：seed 0，relay / concurrent_overlay /
   robot_induced_rebalance，15 Hz，最长 300 tick。模型调用 10/27/38，共75；
   Qwen3-14B cooperative 决策 6/15/20，共41，解析错误0。
   原始活动评分 true/true/false，人接管前两条；机器人合法贡献全部0、物理抓取0。
   时长5.1333/14.1333/20秒。人体单帧最大跳变约1.044/1.066/1.057m；
   motion violation 14/35/21。三条均只作诊断，不能作为正式 Benchmark 成绩。
3. 三条新模型视频与一条正式接触校准视频均通过完整解码和逐帧时间轴核验。
4. 独立原生模型核查通过3个 episode、75次推理、589个原生关节动作；实际外部 /
   腕部像素哈希、动作块转换、5键模型输入边界及物理控制请求全部一致。
   当前有效测试96项通过，HTML三页无浏览器错误、断链或375px溢出。
   smoke目录已删除，两个GPU进程已结束并释放显存。

## 证据边界

新报告 `experiments/dynamic_contact_20261006/index.html` 明确所有限制。
`robot_success` 旧字段是几何目标满足，不等于机器人贡献，必须看
`robot_role_success` 与 `robot_contribution_completion`；新结果增加几何字段显式别名。
`cobalance_score` 是未校准手工代理，不用它掩盖机器人零贡献或物理执行异常。

本轮正式联合运行过程中补了接触记录字段，原生结果 provenance 的源码 SHA256
是报告时文件快照，已明确标注，不能声称精确对应已执行源码。后续入口已改为
运行前捕获并记录运行中改变的文件，后续运行不要在执行中改其源码。

VC 环境补 transformers4.57.1 / accelerate1.10.1，从清华 PyPI，无新模型/数据下载。
已有 Qwen3-14B 放在共享 models，π0.5 服务 GPU1约20GB，Genesis+Qwen GPU0约30GB；
各进程仅使用单卡并在启动前 nvidia-smi 核查。推理仍同步暂停模拟时钟。

## 下一步：沿原始目标继续

首先真正替换人体拿放执行器，取消 Avatar pick/put 对对象的直接坐标写入；
要求连续可见的伸手、实际手物接触、物理持握和释放，以及全身与物体动作一致。
不要仅改动画速度、平滑视频或调评分器掩盖瞬移，不要继续堆机制配对。
随后建立真实模型的基础操作表现，避免把操作分布失败误归因 HRC；在同一自然
活动中保留伙伴、世界、模型和历史，扩展九类任务、留出组合、未见伙伴、多模型和
多 seed，最后才讨论有效的 HRC/cobalance 指标与模型差异。

ARS Evidence Passport: status=UNVERIFIED（完整研究效度）；真实模型运行与机器人
摩擦接触已有证据，人体运动连续性失败、真人效度和成熟 Benchmark 尚未实现。
