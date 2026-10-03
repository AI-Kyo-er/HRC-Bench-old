# 第八轮：真实承载投递、机器人接手与协调成本

本轮实现了机械伙伴代理的真实blue投递，blue随后由机器人接手完成共同任务。规则参考6/6完成，共53730tick；共享许可下保守等待与并行策略使用相同red-careful/blue-direct控制，每个seed并行共同结束时间减少3180tick，即13.25秒。结果只验证开发实例的物理依赖、公开先后约束及协调成本机制，不声称新调度理论、组合泛化或模型能力。两seed是实例复现，非结构留出；没有模型/GPU/下载任务。

## 场景和自主贡献

独立v8保留v3–v7原冻结。伙伴是带prismatic水平电机的无侧壁载台，不是自然人动画。最终载台半尺寸`[.06,.06,.005]`，中心从`[.65,.60,.045]`向`[.65,0,.045]`运输；blue只在场景初始化布置在`[.65,.60,.073]`，靠重力/摩擦承载，无运行期reset、attachment或物品焊接。到位后机器人真实抓blue到left。red也到left，green未分配且保留。载台物理投递将远端实物移到机器人交接来源，机器人后续取的就是该blue，不是另一件替换物品。

运输在公共checkpoint自动启动，每个`simulate`物理step推进，包括机器人抓放期间；单线程共同仿真时钟实现同步动力学。yield只停车等待已在进行的运输，不启动/加速/跳过它，也没有任意yield罚分。固定nominal `.04m/s`、加减速各`.5s`（120tick）、匀速14.5s，命令总时长15.5s。速度与判据在开发前写入配置，后续未按收益增大等待。

实际交付条件同时要求：载台joint距目标小于5mm且速度小于5mm/s；blue相对载台XY偏差小于25mm、相对高度25–35mm；blue世界及相对速度均小于10mm/s；blue–载台实际接触距离≤0.1mm且法向力>0.001N。独立复算使用同tick joint和固定轨道FK、blue实际位姿速度及全接触点，排除blue掉地却恰落在目标附近。首次物理共同满足形成永久历史事件；机器人接走blue后当前支持条件变false，已发生交付不撤销。初始化远端承载不计交付。

本轮首次交付发生在绝对tick3895、共同t0后3715tick（15.479167s）。这是预先速度/位置阈值的首次满足，稍早于命令曲线完全停止；末段残余速度约4.83mm/s，未据结果改变阈值。blue交接控制以实际来源位置抓取，开放夹爪和接近期间运输命令仍按同一曲线结束。

## 开发失败和版本关系

| 开发 | 改动 | 结果 | 全tick |
|---|---|---|---:|
| dev0 | 载台中心z=.005，blue初始z=.033 | 0/3；right旧托盘挡住轨道，载台停在y≈.39499，交付事件始终null | 30780 |
| dev1 | 仅轨道中心抬至z=.045，blue初始z=.073 | 3/3；运输、串行接手、并行接手 | 20745 |
| dev2 | 仅载台位姿查询加`computeForwardKinematics=True` | 3/3；交付首次时刻及成本与dev1相同 | 20745 |

dev0、dev1原世界/config/controls及原始失败轨迹保留。dev0运输6000tick仍未交付；两接手控制继续探测底层抓放并能到目标，但缺交付事件，均严格判失败，不当作合法共同任务完成。dev0 carrier–static接触峰110.91N，故不能仅因robot–carrier零接触称运动通过。

dev0 transport_only的在线“相对XY误差”最大约0.167mm包含默认`getLinkState`缓存位姿滞后：raw link位置与同tick joint最大差约0.166696mm；离线当前joint FK口径的真实运输滑移约8.709µm。两个数字不能混称同一物理滑移。dev2改当前FK测量，最终6reference的同tick FK/joint位置误差最大约2.98e-8m（float32输出误差），运输中blue相对载台滑移最大约0.369µm，支持覆盖3715/3715tick、100%。dev2源码/hash独立于dev1，不能用dev1 hash代替。各版本数值见`control_contact_audit.json`；早期派生审计另保留`control_contact_audit_dev1.json`。

## 许可、参照与真实成本

冻结seed70/71×三条件：exclusive响应等待、shared保守等待、shared响应并行。响应算法只读公开原始已接受约定归约；保守算法是明确独立baseline，始终先等待。条件标签/caseid/seed/policy不在规范观察中。三条件同20公开通用候选，包含当前不可执行/错误目标动作，不按隐藏答案筛选。输入只含公开约定历史、实际物体/载台位置速度、固定区域、实际交付事件、剩余决策及菜单；脚本背景不等于模型亲自协商。

exclusive规定先稳定交付，再整理red/接blue；shared允许运输期间整理red，blue仍需稳定交接。所有真实参考遵守其许可。exclusive提前整理会被协议拒绝、消耗1决策且不执行物理，不把拒绝称碰撞；该违反约定分支只做永久FactsWorld回归，没有真实执行危险/违约动作。shared也保留合法yield，因此统一等待仍能成功，本轮差异来自实际等待与共同makespan。

