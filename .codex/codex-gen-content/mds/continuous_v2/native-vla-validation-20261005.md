# 2026-10-05：匹配历史与原生 π0.5-DROID 阶段记录

## 目标状态

Goal 仍为 active。完整目标是可运行真实具身模型、持续保留世界 / 分工 / 交互
历史的 HRC benchmark，系统测试指导、共同执行和干预的依赖、并发与演化。
不能以手写伙伴、匹配探针或一次模型接口接通代替完成。原始依据为
`.codex/mds/idea.md` 与 `idea-conversation.md`；不要缩成角色切换 / 失败接管。

## 本轮已完成、可直接检查

1. `matched_history_genesis_v2`：3 seed，18 条视频（6 历史来自 v1、12 探针新跑）。
   首次公共输入 / RGB / 动作，以及回答前伙伴完整公共输入 / RGB 五项 3/3 一致。
   reliable adaptive trust=.78 / reliability=.82，接受；failures adaptive
   trust=.34 / reliability=.16，拒绝；frozen 两历史 .7/.7，均接受。四条件
   都完成，但贡献者不同。实际公共记录重放学习，不读 evaluator 潜变量。
   显式重建当前世界与协议，只带两个变量；不是无重置持续活动或真人规律。
2. 原生关节抓放 + 实际腕部相机。`joint_calibration_genesis_v1/v2`：18 次
   关节动作，1.2s 完成，joint_control attach / release / transfer 事件。
   公开几何 IK 教师，非训练模型；物体仍运动学 attachment、无碰撞。
3. 官方 OpenPI commit `215abfb217dbac7d5f1273282331b9b1866c0479`，独立
   managed Python 3.11.16 环境。权重 20 对象 12.43 GB，GCS MD5 全通过，
   `/data1/sieniwgroup/sieniw/models/Physical-Intelligence/pi05_droid/`。
   tokenizer 在共享 openpi-cache。模型服务 GPU 1，Genesis GPU 0。
4. 真模型 `pi05_droid_genesis_v1/v2`：12 / 57 次实际推理、90 / 450 步
   native joint_position，6 / 30 秒模拟时限，均未完成蓝杯收纳、无抓取事件。
   实际末端与夹爪发生变化，保留失败。双相机 / q7 / gripper / prompt 五键
   输入，无物体坐标或内部伙伴状态；官方动作 10×8，15 Hz 每步 .2 rad
   归一化速度转换，执行前 8 个。所有调用 PNG 哈希与关节转换独立核查；
   视频完整解码 98 / 458 帧。首编译11.65s，稳态约90ms；同步推理暂停
   模拟时钟，真实延迟效应未测试。v2 沿用服务随机流，不是严格时限配对。
5. 修正工作项按 role-id 匹配绕依赖、接管绕依赖、几何接近提前成功和
   参考后端 source 数组被搬运覆盖的问题。新活动成功需释放和合法提交；
   旧评分快照不回写。`recovery_contract_genesis_v2` seed0四条件：人接管、
   自行恢复、无失败完成；persistent failure 未完成。蓝杯完成均晚于红杯。
6. 六组新报告核查17个场景 / seed 组合，离线 Chromium 无 JS 错误，
   视频 metadata、RGB / wrist 加载、终态视频定位、事件按钮、375px通过。
   报告写清目的、设置、策略、结果和边界。视频来自运行时渲染，非轨迹动画。
7. 58 tests pass（不运行已废弃方向 tests/legacy_llm_direction），compileall、
   JS syntax 和 diff check 通过；本轮临时 contract_reference_debug 目录删除。

## 复现入口

仓库 symlink `.venv-openpi`、`.venv-vc-pilot`、`vendor/openpi`、`models/pi05_droid`。
数据位于 `/data1/sieniwgroup/sieniw/projects/HRC-Bench/`，仓库 results symlink。
README 提供 serve / run / verify 命令。完成本轮后关闭服务释放显存；下轮重新
检查 GPU 并启动，不能只凭旧日志判断服务仍在运行。
下载因中断句柄缺失且 process 确认停止后才恢复 partial；环境安装已成功。
首次 gcsfs tokenizer 下载失败，改用官方 GCS HTTPS 获取并成功加载。

## 下一阶段按完整目标推进

- 匹配诊断补足模拟机制证据，但必须实现同一自然活动不重置世界 / 协议 /
  伙伴 / 模型进度的历史形成与后续贡献，不依赖新任务重建。
- 让伙伴依据真实原生模型进度 / 停顿 / 失败更新行为，明确公开可辨识性；
  当前 native VLA 伙伴只是观察，不是 HRC 策略比较。
- 核查相机姿态、训练分布、动作控制、任务语言和物体接触；不得把未校准
  场景单次失败归因为没有 HRC 能力。Genesis reference limit 提示需分析，
  不能将真实硬件等价控制当作已验证。
- 建立实际碰撞 / 接触 / 失败与恢复；Avatar 和对象绑定仍操作抽象。
- 有效作用依赖、结构对照、匹配操作难度与结构留出仍待跑真正训练模型。
  结构标签 / cobalance 代理分数不是科学效度证据。
- WLA 只有接口；本轮实际推理模型只有 π0.5-DROID。没有真人 HRC 或
  持续 cobalance 泛化结果。PARTNR / HRIBench 的不足是待审计的研究动机，
  不要断言它们只允许静态固定伙伴。

ARS Evidence Passport: status=UNVERIFIED（研究效度）；工程 / 机制和原生
模型链路证据已核查，完整研究假设、真人和模型协作边界未验证。
