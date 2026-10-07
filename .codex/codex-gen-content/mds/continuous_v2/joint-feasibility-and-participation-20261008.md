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

## 最新接续更新：显式贡献接口（950419b）

上一turn属于progress：新增参数接口／空消息契约、回收语义抽屉、独立核查与跨两活动运行。Goal全部七项仍未完成，不complete/block。

- joint_semantic_drawer_request_20261008已terminal120s。Rπ240调用，原生打开5.65s成立；人没有收纳，29.2s开始退出桌边直到120s未返回，0执行拒绝／0自动缓冲；尚无Robot主动求助。H反复等待可进入，R公开只Opening，不能把几何开放与释放操作区等同。NN输入及实际动作／2401视频核查全部通过。
- human_contribution_contract.py：明确对象ID与区域ID区别、home只是初始位置不是on/in、staging是给伙伴可获取物品的位置。所有区域来自实际scene，不编造下一动作。message/memory:null规范为空不丢合法动作；unknown记录kind原值notice；非法动作／目标仍拒绝，不自动把wine_rack_1改成其他地方。
- ContributionJointHumanPolicy独立适配类，在实际NN输入加human_contribution_interface并使用既有语义事实，源sha与原主运行时一起记录，schema4可重建。旧NN原始输出与失败不倒改。关键实现950419b，256 tests passed / 2 skipped。
- run_contribution_joint_activity.py独立wrapper，继承已提交的运行时，未改正在加载的旧main／human/actor/semantic/intent等文件。不要在新worker结束前改这些及新contribution模块。
- 新固定开发：init3／seed64／120s／每4s高层／H14B候选反思／auto-buffer／真实π技能库／理想感知14B协调（共享冻结权重但私有上下文独立）。两个活动，不作严格单因素对比，不作为正式多模型n。
  * joint_contribution_snack_change_use_20261008：GPU0，PID3522129，session54368，log data1/results/joint_contribution_snack_change_use_20261008.log。
  * joint_contribution_drink_detour_20261008：GPU3，PID3522133，session82535，log同stem.log；GPU3共享π8.9GB＋H预算36.36GB，启动前free39.6GB足够。
- 最新实际中途：两worker约60模拟秒；点心0字段拒绝，0s提供碗，52s已请求搬碗snack_delivery，真实R填装关系仍未见；饮品1区域错误，4s等实际relocate wine到drink_staging，52s选择away。尚无buffer启动。不能把搬空碗当成品交付，不能把离返当已完成餐盘活动。
- Actor／意图接口下一步仍需整体完善，NN源有语义不一致（目标Rack但实际选staging、等待可进入但门已几何打开）。不能仅凭格式通过或身体动了就称拟真／真实协作；也不要马上写复杂新手指／动力学。保留接口未支持动作的边界，不把这些算Robot能力失败。
- 当前发布28视频（27完整120s＋1 partial483frames）、28全play/seek/Range、251links、375px、JS0err，browser verification_final.json。数据27完整／8640观测块／64800真实执行动作，全加载唯一stem来源检验通过。正式split、可靠HumanPolicy、六实际覆盖、多系统正式矩阵和cobalance效度仍缺。
- 服务仍π PID2267256 port8766，VLM PID3095303 port8782，HTTP PID3054726 port8123。旧语义drawer PID3495686已terminal，SemanticDrink PID3380481已terminal。不操作别人的GPU任务；旧显存拒绝日志保留。

下一步：重新核实两个新PID／同session推进，终态后audit/evaluate/video→builder/export/browser，重点审阅政策变化是否体现在正确物品与约定、是否真正Robot响应并影响H。任务可执行性三init2原始操作已有actualπ成功，不能继续无休止底座证明。仅有actor逻辑、引用、绿灯与反复提示不算Goal。正式72计划仍未启动。

## 后续接续：两个参数条件终态／原生推理资格

本turn属于progress：回收两个120秒跨活动条件、独立审计及30视频发布，并开始NN原生thinking资格。Goal仍active，不能complete。

- 两个950419b条件均terminal，init3/seed64，人各60NN／协调30NN：
  * joint_contribution_snack_change_use_20261008：VLA120、人0parse error/0执行拒绝；10.8s准备，40s请求搬碗snack_delivery、60s完成；16近目标请求部分no-op。始终未真实填装，搬空碗不计点心交付；餐盘托盘用途没有实际餐盘行为。
  * joint_contribution_drink_detour_20261008：VLA128、3parse error/0执行拒绝；11.35s准备，33.2—72.95s实际离返；餐盘未搬、酒瓶未上架。不能把身体离返当完成另一活动。两视频2401帧、输入／实际动作／schema4独立重建通过。
