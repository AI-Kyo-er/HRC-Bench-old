# 观察记录

当前三活动均已有完整终态、输入／控制／视频核验。此前接口检查中候选点心帧仍提前报完成，饮品帧改选清盘，抽屉帧改等确认；这些接口帧均未执行，不能当本批效果。以下保留运行初期的观察及随后完整结果。

首例点心已启动并到3.95模拟秒。0秒实际人记录含v5测量与两次真实生成，选择Food→Bowl，没有公开话语。Robot0选择BowlOnPlate并公开说明摆盘，理由仍知道Bowl由人持有，memory_note却先写“Bowl placed”。这是选择与记忆中已完成表达的早期矛盾，不据此预判完整行为，也不将执行选择当成功。

源记录在candidate_snack_detour_symbolic_20261009/episode的human_policy_io、robot_planner_io和trace；运行初期曾持续增长，现首例已终态核验。没有让后台改成另一策略、强制发消息或按预设成功路由。后两例仍须完整运行与视频核验，正式样本0。

## 点心前缀：实物进展、有效请求与过早完成

以下均为模拟时间。记录仍在增长，不能作为120秒完整结果。三个前缀快照保留原始JSONL非空行序号、行文本SHA256与内容；33条来源记录已逐条独立重读核对。见[12秒协调](../../results/candidate_joint_prefix_20261009/snack_coordination_12s.json)、[16/20秒食品放置](../../results/candidate_joint_prefix_20261009/snack_filled_bowl_20s.json)、[32至64秒公开目标与操作](../../results/candidate_joint_prefix_20261009/snack_public_goal_operation_64s.json)。来源核对证明记录一致，不认证语义或协作成功。

- 8秒，人持有食品，公开请求Robot暂停盘子操作，直到食品放置完成。Robot4秒已经hold，不能将其首次暂停归因于8秒请求。Robot12秒重新选择bowl_on_plate，其理由却把仍持食品的人写成持碗；实际自身夹爪接触列表为空。这说明可用线索并未可靠约束生成的执行理解。
- 16秒，人说“即将完成”，实际仍持食品且正在下放；该句没有提前声称已经完成。20秒食品已离手并由碗支撑，人选择将装好的碗移至交付区。不是仅有意图文本变化。
- 32秒，人说“碗已准确放置”“任务完成”，实际仍持碗，执行阶段transfer_lower，碗中心z=1.0686米。此时XY已接近交付点，但还未落桌、离手。v5清除载荷的错误离手事实后，NN仍可能将XY接近误认成完成。
- 36秒，碗已离手，中心约(0.2800,0.4500,0.8984)，食品仍随碗在交付区。40秒人执行idle。这是人执行层的物理进展，不意味着Robot完成了摆盘。
- Robot32至52秒反复等待最终确认，而人32、36、40秒均公开表达完成；Robot的理由还说已经把碗放盘，但实际盘子仍在另一处。这是过时约定与事实误记，不能因为有对话就计有效协作。
- 人40秒公开提出Robot可转饮品准备，60秒明确请求将酒瓶移至drink_staging。Robot60秒选择bottle_on_rack并生成“put the wine bottle on the rack”，公开话语和current_goal却说移至drink_staging。64秒仍如此。实际公开操作库只有放酒架/柜顶等原生操作，没有移至drink_staging的操作。酒架与饮品区不同，此处不能把选中另一技能解释成完成请求。
- 人64秒说“wine_bottle_1正在移至drink_staging”，但酒瓶在60与64秒坐标相同，Robot64秒的自身夹爪接触为空。尚未建立真实持瓶证据，不能计其为已经开始有效转移。

本前缀支持：人已经产生物理贡献，并公开改变需求；Robot据公开请求改变了所选操作。尚不支持：有效摆盘、饮品请求被兑现、完整双向重组成功或候选伙伴已合格。主要新增设计约束见[能力与共同任务边界审阅](CAPABILITY_REVIEW.md)。本批模型与运行设置保持冻结。

## 首例完整120秒：视频、行为及评价边界