| 每seed条件 | 顺序 | 实际等待tick | red技能/运输重叠tick | 闭环makespan tick / 秒 |
|---|---|---:|---:|---:|
| exclusive响应等待 | yield→red-careful→blue-direct | 3715 | 0 | 9835 / 40.979167 |
| shared保守等待 | yield→red-careful→blue-direct | 3715 | 0 | 9835 / 40.979167 |
| shared响应并行 | red-careful→yield→blue-direct | 535 | 3180 | 6655 / 27.729167 |

t0为公共checkpoint自动运输起点（绝对tick180）；闭环makespan计至最后blue释放、撤退和最终停车结束，**包含停车**。首次几何目标条件满足时刻另记`goal_first_ticks`，可能发生在夹爪尚未完全释放时，不等同闭环结束。53730总记录tick含6例初始化1080tick；共同t0后的总makespan为52650tick。18决策、yield6、request0、真实抓放12、协议拒绝0、物理抓放失败0。

重叠定义是red完整技能执行区间与t0至首次实际稳定交付区间的交集，包含动作停留与停车，不等于连续手臂速度活动或人体流畅度；原tick也独立确认并行red期间载台实际移动3180tick。所有条件交付物理事件完全相同，控制method/目标相同，不靠路线差或人工等待罚分制造收益。不证明所列策略最优；其他合法抓放路径、运输中截取blue及request/assisted分支未全部覆盖。

同seed三条件公共物理checkpoint及完整物理前缀精确相同；exclusive与shared_wait的整个解压物理轨迹也相同。shared_wait/shared_overlap初始规范messages相同，baseline算法选择有别。两组shared成本比较只是本实例实际机制，不作显著性/泛化推断。

## 全接触、输入审计与比较器errata

必要blue–载台接触独立统计，6reference共164520接触记录，绝不称“所有object–partner零”。禁止robot–carrier、其他物品–carrier、carrier–静态环境，以及非目标robot接触四组都为0；正常机器人抓目标物品/目标物品与盘接触保留。green从共同起点至结束最大位移约1.12e-11m，未收到机器人接触。每tick保留距离和双方接触位置，不删零力或正距离记录。

独立`input_cost_audit.json`核对6例18步规范messages、物体/载台状态与原tick、当前FK/joint、区域、菜单/预算、history不可变前缀与反馈、交付事件无未来信息，以及等待/技能重叠/闭环makespan。全tick独立复算首次交付、支持覆盖、首次目标条件、green轨迹，在线/离线一致。transport_only没有pickup，其`event_persists_after_pickup`标null/不适用；只有真实blue抓放成功的serial/overlap控制和6reference验证取走后事件保留。

**比较器errata**：冻结run的`exclusive_and_shared_wait_full_trajectory_sha_equal`实际比较gzip artifact SHA，gzip头mtime不同使两seed都false。原字段/原结果/冻结不覆写，也不重跑物理。事后只读审计对解压全tick规范JSON计算digest，并逐tick核对，两个seed物理等同均true。文件完整性仍用原压缩SHA；物理等同性采用`canonical_physical_trajectory_pairs`，不能混用。新增永久回归确认gzip元数据差异不算物理差异，而真实物体位置变化能被比较器检测。

## 产物和复核

最终freeze：`cases/reference_freeze.json`，SHA256 `fa1a1bb5a920291fbec893dab3cfac0f1092b147072d0381c5c6d91ed2acddb1`，记录6case、20候选system、最终dev2源码链、固定配置、包版本、Panda/plane资产SHA与控制审计SHA。`world.py/world_v1.py/world_v2.py`分别保留开发版本；正式只调用v2。

小产物在`results/structure_v8`：三版本control summary、contact audit、reference summary、input_cost_audit、execution_receipt。原始大数据通过`raw`链接到`/data1/sieniwgroup/sieniw/HRC-Bench/results/structure_v8`，含各开发版本失败/成功全tick、原始决策messages、关键帧和执行日志。

实际reference帧：`raw/reference/A_delivery_shared_overlap_70/frames/00000.png`初始远端blue；00001为red完成但运输未到位；00002稳定交付；00003机器人接blue后的最终。`shared_wait_70`同0初始、1交付、2red、3最终可比较。图像不替代全tick接触证据。

新增初版4项FactsWorld/固定profile回归及一次全套34项通过；测量修复后focused4通过；再增加gzip比较器永久回归后最终focused **5项通过**，未冒称已跑35项全套。FactsWorld是协议约束单测，不是物理执行证据。正式6例及当前FK/接触验收由真实PyBullet轨迹另证。

已有结果只读复核：

```bash
.venv-llm/bin/python -m experiments.structure_v8.audit
.venv-llm/bin/python -m experiments.structure_v8.reference_audit
.venv-llm/bin/python -m unittest tests.test_structure_v8 -v
```

首次执行使用controls_v2→控制审计→run freeze→run run；这些执行器禁止覆盖既有输出/冻结。环境PyBullet3.2.7、numpy2.5.3、CPU DIRECT、1/240s timestep、solver100迭代；完整配置/依赖/源码见freeze和receipt。本轮仅仿真，未部署真机。