- 当前报告30视频（29完整120s＋1 partial），全部play/seek/Range206、269 links、375px、JS0error通过。dataset29完整、9120观测块、69600实际控制动作，唯一ID全加载检验通过；无formal split或专家标签。
- EVALUATION_PLAN已修正init2三类actualπ成功参考，不能说饮品只有replay；测试init4/5依然未运行。72正式矩阵未启动。
- 56382a3：ReasoningJointHumanPolicy继承贡献／语义层，同一Qwen3-14B原生enable_thinking=True、最大4096新token。单次人NN，不候选＋反思第二次，机器人Vision8设置不变；这个人策略变体不是新增Robot模型覆盖。最终JSON从</think>后取，完整原始输出保留。无教师下一动作、私有评分、新训练或下载。
- 永久新test验证剥离think后保持实际消息，不替换选择。先前full256passed/2skip，新focused2passed，尚未做最后full257。下一次有必要改动／验收时跑对应检查，不为绿灯无谓重复。

当前live必须ps核实：
- joint_reasoning_drawer_request_20261008，GPU2，PID3555437，session29736，log data1/results/joint_reasoning_drawer_request_20261008.log；init3/seed64/busy/robot_request/120s、human-auto-buffer、native技能库、Vision8＋π。
- 最新观察thinking 0s place plate到personal，4s正确等待真实门未开（不能仅相信公开话语），8/12重复relocate_plate同位置，28/32实际away、36return，40relocateCreamDrawer，44继续，48有一次presence与搬物冲突→保留wait。47.95s真实持cream、transfer_raise，原生R开首次6.2s。这些均中途，不提前宣布完整HRC成功。
- buffers0：人自行先放餐盘，既有自动缓冲未实际触发。这说明思考条件仍须实际frame和结束状态审阅，不能称buffer有效性已证明。
- vision PID3095303 GPU1 port8782，π PID2267256 GPU3 port8766，HTTP PID3054726 port8123。其他新worker已terminal；不动外部GPU任务。
- 当前job加载core main、humanBase、semantic/contribution/intent、Kinematic/native*.py以及reasoning wrapper等都保持源冻结，结束前不要修改。coordinator服务自身源保持加载版本。

Next：按同PID/handle等待reasoning终态，audit/evaluate/full decode→builder/export/browser。审阅当前需求／实际贡献／伙伴响应，不能因格式少错、动作执行或世界关系满足就判cobalance。仍需六情景实际覆盖、可靠人策略、完整双向重组、多系统正式多init和评价。未来要扩大合理贡献接口／任务交互而非反复小提示或人体抓放LoRA；未支持动作不能当R能力缺口。


## 本轮接续：终态事实回收、契约／测量修复与测试初态参考

本轮属于progress：回收推理抽屉、独立审计，修复两个真实接口问题，运行并核验init4两条参考，启动跨活动NN与剩余参考。先前仅整理Goal文本不构成实验进展；本轮已依据实际PID、日志与记录重新核实。Goal仍active，全七项未满足，不complete／block。