输入／控制核验和完整2401帧视频核验均verified，相关源码运行中变化为空；v5、32B-AWQ及FP16事实由保存provenance核对。人16次双阶段决定、32次NN；Robot30次协调和64次实际VLA，2400步控制，人执行拒绝0。这里的核验不证明真人拟真或有效协作。

[12项行为审阅](../../results/continuous_v2/candidate_snack_detour_symbolic_20261009/public_request_response_review.json)及[引用核对](../../results/continuous_v2/candidate_snack_detour_symbolic_20261009/review_evidence_verification.json)已发布；[5个过程区间](../../results/continuous_v2/candidate_snack_detour_symbolic_20261009/reviewed_coordination_metrics.json)有源锚点和实际控制时间。36至56秒有20秒保持，不称有效确认延迟；68至72秒有4秒保持及人反馈，不称此前饮品安排已经成立。

原安排物理匹配首次34.2秒，最后一秒持续成立，终态碗／食品均释放。装填与交付是人实际执行的贡献；原生食品入碗谓词为真不是Robot装填证明。summary给出的原生目标首次稳定17.45秒，当时人仍持食品transfer_lower，v5释放支撑为空；该历史字段不能直接成为释放／交付／Robot贡献训练标签。原始summary不覆盖，独立过程证据另列。

同资源VLA暴露11.85秒；人持物时Robot夹爪接触累计0秒。暴露不是碰撞标签，夹爪零接触不是全身安全。身体离返区间为空，本例不认证暂离返回能力。撤回饮品的68秒公开线索被Robot同轮读到并选择保持，72秒人认可暂停；承认局部链路，同时保留早报完成、过时等待和操作目标错配。

已从原始视频保存并查看[32秒](../../results/candidate_joint_prefix_20261009/visual_review/snack_32s.png)、[36秒](../../results/candidate_joint_prefix_20261009/visual_review/snack_36s.png)、[72秒](../../results/candidate_joint_prefix_20261009/visual_review/snack_72s.png)三帧，完整视频在[index.html](index.html)。这些是原始Sim视频取帧，供行为审阅保留，不替代完整视频或定量接触证据。正式样本0，后两例不预判。

## 放置释放的独立重建

[释放核查](../../results/continuous_v2/candidate_snack_detour_symbolic_20261009/released_placement_audit.json)绑定保存的公开食品入碗目标，叠加人明确持物／载荷归属和原始手部接触，重新累计0.2秒稳定时间。原始记录首次成功17.45秒，重建后的食品释放稳定首次18.35秒；完整点心交付首次34.2秒是另一项条件。115个采样状态与原成功标记不一致，其中111个仍有人持有或随人携带，包含搬运装好碗时的食品载荷；这些是同一条运行的采样状态，不是115个独立实验失败。

核查只输出放置释放事实，Robot贡献和正式分数均为null；不改原始summary，不写策略输入。中断或不满预定步数、缺载荷归属、目标对象不对应、源文件版本变化时拒绝认证或展示。新增8项测试覆盖直接持物、载荷、所要求的容器释放、真实手接触、稳定时间重置、公开目标绑定、终态及来源变更。完整测试373通过／2跳过；更新后的候选报告1视频／23链接浏览器通过。

复现：`PYTHONPATH=src .venv-libero-native/bin/python scripts/audit_released_placement.py --input-dir results/continuous_v2/candidate_snack_detour_symbolic_20261009 --object-id cream_cheese_1 --receiver-id akita_black_bowl_1`。其他任务须匹配自己的公开放置目标；抽屉开合不是放置，不用此核查替代关节评价。后续若导出完成标签，应从已核验观测重建，不能直接把旧summary字段当Robot完成标签。

## 饮品运行中：持物、请求与实际提供

[0至35.95秒的12条来源快照](../../results/candidate_joint_prefix_20261009/drink_resource_transfer_36s_prefix.json)已逐条重读并核对行文本SHA256。尚无完整终态，不计纠正接管或共同任务成功。

