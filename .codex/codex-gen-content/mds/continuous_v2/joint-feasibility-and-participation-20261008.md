# 动态共同活动、参与契约与原生技能库（2026-10-08）

Goal仍active，七项完成标准未全部满足；不complete/pause/block。本轮为进展：实际审计、发布视频／数据、修复参与契约、扩展操作接口、启动跨任务开发，不是状态复述。用户要求中文、GPU先nvidia-smi单卡、data1大文件、本土模型源、不覆盖旧失败。无新下载、外部API、子代理或临时smoke。

## 当前已提交实现

9fdfa2c：报告builder、参与字段schema2、三条新初始化开发协议。
4a53edb：实际过程测量、同stem跨run数据加载、视觉原生单技能系统。
dbd1d67：具体活动外部事实、双方可能贡献的公共描述、九条公开原生操作库、独立视觉与理想感知选择、19条报告及复现脚本。

核心：人Qwen3-14B候选＋实际NN反思；连续人运动学／附着0.2m/s；机器人实际π0.5原生7D OSC 20Hz，不改写机器人位姿或吸附。此批场景是MuJoCo/LIBERO，不是Genesis。人和文字机器人协调器共享冻结权重但不共享私有上下文。视觉协调Qwen3-VL-8B额外模型，不能称裸VLA。

schema1旧记录：participation=step_aside只当文字，实际未走开。schema2显式参与枚举可以来自presence_choice或participation；冲突拒绝，不解析自然语言替人选择。每行保存choice_schema_version，旧数据按旧schema审计，不倒改。

robot_skill_bank.py：九条技能字符串与安装的官方LIBERO-goal公开任务语言核对，NN选择skill_id，适配器只编码它所选指令。不是阶段路由，不保证技能在新初态成功。支持holding的语义仍是维持原抓持，不暗中增加释放／新抓放技能。库外请求、操作失败与协调失败必须分开。

activity_private_context.py：18种活动×情境的外部事实文本绑定实际物品，保留seed时间窗与初始参与位置，不写action或下一策略。main仅--activity-specific-context启用；先前通用“有一件东西”的歧义开发原样保存。初始公共任务改为可能贡献，非已完成或已接受承诺。

## 已独立完成结果

参考成功三类：
- joint_feasibility_drawer_access_20261007：固定人＋实际π0.5，完整清理／开／放入。
- joint_feasibility_snack_service_handoff_20261007：固定人＋实际π0.5，提供碗／填／带载荷交付。
- joint_feasibility_drink_storage_tolerant_20261007：固定人＋既有末端轨迹实际OSC反馈，当前机器人NN=0；不能当VLA成功。

其他饮品参考、回放、strict tracking失败全部保留；原点心in_box接口崩溃仅24.1s部分视频。

上一批神经也全部审计：grounded direct/visual、symbolic、native_skill、participation共8条120s。抽屉native_skill真实10.4s开、28s奶酪放入，36s公开改用途、后实际转到snack_delivery；反复搬起与过时澄清，期末仍持物，不是完整协作。旧leave_return仅话语，没有身体离返。

三个init1/seed62完整120s：
- joint_presence_contract_snack_leave_return_20261008：人60NN，协调30NN，VLA176；碗10.9s释放准备，15.7s贡献请求完成；28s选择away，31.15s请求完成；32s选择return，35.15s完成。实际身体y>=.8区间29.2—32.95s。原生填碗从未成立。动作兑现成立，协作正确／整体完成不成立。
- joint_dynamic_drink_correction_20261008：人60NN，协调30NN，VLA232；4s提供瓶，15.35s准备，20.55s请求完成；通用纠正后仍只核查，没有实际纠正／接管，原生未上架。
- joint_visual_native_snack_leave_return_20261008：人60NN、视觉30NN、VLA240；实际离返同29.2—32.95s，持续选择填，未完成。视觉图像hash与真正输入、编码及实际指令逐项重建核查通过。不凭单例排名。