- joint_reasoning_drawer_request_20261008已terminal120s。H30原生推理／R30视觉协调／240实际VLA；旧schema4独立重建通过，2401帧解码／timeline通过。6.2s真实打开；59.15s人请求10退手完成，60s记录cream与wooden_cabinet_1_g27真实底面接触；76s重复取物，84s说已存好但正在持物抬起，120s仍持奶酪。两离返29.2—36.95和85.2—108.95。无主动R请求，完整活动失败。public_request_response_review.json逐条保留事实，不是专家／真人标注。
- 6b9cbe1：schema5只允许return_to_work＋relocate（执行器自身会接近桌边），物品／目标不变，step_aside＋搬物仍拒绝，旧schema4不倒改。ReasoningJointHumanPolicy新批schema5。旧有10拒绝保留。
- measurement_version2增加真实抽屉底面几何接触＋相对高度／XY的释放支撑事实；手持／gripper接触／仅附近／侧壁不计。没有成功评分或下一策略。observable_world保留measurement_version1，独立audit按记录版本重建。260passed/2skipped；旧推理抽屉审计在新代码下复验通过。
- b769989：发布推理终态，预先记录跨活动与测试初态参考协议。新的两NN条件用init3/seed64/120s/4s高层，单次H14B thinking4096，Vision8技能库＋实际π；没有新下载／训练／教师。
- init4点心参考终态：实际VLA16，10.85s准备、22.25s填装、44.15s人请求交付完成，reference_complete=true。init4饮品终态：实际VLA204，11.35s释放准备、16.6s退手完成，无原生上架，reference_complete=false、stage robot。两条均全输入／控制／2401视频核验通过。此批无动态人，饮品不能归动态HRC失败。人参考调度／robot等待和清场有独立来源，不称整条轨迹都来自VLA。
- 当前已发布33视频：32完整120s＋1早期partial。浏览器33全play／seek／Range206、298链接、375px、JS0err。数据32完整、9840观测、76800实际动作全加载／唯一ID通过；无formal split或专家成功标签。dataset和HTML已更新。

必须重新ps确认的live（本次最后核实均alive）：
- joint_reasoning_snack_join_20261008，GPU0，PID3629154，session54739，log data1/results/joint_reasoning_snack_join_20261008.log；最新NN32s、schema5解析无错。20s实测cream支持接触bowl，正在人所选交付运动；不是完整活动或加入后重组已经验收。它在初始aside开始放物，不强迫等待外部cue，需要审阅是否已提早参与。
- joint_reasoning_drink_correction_20261008，GPU2，PID3629322，session57724，log同stem.log；最新NN32s，point rack，尚未收到具体用途cue（该次private_context=[]），不提前说纠正失败或覆盖成功。
- 六参考串行父进程PID3634992，session83809，GPU1，log data1/results/joint_references_test_initializations_20261008.log。init4前两已terminal且核查，当前drawer init4子PID3648740最后alive约1m07；之后按同脚本依次init5三个，不能因旧子PID消失就重启父任务。
- π服务GPU3 PID2267256 port8766；Vision服务GPU1 PID3095303 port8782；HTTP PID3054726 port8123。启动时GPU0/2各48GB空闲，H预算36.36GB；GPU1约30GB空闲供参考渲染，没停止他人GPU。

源冻结：以上live加载main、JointHuman、Semantic／Contribution／Reasoning／intent_observation、Kinematic／native*.py、joint_world／activity_private_context／skill_bank等。终态前不要改这些文件，也不要因工具handle过期重启。只改报告、审计或独立分析（如需变更审计，保存准确版本）。本轮无临时smoke文件。

Next：继续同PID／session；收齐余四参考及两NN，逐个audit/evaluate/independent full decode，解读当前实际共同安排与终态，不以NN宣称、格式通过、原生局部目标或身体移动计完整HRC。报告RUNS已登记8新条件，终态若还没独立video／audit则builder会拒绝发布，先完成核查再重建／导出／浏览器。仍缺可靠动态伙伴、六实际情景、完整持续重组、正式多系统多init与cobalance有效评价。不要回到长篇架构空想或同一小提示的无穷迭代。


## 接续终态：原生工具链与首个维持到终态的神经物理链

本轮progress：六条参考全部回收／独立核查，原生推理两条件终态分析，原生工具人接口、结构化话语及稳定放置执行落地，三条新工具条件全部运行结束并核查。Goal仍active，未满足六情境实际覆盖、可靠伙伴、完整动态重组、多系统正式矩阵和cobalance有效评价；不complete／block。

权威提交：721c7d9原生工具反馈人；6c2585a结构化话语、接触事实、稳定放置及原始安排物理见证。有效完整pytest271passed/2skipped。没有新模型／数据下载、训练或临时smoke文件。

全部worker已terminal，无待回收：旧推理PID3629154/3629322、参考父PID3634992及新Tool PID3683588、Structured PID3733762/3733839均已ps核实不存活；不要重启。π PID2267256 GPU3 port8766、Vision PID3095303 GPU1 port8782、HTTP PID3054726 port8123仍alive，需要重新核实再用。