- 人0、4、8秒实际持酒瓶并选择wait，同时要求Robot放酒架。Robot输入包含人持酒瓶，仍选择bottle_on_rack，没有先提出提供／释放请求；资源仍由人占有。8秒Robot实际夹爪接触是flat_stove_1，不能当已经接手酒瓶。
- 人28秒的实际生成工具调用自己选择wine_bottle_1→wine_bottle_1_on_cabinet，公开话语仍要求Robot放酒架，理由还说临时柜顶会冲突。不是后台把酒架路由成柜顶，归一化只补memory。是否为合理暂放以供Robot后续搬运，需要实际释放和公开分工证据，不能先认证接管。
- 35.95秒人仍持酒瓶transfer_translate，位置约(0.036,-0.240,1.290)，尚未柜顶放下。Robot32秒继续酒架操作。后续私人用途变化的实际机会与双方响应继续按同一版本核对。

## 饮品36秒生成失败及后续公开纠正

[36／40／44秒的10条来源快照](../../results/candidate_joint_prefix_20261009/drink_correction_delivery_44s.json)已逐条重读与SHA核对。36秒意图层已根据35.6秒私人信息更新为柜顶立即取用，但贡献生成在communication.text中反复重复，4096个实际生成token用尽（611个思考、3482个JSON及封装）。实际JSON字符串未结束，parse_error为Unterminated string；没有有效工具调用。原先拟生成的pause_current及纠正话语都未执行／发出，实际回退wait延续28秒的原搬运。因此不能从私人35.6秒或失败36秒话语计算Robot忽视纠正或响应延迟。

40秒人发出有效的柜顶立即取用说明，实物已由人释放在柜顶；Robot同轮hold并要求澄清原酒架安排。44秒人再次明确酒架信息过时、立即取用且不再需要该物品动作。Robot直到60秒仍重复澄清。保持减少了继续执行旧操作，但是否更新当前约定与理解要继续审阅，不能仅由hold认证成功。

独立输入审计现重放并核对真实解析错误、空工具调用和实际回退，生成失败的证据可以完整核查；它不将失败输出改为有效策略。错误计数与报告中的生成状态单独展示。首例重新核查仍verified、生成错误0，其释放派生证据也按新核查文件SHA重新生成。

下一版[有限文本协议离线检查](../../results/candidate_joint_prefix_20261009/drink_output_protocol_36s.json)使用实际lm-format-enforcer 0.11.3：旧语法接受完整13288字符的未闭合前缀，有限文本语法在691字符位置要求结束引号，禁止继续同一重复字符串。限制自由话语、理由等文本长度，保留动作／对象／目标枚举；失败历史摘要只陈述实际回退及未公开消息，原始失败文本保留。这一离线阶段没有新NN调用或Sim行为，随后一次真实贡献生成见下节。协议未接入当前Sim批，完整伙伴资格仍待验证。当前批次继续冻结设置。完整测试379通过／2跳过。

## 下一版一次真实贡献生成：接口通过，闭环仍待验证

[实际接口报告](../bounded_human_interface_20261009/index.html)在独立GPU0使用同一冻结32B-AWQ，重放36秒的实际输入及已生成私人意图，新seed14136。实际生成568token，JSON与工具解析通过，思考未强制关闭，生成约96.57墙钟秒，模型加载另计7.13秒。独立来源／输入／全部实际token／解析核对通过。

新选择是人自己Wine→Cab，同时公开请求Robot放Cab，符合柜顶立即取用方向；这仍有同资源分工不明确的问题。没有执行新Sim动作，没有新方法自己的持续历史，也没有认证Human伙伴可靠性或因果改善。原失败历史摘要未涉及本次36秒输入，不能借本样本证明该摘要的效果。检查进程已退出，nvidia-smi确认GPU0只剩15MiB背景占用；GPU2/3继续原三活动批。

当前原饮品例到83.95秒，64秒再次记录Unterminated string生成失败，回退wait无公开消息。保留原失败，下一版方法只作为待完整闭环资格的候选；不改本批原始结果或设置。

## 饮品完整120秒：物理结果、生成状态和公开衔接

