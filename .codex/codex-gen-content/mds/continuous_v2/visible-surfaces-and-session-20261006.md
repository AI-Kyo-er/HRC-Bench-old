# 2026-10-06：可见目标语义、位置专家与跨活动伙伴实测

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-06
- Verification Status: UNVERIFIED（完整研究效度；执行与产物已核查）
- Version Label: visible_surfaces_session_v1

前一goal turn属于progress。本轮也有实际代码、权重、闭环和视频证据，完整goal仍active。
不能以这些工程进展或教师成功标记成熟Dynamic Human Policy HRC Benchmark完成。

## 模型适配与闭环

- 完整动作专家、语言LoRA和动作投影训练1200步，457,967,648参数更新；视觉与语言主干冻结。
- 使用原有两批729帧，train598/dev131；末尾观察保留，未来缺记录的动作步mask掉loss。
- 新标签是下一控制tick内实际施加的最后一个限速PD位置目标；原速度标签保持原样。
- train-only归一化匹配相对位置DeltaActions，输出恢复绝对位置与连续夹爪闭合比例。
- 固定16个dev样本的flow-matching loss：1.678814→0.004114；不是全dev或操作成功率。
- 权重：`models/HRC-Bench/pi05_contact_position_expert_v1/1200`（实际在共享models数据盘）。
- `pi05_position_atom_evaluation`：seed21、30秒、15Hz、horizon4，3项0/3，339次模型调用、1350动作。
  只有blue有真实双指接触抬起证据，最终释放偏离旧目标；red/green无有效抓取。
- dev真实观察单次采样动作审计：首步关节MAE约0.006–0.070rad；低flow loss没有消除控制误差。
- 三条像素、模型输出、位置转换、物理请求与真实视频完整核查通过，不归因于HRC能力。

## 公开任务与生成式记忆

- 持续公开任务板从实际assignment/reassignment/correction消息构建，不从私有评测器读取。
- Qwen生成并保留current_goal，以及真实观察上的经验文本；角色选择仍由模型生成。
- session模式保留同一persona和最多48条历史经验，输入最近12条；明确与当前世界状态分开。
- 保存public_task_board.jsonl / human_session_memory.jsonl / human_memory_retrievals.jsonl。
- `pi05_position_qwen_session`：同一cooperative伙伴、可见区域、seed21、最长40秒，3任务。
  404次VLA调用、1614原生动作、108次Qwen决定/经验；解析错误0。
  relay在27.6秒完成human:red和human:blue，两项贡献全由人完成；另外两项未完成且无贡献。
  机器人贡献全部0。三条运动、像素动作链路和视频核验通过；运行中src无改动。
- 后两活动分别保留12/24条旧经验，实际输入最近12条；但伙伴整段observe，声称等待最新位置确认。
  开始接力选择red正确，后期仍可能把接管blue误称为原先分配任务。任务板不保证模型正确理解。
- 世界在每个episode重置，时间回到0，而人的经验跨episode保留；不是世界无重置的持续活动。
  不能从这轮推断记忆效用或真人行为规律，下一步优先考虑真实持续世界与明确活动上下文。

## 可见表面与数据生成

旧“放到蓝色底板”语言与不可见65mm中心点判定不完全一致，部分绿色点也在旧底板外。
新goal_regions.py让显示与判定共用0.50×0.24m蓝色收纳/绿色留用区域；检查完整物体AABB
足迹与工作面高度，仍需真实接触抬起、稳定支撑、释放和前置贡献。旧结果不重评分。
新布局独立变化各物体位置、保证分离且初态不已满足区域目标；VLA仍只得到相机/本体/公开语言。

数据教师在新布局出现手掌压物体，第一批96计划因此主动停止；3条已结束失败视频保留，
未结束目录清理。其目录为 `.../datasets/visible_surface_demonstrations_v1`，只作诊断。
教师后续使用实际碰撞几何计算手掌间隙、限定笛卡尔步长，并允许在表面内低落差时实际释放。
不同教师校准阶段不能合并成独立效果样本：

- visible_surface_contact_calibration：green/blue两seed完成，red两seed未完成，4/6。
- visible_surface_release_calibration：red两seed未完成，仍停在carry阶段，0/2。
- visible_surface_area_release：允许carry/lower在物体已进入区域且低落差稳定时释放，red seed104完成，383帧。
  上述释放不改物体坐标；正式提交仍由实际落稳与接触证据判定。

校准共9条视频严格核验，三颜色均已有物理可行性证据；不是学习模型成绩。
正式96条采集目前正在运行：

- process PID **430271**，exec handle **56617**，GPU0。
- 输出：`/data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/visible_surface_demonstrations`。
- 日志：`.../cache/visible-surface-full-collection.log`。
- seed100–131，green/blue/red；截至本轮报告快照已核验63/96且63成功。
- `progress.html` 与 `live_video_verification.json`是明确的部分快照；最终dataset.json尚未生成。
- 运行中保持src和使用的教师源代码不改。下轮先复核同一PID/handle，不能因观察超时重启。

## 模型资源与下一步

π0.5-LIBERO从中国ModelScope直连下载完成，10个文件按公开SHA256/大小核验。
实际：`/data1/sieniwgroup/sieniw/models/lerobot/pi05-libero`；仓库`models/pi05_libero`软链接。
download_receipt.json记录来源、无环境代理、重定向仅ModelScope/中国OSS。
它是LeRobot格式PyTorch权重，key有model.前缀，动作7维，状态8维；尚未完成本平台推理。
不得把下载完成当成第二模型已测，也不得直接喂DROID的关节状态8D而忽略控制语义。
原π0.5位置服务PID392796/GPU2在本轮收尾结束；CPU下载PID424979已退出。

优先继续：完成96条采集与严格核验，扩大/修正基础操作训练；接入仿真预训练参照并
核对真实状态、相机与动作约定；让活动转换保持物理世界与人/机器人历史连续，再评测
多人格、开放目标、九类活动与更多真实具身算法。当前仅cooperative合成伙伴和一类机器人架构实测，
人体仍六DOF接触手+IK显示骨架，非完整人体动力学或真人校准。同步推理暂停模拟时钟。

本轮回归测试116项通过。重要代码已有dab61c2提交，其余场景/报告更新在收尾提交。
未跟踪用户COOPERA PDF继续不提交。没有VPN模型/数据下载或非中国下载回退。
