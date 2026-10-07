# 新Goal：动态共同活动，首轮实现与开发证据

新Goal已由用户启动，active。目标全文以用户最近消息／.codex/mds/goal-2.md为准，不沿用旧Goal paused状态。当前不满足七项完成条件，禁止标complete。上一Goal-turn被中断只读检查，本轮完成代码、实际运行与证据，属于progress。

用户纠偏：人拟真指Policy／Intent，不再以人体受力／夹手／抓放LoRA为研究主线。人执行可运动学／附着，机器人必须实际具身模型控制。双方必须存在工作依赖和实际可用交互渠道；三类日常活动和六类动态情景都需实际覆盖。不能因底座或小样本工程验收完成而缩小目标。

实现：src/hrc_pilot/joint_activity.py三活动（snack_service、drink_storage、drawer_access），joint_human_policy.py已有Qwen3-14B在线意图／参与／动作／公开表达／私有记忆，无旧LoRA；kinematic_human.py人专用连续速度／附着，只能写当前人握持物品，机器人pose写入0；joint_activity_dataset.py同stem加载，按真实robot_control截取动作标签，未执行块尾不能当标签。scripts/run_joint_activity.py同世界20Hz、2秒人决策、10步机器人块，公开话语进入真实输入，robot动作／明确回复进入人后续输入。协调系统可选，身份独立，不归功裸VLA。

设计与协议／统一入口：experiments/dynamic_joint_activity_20261007/{DESIGN.md,DEVELOPMENT_PROTOCOL.md,README.md,BEHAVIOR_REVIEW.md,index.html,facts.json,report_verification.json}。Goal七条验收均逐项列当前状态。参考COOPERA／HABIT／HRIBench／PARTNR原始论文和官方实现；无新模型或数据下载。Skill使用experiment-agent run inline，用户Goal授权覆盖生成／修改脚本，未要求代理团队，未spawn。

结果根目录都在results/continuous_v2（data1软链）：

- joint_activity_{snack_service,drink_storage,drawer_access}_dev_20261007：首批在9.95／15.95／13.95s主动SIGINT，实际模型产生参数／schema错误，不是超时／猜测死亡。三个进程exit130，保留diagnostic_reason.json／diagnostic_video_verification.json和部分视频；不能计完整活动。前思考1536token不完整JSON、memory数组却要求string、action=message缺支持等。
- joint_activity_{snack_service,drink_storage,drawer_access}_schema_20261007：三条完整80s，每人40NN、160π0.5NN块／1600控制，视频1601frames80.05s，各source_changed[]。独立交互／速度／命令／图像hash核查通过；人峰速.2，机器人posewrites0。原生机器人目标均false，但无法作HRC结论：后续独立编码发现156／156／140条超过实际200token，近期对话／状态被截断。language_observation_verification.json明确diagnostic_input_truncation。全部保留，不回写为成功。
- joint_activity_drink_storage_compact_20261007：完整80s；消息动作已支持，直接π0.5、最新两条完整人／机器人公开话语，原生活动介绍不重复。160实际VLA调用的真实token／mask／解码与checkpoint归一化＋sentencepiece独立重建完全一致，120—139token、截断0。人40NN：37message、2wait、1point，2次非法message_kind；无pick／place。40s来客通知后公开留用酒瓶。原生收纳false不能自动判动态需求失败；若瓶子已可用，留在桌面可能合理。需要相同接口的正常收纳参照，区分响应请求与原本不能收纳。
- joint_activity_snack_service_coordinated_20261007：完整80s；人2／4／6pick碗，8place serving_ready，实际10.15完成；40／42公开改带走，70机器人回复准备交接。人40NN（22message/14wait/3pick/1place），视觉协调器Qwen3-VL-8B40NN（11hold/29move_ee）；44保持块／116实际OSC末端移动块。**π0.5实际调用0**，虽然服务配置在，但不能计它失败。机器人从未装奶酪，双方出现“正在／已经填好”的无物理依据说法。完整活动未完成。language status not_applicable_no_vla_inference；机器人公开计划与对话隐私边界独立核查通过。

关键接口改动：libero_torch_policy.py对任务＋normalized8维离散state总长度>200明确抛错，不能静默截断；返回language_input_evidence（实际ids／mask／decoded）。旧run_libero_native_reference依赖model_input_evidence.processed_rgb，因此新增receipt故意用另一key，不破坏OpenVLA分支。scripts/audit_joint_activity.py逐token独立重建、区分真实VLA调用／协调NN／执行原语，不把model_calls文件行数等同NN推理。最新源变更均在原run terminal后；不要将旧sourcehash替换成现版本。

本轮全套：PYTHONPATH=src .venv-libero-native/bin/python -m pytest -q tests --ignore=tests/legacy_llm_direction，233passed2skip；compile／diff通过。一次新增测试在Sim env无OpenPI模块失败，已用独立模块stub修复，最终全套通过。不要跑仓库root pytest，会收vendor／旧结果源码。永久回归保留，无临时smoke产物。

源码提交：ab85b48、711efee、29205d4、18b1814；最终报告／memory收尾提交另见git。用户此前已提交自己的goal文档／PDF（d93685f），本轮未修改原材料。

下一步必须推进整个Benchmark：明确准备／交付／接管的可观察完成条件与已公开约定，三任务实际可执行性参照；固定任务语言和操作难度的基础模型参照；双方真实执行反馈及有依据的事实检查／COOPERA式反思，避免历史中的愿望变世界事实；可靠策略条件后再冻结六情景、多背景／init、第二真实模型／明确不同系统矩阵和完整过程指标。不是继续大量提示微版本、夹手／LoRA或把消息／动作计数当cobalance。

所有仿真worker已terminal。自己服务π0.5（session29081）、视觉协调器（session54492）、报告HTTP8123（session16443）在收尾后会停止，是否存活以ps／工具handle为准。不得因观察超时重启或kill仍活进程。当前Goal仍active，不设置paused／blocked。