19段视频独立完整解码与时间轴通过（18×2401帧＋部分483帧）。统一报告experiments/joint_feasibility_20261007/index.html，关键行为BEHAVIOR_REVIEW.md、正式计划EVALUATION_PLAN.md。此前单操作能力限制已披露。浏览器19段全部play/seek/Range206、172links、375px通过，记录data1/results/joint_report_browser_20261008/verification_final.json。

数据datasets/dynamic_joint_activity_dev_20261008软链data1：18条完整轨迹、6480组观测、43200实际控制动作，全量加载、唯一sample_id、实际执行前缀核对通过，不标专家成功。不用配对manifest，脚本export_joint_development_dataset.py可复现。私有人记录不进入机器人输入。数据末尾验证文件权威，扩展后不要硬复用旧计数。

248有效pytest通过、2skip：PYTHONPATH=src LIBERO_CONFIG_PATH=.../cache/libero-native .venv-libero-native/bin/python -m pytest -q tests --ignore=tests/legacy_llm_direction。新增技能库两个测试对官方公开语言及可改选技能编码，活动事实一个测试保留采样不含动作命令。不是策略效度证明。

## 当前正在运行（必须重新核实PID；不要改加载的核心源）

三条dbd1d67、init2/seed63/120s、每4s高层、人schema2反思、初持物、具体情境＋公开技能库：
- joint_skill_bank_snack_detour_20261008，GPU2，PID3095305，session70729，log data1/results/joint_skill_bank_snack_detour_20261008.log。
- joint_skill_bank_drink_correction_20261008，GPU0，PID3095304，session92470，log同stem.log。
- joint_skill_bank_drawer_request_20261008，GPU3，session54112，PID需ps确认，log同stem.log；视觉服务GPU1。

前两启动后第一NN选择已写，第三初始选择open_middle_drawer。都是live，不当终态。初始NN仍出现把准备计划当已完成，原样记录，不修改source去美化。

视觉技能库服务：GPU1，PID3095303，session6820，端口8782，log joint_visual_skill_bank_server_20261008.log，metadata policy=neural_visual_skill_bank_coordination。
π服务：GPU3，PID2267256，端口8766，旧session52743可能已失效，但ps确认live；不能因句柄失效重启。
报告HTTP：8123，session50226；需要用ps/连接核实。上一HTTP在自动Goal续轮被关闭，已确认连接拒绝和PID缺失后才新起。

主入口hash包括native*.py、human/actor/joint_world/skill_bank/situations/context等：三worker终态前不要改这些。服务serve_robot_coordinator.py、robot_skill_bank.py等也须保持加载版本；要改先等worker终态再停止自己服务。模型总显存预算检查后单卡；GPU3人模型与π服务合计在49GB内，别忽略共享余量。

## 下一步

1. 三worker各按原句柄或具体PID核实进展，不因新turn丢session而重启。
2. 终态后audit_joint_activity、evaluate_joint_process、verify_episode(require_timeline=True)保存independent_video_verification，再builder／export／browser核验。builder对完整结果要求输入与视频独立核查；未核查会拒绝发布，旧页面不会替换。
3. 实际检查detour、correction、robot_request有没有行为发生，所选技能是否根据公开新用途改变、实际物体终态与约定如何。不以配置、对话或旧native_success代替。
4. 根据实际使用技能补齐匹配初态的原生操作参考／基线。九条原生语言存在不证明执行成功，饮品此前只有轨迹反馈完成，尤其不可直接宣称协作缺陷。
5. 继续整个Benchmark：六类实测、人策略事实一致性及实际伙伴响应、完整双向案例，冻结多系统×多场景×测试init4/5正式矩阵。EVALUATION_PLAN的72例是计划未启动，不已完成。
6. 最终语言／公开信息／输入权限／任务长度混杂要分开，cobalance负担与语义约定尚未验证；Goal保持active。

## 后续权威更新（接续时以本节为准）

