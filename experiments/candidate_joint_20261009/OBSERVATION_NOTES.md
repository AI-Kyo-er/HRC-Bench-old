# 观察记录

当前首例点心已有完整终态、输入／控制／视频核验，后两例继续。此前接口检查中候选点心帧仍提前报完成，饮品帧改选清盘，抽屉帧改等确认；这些接口帧均未执行，不能当本批效果。以下先保留运行初期的观察，再给出完整结果。

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

下一版[有限文本协议离线检查](../../results/candidate_joint_prefix_20261009/drink_output_protocol_36s.json)使用实际lm-format-enforcer 0.11.3：旧语法接受完整13288字符的未闭合前缀，有限文本语法在691字符位置要求结束引号，禁止继续同一重复字符串。限制自由话语、理由等文本长度，保留动作／对象／目标枚举；失败历史摘要只陈述实际回退及未公开消息，原始失败文本保留。该协议尚未接入当前运行，未生成新的NN调用或Sim行为，下一版实际资格仍待验证。当前批次继续冻结设置。完整测试379通过／2跳过。