[完整13项审阅](../../results/continuous_v2/candidate_drink_correction_symbolic_20261009/public_request_response_review.json)、[来源核对](../../results/continuous_v2/candidate_drink_correction_symbolic_20261009/review_evidence_verification.json)与[4个过程区间](../../results/continuous_v2/candidate_drink_correction_symbolic_20261009/reviewed_coordination_metrics.json)已发布。20次人NN、30次Robot协调、80次真实VLA、2400控制步；4次贡献JSON未闭合（36/64/84/104），执行拒绝0。完整2401帧／20FPS真实视频核查通过，相关源码运行中变化为空。

38.45秒首次观测酒瓶已离手并与柜体接触，120秒仍在柜体上释放支撑。原生Rack目标False不代表更新Cab用途必然失败；实际搬运从28秒开始，不将其全部归因于35.6秒变化。人40有效公开Cab立即取用，Robot同轮hold，理由和memory_note已包含新用途并说当前位置正确；公开澄清却重复到116秒。100秒理由进一步认为无需Wine动作，message仍旧。这是生成字段／控制／公开反馈不同步，不能说模型完全没读到更新。

44至100秒56秒实际hold、40至116秒76秒实际hold只是所标过程窗口，不认证有效响应延迟或一致约定。64/84/104无有效公开消息，不拿失败草稿当新提醒。累计同资源VLA暴露38.4秒、夹爪接触人持物0秒；没有身体离返，不代表全身安全或离返能力覆盖。

已查看原始视频[0秒](../../results/candidate_joint_prefix_20261009/visual_review/drink_0s.png)、[36秒](../../results/candidate_joint_prefix_20261009/visual_review/drink_36s.png)、[44秒](../../results/candidate_joint_prefix_20261009/visual_review/drink_44s.png)及实际[初始策略图像](../../results/continuous_v2/candidate_drink_correction_symbolic_20261009/episode/observation_000000.png)。[相机与真实碰撞几何记录](../../results/continuous_v2/candidate_drink_correction_symbolic_20261009/target_camera_probe.json)重建XML/qpos缓存帧并核对物体位置：0/28秒Wine碰撞包围盒在外部、腕部两路提供相机视锥外；36秒外部相交时仍持物；40秒外部相交、腕部跨相机平面为未知。包围盒相交不证明可见或无遮挡，投影坐标在图像翻转前；翻转不影响是否相交。

因此，早期VLA执行不能直接作为正常可见可用条件下的上架能力证据；高层提供／资源协调和下游视觉条件分开。完整Sim视频在[index.html](index.html)，原三活动方法仍冻结，抽屉继续，正式样本0。

## 抽屉前缀：真实依赖与暂停恢复

[0至36秒的17条来源快照](../../results/candidate_joint_prefix_20261009/drawer_pause_resume_36s.json)已独立重读与行SHA核对。第三例仍在运行，不计终态或完整离返覆盖。

Robot0秒选择实际开中抽屉，原生关节稳定见证首次11.3秒；12秒人观察到0.160米可达开口，自己选择Cream→drawer_storage。随后16/20/24秒自己的执行测量分别为pick_approach、pick_lift、transfer_translate，Robot16秒之后保持并公开说明是人处理。人这几轮却把自己的搬运归为Robot。实际跨主体依赖成立与自生成角色理解错误须分开，不抹掉真实开门或给Robot记人搬运贡献。

本例实际紧急联系通知22.6秒，后续结束消息59.2秒。人28、32秒选择pause_current，保留持Cream，原motion请求3取消；Robot28秒公开认可暂停，但其16秒已hold，不能将首次保持归因于28秒请求。人36秒选择重新放置，Robot公开认可恢复，同一世界保留已打开抽屉和手中物品，未重置任务进度。

人36秒理由说联系已处理，尚未收到59.2秒后续消息；允许模型自主恢复，但这不是被外部结束消息触发的返回，其自述依据待审阅。0至43.95秒身体仍在[0.25,0.6]，没有实际旁移／身体返回。操作参与暂停8秒与身体离返不是同一证据。