- 8a5f5bf补齐init2匹配参考；三条reference全部完整True，机器人均实际π0.5：点心12次／20.8s、饮品20次／27.45s、抽屉12次／17.8s，人NN=0。现在不能继续说饮品只有轨迹反馈成功。
- a7c2db6：human-auto-buffer可选，仅兑现NN已选relocate时连续暂放原持物到其公开个人缓冲区，再取目标物。不读评分、不选新活动。物品接触机器人仍拒绝。两个永久回归验证重复请求不重启、两物连续、机器人qpos0修改。此缓冲在NN复测因抽屉没打开而未启动，不当有效协作证据。
- 9077c65：Intent语义观测、SemanticJointHumanPolicy、独立运行脚本run_semantic_joint_activity.py，actual private_input/reflection_input为NN真正得到的紧凑事实；observation_source_scene保留原始测量供重建。没有坐标／评分偷偷注入，事实和公开伙伴说法分开。辅助message_kind未知时notice保留原值，非法动作／区域不矫正；schema3独立重建。Source SHA含适配类和独立wrapper。
- 全量有效pytest253 passed / 2 skipped。27视频独立解码／timeline通过；27浏览器核查正在session92993（先poll）。此前25全部播放拖动Range、224链接和375px通过。
- 数据现在26完整轨迹、8400观测、62400实际动作（按dataset_verification.json核实）。没有正式split或专家成功标注。
- 三条技能库NN全部终态：点心detour仅33.2—36.95s离返，无饮品操作；饮品4s留用后116s保持，但R回复仍等待释放后上架，不能称接受留用或证明理解；抽屉5.6s真开，人44s后7次奶酪请求因持餐盘被拒。无真实机器人主动请求见证。
- 新drink公私请求复核文件是public_request_response_review.json，不是agreement。记录4s原话、之后0VLA、H一直持瓶、R回复8s进入H输入；R实际保持≠接受取消，不自动完整HRC分。
- joint_buffered_drawer_request_20261008终态120s：VLM0s执行后4s虚称opened、保持，真实门未开；28次不可进入拒绝，buffer0启动。实际input／动作／视频审计通过，但伙伴事实理解及任务完成不成立。
- joint_semantic_drink_detour_20261008终态120s：32s人暂停以处理餐盘需求，R真实hold；76s唯一relocate酒瓶到staging，87.3s释放准备、92.45s完成；未上架、餐盘没实际搬。大量目标名wine_rack_1不是区域、message:null语法造成失败；不能算全部policy错误或机器人HRC缺口。
- METHOD_REFERENCE_UPDATE_20261008.md重新对照HABIT与COOPERA原文，采纳／未复现项明确。暂无真人效度或新NN训练。未来需先统一高层贡献与执行器目标的契约，别继续区域命名和辅助字段错误导致假失败；不要开始72正式矩阵直到伙伴有效。

当前唯一live worker（必须用PID/stream重新确认，不因handle缺失重启）：
- joint_semantic_drawer_request_20261008，GPU2，PID3495686，session8049，最新确认23.95s（2m55s）。init2/seed63/120s，busy robot_request，人Semantic＋auto-buffer，视觉技能库NN＋π。先前GPU2被其他用户进程占用，预算检查在加载/创建结果前exit2；GPU释放后才启动，拒绝日志保留data1/results/joint_semantic_drawer_request_20261008.gpu_unavailable.log，不覆写。
- Vision bank服务GPU1 PID3095303，端口8782；πGPU3 PID2267256，端口8766；HTTP8123 session50226，需核实。
- 其他新worker/匹配refs均terminal，没kill外部进程。不要改当前加载的main、Semantic/intent_observation、JointHuman、KinematicHuman、native*.py、skill_bank、world、context等源，等drawer终态后再修契约。
- Next：回收drawer→独立audit/evaluate/完整解码→builder/export/browser。按照真实行为补六覆盖和可靠人策略，再做多系统测试init4/5正式矩阵。Goal仍active，未满足七项。

最终报告检查：session92993已terminal exit0，27段全部实际play/seek/Range206、242链接、375px、JS0error通过。数据26/8400/62400全量加载通过。当前drawer PID3495686仍live，最近ps为3m45s；Goal不complete。
