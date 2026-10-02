# 第七轮：独立neutral检查位置与首次blue返回选择

本轮只验证脚本共同背景下的任务协议、真实控制及首次选择的可辨识性，不运行神经策略，不声称组合泛化、模型协商或真人行为。保留v3–v6全部冻结与原结果；14B旧接口门槛仍未通过。此处新增22候选协议不能继承旧40调用的组成能力结论。

## 场景、能力与作用域

`NeutralWorld`只在初始化创建独立浅检查盘：中心`[.65,0,.005]`、底板半尺寸`[.06,.06,.005]`、两侧壁位于`y=±.06`；blue检查位置为`[.65,0,.036]`。盘与left/right外层目标无关。沿用v5 dev3来源侧控制、v3.2停车控制及真实Panda动力学/指爪摩擦；没有运行期物体位姿重置、attachment或设置success。物理区域由实际位置、速度和固定几何阈值判定，与历史目标无关。

22个候选在所有阶段固定公开：旧20动作、`finish_guidance`、新增1个`stage_blue_neutral`。后者只提供blue到neutral的专用暂存能力，不新增red/green暂存动作。菜单包含当前错误或不可执行动作，不能从候选筛选答案。伙伴是电机移动的占位几何代理，没有真人感知或搬运能力；占位影响公共中央路径的几何安全前提。阻挡探针是AABB支持的提前拒绝，没有执行碰撞；正常指爪–物品/物品–盘接触不属禁止记录。

顺序为：脚本red真实入left → 进入已接受blue局部指导 → blue真实暂存neutral → 伙伴实际进入检查通道 → yield令其实际撤离 → green在child仍活动时入right → finish终止child → blue恢复此前外层left/right目标并真实抓放。finish只变公开事件，不移动任何物体、不重述blue返回目标；red/green分工与已实现进度保留。局部检查通过以blue实际在neutral且伙伴撤离为依据，不直接完成全局任务。

blue外层目标left/right、seed60/61、菜单normal/reverse独立交叉8例；red固定left，green固定right。共同接受背景由脚本预置，不是模型亲自接受或协商。规则策略只读取公开观察并归约原始历史；`case`字段只用于场景初始化、离线记录和预算，不传入规范messages。观察仅含原始`history`、实际`physical`、几何`physical_placements`、剩余决策预算及完整候选；无phase/active/currentgoals/caseid/seed/历史长度标志。没有由隐藏评分目标产生的完成标签。

## 真实结果与匹配审计

| 验收 | 结果 | tick | robot–partner / object–partner接触记录 |
|---|---:|---:|---:|
| neutral→left/right × direct/careful，seed60低层控制 | 4/4；16/16真实抓放 | 51600 | 0 / 0 |
| 8例公开历史规则reference | 整段8/8；首次blue返回尝试目标正确8/8且真实放置成功8/8 | 102240 | 0 / 0 |

控制prefix含red/green进度、blue暂存、伙伴占位与撤离、占位时direct无执行拒绝及blue返回，最终其余物品保留。direct每例12780tick，careful13020tick。控制未启用渲染，不补造其关键帧。后续reference每例12780tick、5决策，24次决策期真实抓放加8次red公共前缀共32次。40决策中yield8、finish8、request0、协议拒绝0、物理抓放失败0、目标纠错0。没有把候选中存在request/assisted当作这些分支已被物理验证；伙伴占位期间neutral绕行抓取、任意自主物品顺序也未全部覆盖。

4组同seed、同菜单left/right配对均满足：到finish的原始全tick物理轨迹SHA精确相同（包括对象/关节/伙伴/接触），finish完整物理checkpoint精确相同；删整个history后的规范system/user messages逐字相同。finish前后物理不变、green在right且保留、blue仍neutral、两个case全局完成均false。有效blue返回集合分别是`{place_blue_left,careful_blue_left}`和`{place_blue_right,careful_blue_right}`，不相交；共同合法无物品推进yield保留。目标没有从seed、red/green或菜单顺序派生。

40步规范输入审计确认原始messages对应当步观察、物体位置/姿态/速度/伙伴位置与原tick一致、公开区域符合固定几何、历史前缀不可变、反馈恰出现一次、预算与完整菜单一致。接触记录均含contactDistance和位置对，在线计数与独立离线全tick审计一致。静态neutral几何由源码固定；原tick日志记录动力学实体，而非每帧重复静态资产。