结果：
- init4／5六条：snack两条reference_complete=true；drawer两条true且真实包含；drink两条false。所有完整120秒，audit／process／2401帧video独立通过。参考人NN0，等待／清场独立来源，不算整条VLA或动态能力。
- reasoning_snack_join：H30/R30/VLA240；0.95秒进入早于19.5秒可用cue。32.45秒释放成品于delivery首次匹配，但108s改回serving_ready，116sreturn打断，终态持碗；不能据首次达成或语言自报称连续协调已完成。
- reasoning_drink_correction：VLA120，上架10.8s曾成立。37.5s柜顶个人用途cue，40s改公开需要、54.25s移动个人区完成，R44s后仍上架；后续反复取放。不是原生目标未成立就等于操作失败，也不是新的共同约定被接受。
- joint_tool_drink_correction_20261008：schema6，26/30parse failures，结构化message导致整选择拒绝；实际VLA0、合法后段relocate才放下酒瓶，NN错误完成人理解仍有。完整输入token／工具历史／控制／视频核验通过，保留接口诊断，不算可靠伙伴。
- joint_structured_tool_drink_correction_20261008：schema7，H30/R30/VLA64，0执行拒绝；10次action=accept被原身体动作枚举拒绝（不是done，已核对raw并修正文档）。10.6s上架曾成立；96s声称柜顶完成并away，终态实际wine contact=table，held=None，97.2s退出未返回。人自己已公开需要柜顶，却误用位置／声明；当前安排未验收。
- joint_structured_tool_snack_join_symbolic_20261008：schema7，H30/R30/VLA96，0parse、3执行拒绝no_held_object（0/8/44秒place）。9.1s真实填装、27.8s释放成品于delivery，120s及末一秒持续匹配；机器人后续确认并hold，人wait保留可用性。首次神经共同活动完整物理链维持正例。Human0秒已选active，身体32.95入、57.2退出，不据此计通知后才开始合作或完全可靠。NN策略真实决定，未后台选择正确下一策略。

实现边界：
- ToolJointHumanPolicy用本地Qwen自带Hermes原生tool_call／tool_response，最近四个实际交互＋六条自选非空私人记忆；一次thinking4096，实际message/tool输入和完整token逐条保存。接受不等于完成，反馈只有实测执行与事实，无评分、未来cue或下一动作教师。schema6/7独立token重建已全部通过。
- StructuredToolJointHumanPolicy只转发明确message/message_kind对象或原字符串，拒绝未知私有嵌套字段／冲突，不重选动作。原始参数留在工具历史，canonical公开speech与执行choice留在记录。人额外获当前真实物体接触实体（不是完成谓词），源码中实际输入与保存private_input一致。
- SettledPlacementHuman是独立低层类，只兑现已选relocate；释放支撑且速度<.02m/s、XY<.01m/Z<.025m时满足已在目标的请求，容纳实测18mm沉降，不改目标、不抓回、不写R状态。显式return即使物品已到位仍连续执行。原KinematicHuman未改，旧结果版本保留。
- joint_process_metrics新增original_arrangement_physical_observations：原生关系、释放（碗和内容都不被持有）、接触及原目标。当前安排评分仍None，不以旧目标匹配给cobalance或新用途成功。该函数只在离线evaluate使用，不给策略馈送。

已发布：42视频=41完整120s＋1早期partial；42全独立decode/timeline及浏览器play/seek/Range206、382links、375px、JS0error通过。dataset41完整、12000观测、98400实际7D动作，全加载／唯一ID验证。无formal split或成功专家标签，参考/失败/保持来源清晰。报告pending=[]，所有本轮结果及失败保留。每重要case有assistant_review_of_saved_records_not_human_study复核，不伪装真人研究。

下一步必须从实际任务／伙伴接口推进，别继续同一字段的小版本空转：
1. 人表达“放物”和“接受/拒绝/结束”等高层贡献与沟通，不应被迫学单手pick/place微步骤；实际三次no_held和10次accept提供直接证据。设计一次统一的自然贡献／沟通接口，策略仍由NN选，执行层可靠兑现；不能靠固定状态机安排人的下一策略，也不能自动判完成。
2. 现有_home只是初始位置标记，不能承载on-cabinet等真实关系目标；提供实际场景可用的支持面／区域，或明确由机器人完成的请求。不要把cabinet_home当柜顶，不反复修手指接触。
3. 先补三活动的可信伙伴和六类真实情境，再冻结多系统、多init正式样本。已有参考可用性与神经完整物理链正例是前提，不等于动态人研究全完成。保留原idea局部/长度匹配/复合/未见组合要求。
4. 所有实验现在已终态，核心源可在新批前合理修改；若启动新worker再次冻结加载源。每次GPU先nvidia-smi，单卡预算足够，不操作他人进程。

