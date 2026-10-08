# 候选三活动运行中：任务与实际能力边界

用户要求继续完整Dynamic Human Policy HRC Benchmark。上一条只整理Goal文本，没有实现改动，按no progress处理；本轮依据实际进程和JSONL继续，不根据旧会话时间重启。

复查batch父2719750、首子2719751、π服务2719139存活。GPU2约43.9GB、GPU3约8.9GB；两者仍服务实际任务，不停止。首例candidate_snack_detour_symbolic_20261009已超过68模拟秒，未terminal。三例仍用同一冻结32B-AWQ/v5，人物及文字协调器同时变化，不作人模型大小的单因素结论。

新增原始快照snack_public_goal_operation_64s.json，与之前12/20秒快照合计33条JSONL非空行逐条重读、SHA及内容核对。repo results/candidate_joint_prefix_20261009是指向data1的软链接。快照来源可复核，不认证语义，也不是正式成绩。

实际发现：16秒人的“即将完成”与持食品下放一致；20秒食品离手、碗支撑。32秒人说完成时仍持碗transfer_lower、z1.0686；36秒才已离手，40秒idle。Robot32至52秒仍等待已有公开确认。人60秒请求酒瓶到drink_staging，Robot选bottle_on_rack/真实指令put the wine bottle on the rack却说到drink_staging；实际九操作无任意区域放酒瓶。64秒酒瓶位置仍等于60，Robot夹爪接触空，人仍说在转移。不能将此归成纯VLA协作缺陷或已完成动作。

新增candidate实验CAPABILITY_REVIEW.md：日常活动依赖与真实操作接口先对应；超能力需要允许拒绝、替代、请求人接手，不静默重命名技能。若核心任务需任意功能区放置，应接入/适配真实策略并验证，不能后台搬Robot物体补洞。此设计不把Benchmark收窄到九操作。OBSERVATION_NOTES、BATCH_REVIEW与HTML前缀解释同步，仍0完整视频/正式0直到terminal输入和视频核查。

下一步收齐同batch三例，不改运行模型/能力/提示；逐例区分伙伴事实错误、接口、执行和协调失败，检查全视频。之后落实可执行六情境与两实际不同系统。原idea结构关系与未见组合要求保留，不将六种生活通知视为结构覆盖。Goal保持active。

## 后续全局设计与模型适配核对

上一轮progress提交4855292。本轮同父／子／服务已复查live，并poll同session58742仍运行；首例推进至87.95秒，Robot84秒hold公开尊重人的暂停饮品要求。仍未terminal，不能重启或改已加载源码。

沿用academic-research-suite实验设计inline；已核对COOPERA3.2及官方HUMAN.md、HABIT官方工作链／可观察反应及训练README、HRIBench3–5节。整体DESIGN.md补入活动实例化、关键状态可执行性、生成式闭环、伙伴审阅、stem数据发布、正式评测六阶段。保持私有边界与同一世界；生活情境和结构因子分开，未见组合保留，不预设复合一定更难。

本地OpenVLA config.norm_stats只有libero_spatial；当前CASES三活动为libero_goal。直连ModelScope两个候选goal ID都404，仅是有限搜索未取到资源，未下载／绕行VPN，不能推断所有中国镜像都不存在。不同模型需适配依据与同任务操作资格；旧空间模型接入不能直接计两模型正式覆盖。文本／视觉协调＋同π可以明确不同系统比较，但不能称不同VLA比较。

README明确旧布局成功与新区域饮品失败不可混用，更新32B/v5已真实运行而非仅资产准备。报告链接完整设计和七项证据状态；不因文档、来源核对或浏览器通过mark complete。运行GPU仍有实际工作，保留服务到批次结束再及时释放。