43.95秒Cream已离手、与柜体接触，Robot夹爪未接触该物品。完整内部包含、终态稳定、后续Plate需要及电话结束后的处理继续等完整轨迹核对，当前不得先认证整个存储／动态协作成功。

## 抽屉前缀的声明区域与贡献归属

[七帧独立几何重建](../../results/candidate_joint_prefix_20261009/drawer_declared_region_56s.json)保存0／12／28／36／43.95／48／55.95秒的原始行SHA、保存XML哈希、重建帧及碰撞盒八角点。使用资产原有`wooden_cabinet_1_middle_region`箱形site，未围绕结果拟合目标区域。43.95、48、55.95秒Cream完整碰撞盒在该声明区域内，距最近边界约2.47毫米；人已离手，原接触记录是Cream真实碰撞盒与中抽屉底面g27。28／36秒也在区域内，但仍由人持有，不计已释放存物。这里核对的是声明区域内碰撞盒包含，不能扩展为视觉mesh／完整抽屉结构安全或120秒终态认证。

人44秒选择Plate→个人位置，但回执`already_at_requested_supported_position`：盘子已在先前自动暂放的个人位置，此次没有新增搬运。48秒人公开说全部完成；此时有Cream声明区域包含／底面支撑及Plate先前清理的实际证据。Robot开门与Human存物、自动暂放和后续无运动请求分别归因。正在运行的后半段、身体离返及后续私人消息仍待完整审阅。

## 内部理解与实际贡献进一步审阅

36秒意图输入own_execution明确actor=human、持Cream、当前运动已取消，并有Robot32秒公开说Human持物暂停；同次生成的private_memory仍说Plate由自己持有、Robot未执行动作。60秒生成的understood_shared_arrangement又把Cream存入归Robot。身份和公开反馈已可用，仍出现旧解释延续，不把它归为没有通道或仅缺状态字段。

当前8项逐案例解释及4个过程区间草稿保存在prefix目录，真实字段均已重读；完整终态／输入／控制／视频核验前不发布正式案例量。详见[伙伴有效性与文献取舍](PARTNER_VALIDITY_REVIEW.md)。有限文本批仍需完整验证上述事实与主体理解，不由一次接口通过推断问题解决。

## 抽屉完整120秒：依赖、终态和接触

输入／控制／源码冻结核对及2401帧20FPS512×896完整Sim视频verified。18次人决定／36NN，30次Robot协调／24VLA，2400控制步，人解析错误0、执行拒绝0。11项解释与5个过程区间已核对来源，尚非独立语义认证。三活动现3/3完整，正式样本0。

原安排首次释放支撑物理匹配41.4秒，末秒持续成立；原生开门首次稳定11.3秒，两者不混为整个任务完成。41.4秒及119至120秒全部采样的22帧独立CPU重建，Cream完整碰撞盒在资产声明region内、离手并接触真实底面，最小边界余量约2.28毫米；不认证视觉mesh／全部抽屉结构或全身安全。

44秒Plate请求是既有位置满足，44.05秒完成的是请求11，同时原存物请求9取消；不是原搬运自然退手完成，不把summary的完成时刻直接作为一次真实放置标签。当前操作暂停恢复保留进度有证据，身体离返区间为空。

同资源VLA暴露0秒；实际保持时19.85至21.6秒Robot夹爪接触人持Cream共1.75秒。不测接触力、全身碰撞或合法交接，不能因没有VLA暴露而说没有接触。原服务已无客户端和GPU任务，2719139停止，GPU2／3分别15／17MiB背景占用；新批GPU0／1继续。

已查看原视频[28秒暂停](../../results/candidate_joint_prefix_20261009/visual_review/drawer_28s.png)及[41.4秒释放](../../results/candidate_joint_prefix_20261009/visual_review/drawer_41.4s.png)，12／119.95秒原视频帧也保存；完整视频见[index.html](index.html)。[声明区域22帧核对](../../results/continuous_v2/candidate_drawer_leave_return_symbolic_20261009/drawer_region_verification.json)与[终态案例来源](../../results/continuous_v2/candidate_drawer_leave_return_symbolic_20261009/public_request_response_review.json)分别保留。