特别注意：此前长分析中大量重复、 speculative架构与虚构元数据名称不是代码或研究进展；只信实际文件、PID、日志和核验结果。不要延续那些分析，不新增无必要复杂类或列出永不执行的长计划。


## 接续：自然贡献／交流接口与真实支持面（fcc1dcd）

本轮progress：统一自然人贡献和沟通接口，真实柜顶碰撞目标，低层当前贡献执行、原生输入／几何独立核查与277测试，启动跨两活动新批。完整Goal仍active未完成；不complete/block。

- HumanDecisionPolicy/schema8，一次真实Qwen3-14B原生thinking4096，contribution与communication分别可空。place_object直接映射当前一次relocate，hold_object取来保留（已持有时明确停止旧放置）、step_aside/return/wait/indicate。accept/reject/request/finish等只转发NN原话；finish不标记环境成功或替伙伴同意。原始call参数保存，四实际工具交互＋六自选私人记忆，不选择下一任务。
- human_decision_interface移除执行菜单中的_home调试中心；真实柜顶每个物品的目标以g9实际碰撞顶面和物品当前碰撞底面／姿态计算。HumanSupportTargets来自几何，不是任务分数。CPU实际MjSim.from_xml_file已验证真实存档XML；不是mujoco_py（环境未安装）。独立audit使用robosuite绑定重建每次qpos的目标与全部NN输入token。
- ContributionHumanExecutor沿用连续附着、人速度.2；高目标运输抬升随目标位置，显式身体return/away不在身体未到位时完成。用户不需控制手指阶段。机器人仍实际π动作，不改R状态。
- 包括自然指令、接受/结束、私人字段边界、几何随姿态、保留中止旧放置和身体返回的六项新测试。全回归277passed/2skip（最终代码已复验），不是伙伴语义有效性的证明。

目前42视频／41完整／12000观测／98400实际动作终态产物不变，新条件只是pending。浏览器42全play/seek/Range、383links、375px、JS0error通过（增加自然接口协议链接）。未冻结正式split或样本统计。

必须按PID重新核实的两个live：
- joint_natural_drink_correction_20261008：GPU0，PID3891982，session8765，log data1/results/joint_natural_drink_correction_20261008.log。init3/seed65/particular/correction/120s；最新36模拟秒有家人柜顶用途后公开说明等待机器人放柜顶，但尚无终态，不能宣称成功。4/8秒尝试直接destination=wine_rack_1（物体非支持目标）被拒，意图是自己直接收纳，这属于未支持的具体目标／接口边界，不直接判策略或R失败。
- joint_natural_drawer_leave_return_20261008：GPU2，PID3892136，session57546，log同stem。init3/seed65/busy/leave_return/120s；最新28模拟秒出现未知贡献parse_error，原始保留，尚无终态。按实际raw解释，不泛称字段改善或伙伴已拟真。
- 两者人/协调每4s、Vision8技能库＋实际π，同一自然接口，无额外反思。GPU0/2启动前各48GB足够，H预算36.36GB；没动他人进程。
- π PID2267256 GPU3 port8766、Vision PID3095303 GPU1 port8782、HTTP PID3054726 port8123仍需再核实。此前所有workers已terminal，没有重启。

加载源冻结：main／humanDecisionInterface/Policy/supportTargets/contributionHumanExecutor／toolHuman及父类／Kinematic／native*.py／world／context／skill_bank及wrapper。不要改live加载的源。SourceSHA已记录本次全部依赖，旧版本不倒改。报告、审阅和独立审计可以继续。

Next：同PID/handle回收两条→audit（schema8、全部token、CPU几何）/evaluate/full decode→实际需求、伙伴回应、行为、终态分析→报告/导出/browser。六类实际覆盖、可靠人策略、完整动态重组、多系统正式矩阵及cobalance仍缺。

不要再把内部长分析中的重复元数据名、虚构架构或未执行设想当成进展。只信已提交源码和实际结果；不要继续单一枚举/小提示的无穷变体。未支持的关系目标、NN忽略接口及真实策略不一致应分开。下一次设计应依据实际raw、人的需求与场景可表达关系，优先三活动六情境完整链路。