## 首次尝试评分与能够证明的范围

评分定位**成功finish后的首次blue left/right放置尝试**，包含place/careful/assisted；错误目标被协议拒绝也必须记为首次尝试错误，不能改记为之后首个合法/成功动作。没有blue尝试记未作答/未推进。目标正确、实际物理尝试、放置成功、有效性及whole-task完成分别记录。finish后的yield/request等前置非blue动作及其目标揭示反馈次数单列。

`audit.first_return_audit`按决策序列定位finish，而非仅按tick：合法no-op/协议拒绝/finish均可能不推进tick。它报告finish后首次尝试之前的blue目标揭示反馈，以及首次尝试自身是否触发纠错。原Episode的`prior_target_corrections`是累计全部blue动作纠错计数（含child期间）；本轮全为0，审计另以finish后的窗口明确评分。后续神经评估应使用该窗口评分，不能把child的neutral纠错当作外层目标已被透露。当前非blue合法no-op不透露blue目标。

错误blue目标会被协议拒绝，并显式反馈当前已接受目标，不推进物理但消耗1决策、记1invalid和目标纠错；随后可重试正确目标完成整段。提前或重复finish同样不推进物理、不弹出第二层/改写目标，仍计成本。上述错误恢复仅由FactsWorld永久单元测试验证，**不是本轮真实物理错误恢复轨迹**；真实reference没有触发这些错误。

只读位置捷径检查：8条实际finish观测中blue均在neutral，旧“从left/right反盘”规则无定义；固定left和固定right各匹配4/8实际有效返回集合。这些是基于实际观察的首次选择诊断，没有新增盲策略物理rollout。两配对在history移除后输入一致而有效返回集合不交，排除了当前位置或固定seed/menu反推目标的旧捷径；无历史策略仍可能左右试错并利用纠错反馈或终止完成，因此不能断言它整段必败。

这是小集工程可行性和测量辨识性证据。只有blue目标字段的公开历史不同，left/right字符串长度也有1字符差异，并不称严格等token或等信息因果对照。新stage/finish与局部状态追踪仍需独立原子基础校准后才能考虑神经研究；本轮没有进行该校准，也没有继续模型调用。

## 文件与复现

- 冻结：`cases/reference_freeze.json`，SHA256 `c5e25a7966c027b9ab1918616bcd5fcfd023102ba56211ed6ed3ad66d843362e`。记录8case、22菜单system、源码链/官方Panda资产SHA、包版本及控制summary SHA。
- 小产物：`results/structure_v7/control_summary.json`、`reference_summary.json`、`input_and_pair_audit.json`、`execution_receipt.json`。
- 原始数据：`results/structure_v7/raw`链接到`/data1/sieniwgroup/sieniw/HRC-Bench/results/structure_v7`，含每例gzip全tick、原始规范messages/决策/成本、summary、执行日志与测试日志。
- 实际关键帧：`raw/reference/B_neutral_{left,right}_60_normal/frames/00000.png`至`00005.png`；00001是blue暂存后伙伴占位，00003是child期间green入right，00004是finish后共同几何，00005是blue分别返回左右。图像不能替代接触审计。
- 验证：新增5项focused协议/评分测试均为FactsWorld替身；一次全套30项通过。独立审计8例40步通过。补充按决策序列评分的回归后，最终5项focused再次通过；未反复重跑全套。详见执行回执的句柄终态。

首次运行依次执行（输出目录必须为空，冻结不得覆盖）：

```bash
.venv-llm/bin/python -m experiments.structure_v7.controls
.venv-llm/bin/python -m unittest discover -s tests -v
.venv-llm/bin/python -m experiments.structure_v7.run freeze
.venv-llm/bin/python -m experiments.structure_v7.run run
.venv-llm/bin/python -m experiments.structure_v7.audit
```

复核现有结果只运行audit；controls/run有禁止覆盖保护。PyBullet3.2.7、numpy2.5.3、CPU DIRECT、DT=1/240、solver迭代100，完整依赖/资产见freeze与receipt。没有启动GPU任务、下载或外部推理服务。
