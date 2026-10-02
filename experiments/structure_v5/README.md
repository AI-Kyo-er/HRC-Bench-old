# 持续约定与局部指导的规则物理可行性

本轮先仿真，建立脚本已接受背景下的最小参考原型，未运行神经策略。本轮不是协商行为、组合holdout或泛化/因果效果证明。十个开发例复用真实Panda/Bullet摩擦抓放和运动伙伴占位代理，禁止运行期物品瞬移、attachment或直接写success；局部检查是依据实际blue区域触发的伙伴脚本，不代表自然人感知/行为或真人安全验证。

## 先发现并修复盘内返工缺口

旧SafeParkingWorld仅在搬运段绕行，从home接近已入盘物品的关节轨迹仍扫过伙伴。所有原始失败独立保留，版本没有覆盖：

| 控制开发版本 | 四例严格通过 | 真实抓放 | robot–partner接触tick | 说明 |
| --- | --- | --- | --- | --- |
| dev0：旧v3.2控制 | 2/4 | 7/8 | 649 | 右→左绕行抓取失败；最大normal force1464.69N |
| dev1：来源侧接近路径 | 3/4 | 8/8 | 357 | 高力approach已消除，但左来源link4仍有零力接触记录 |
| dev2：来源侧冗余IK | 4/4 | 8/8 | 0 | 保持占位几何，以第1/3关节rest偏置增加前臂间隙 |
| dev3：完整接触日志 | 4/4 | 8/8 | 0 | 与dev2动力学/控制相同，仅增加contactDistance和position_b |

四例为blue左→右/右→左 × 占位careful/实际释放后direct，seed40。每次先真实抓放blue入盘，伙伴电机进入占位；direct能力在占位时仅被几何安全前提拒绝，不能算观察到碰撞。释放或绕行后的跨盘抓放由真实位姿/速度判定。最终dev3全29520tick、原初始桌面来源六个绕行抓放20160tick，robot–partner及object–partner接触记录均0；初始来源6/6成功。末端到位和最终任务成功分别记录，不以waypoint误差代替物体进度。

`control_contact_audit.json`逐tick复核在线计数，并分别记录两类伙伴接触。正常指爪–物品、物品–托盘接触保留，不声称所有接触为0。dev0/1的object–partner均0，但旧trace缺contactDistance，dev1零力记录无法据此区分穿透、近零接触或正距离缓存记录；未补造旧数据、未事后放宽零记录标准。dev2也缺距离字段；最终dev3与初始来源回归所有接触均有距离和双方位置。

## 最小任务语义

每seed40/41包含A三例和B两例，共10例；goal方向和候选顺序随seed反转，两个轴耦合，不能估计独立顺序效应。所有A/B菜单相同：原20通用候选加`finish_guidance`，共21个，不按约定/scope/评分筛选正确动作。输入只含公开历史、实际物品位姿/速度、物理区域、伙伴位姿/几何阻挡和预算，没有免费归约后的exclusive/active/goals/已完成标签。参考策略只接收此公开观察并归约历史，固定顺序仅用于操作匹配；未用case隐藏目标或未来伙伴回应。

A的公共物理前缀为red真实入初始目标盘并停车，随后伙伴实际占位。预置已接受背景分别为exclusive（下一抓放前先yield）、shared（可独立careful绕行）和independent（无上述依赖的操作提醒参照）。同一占位的后续义务因此不同；exclusive可在yield后自由选余下物品和路线，shared可绕行任意物品或请求实际清道。参考本轮选择exclusive先yield、shared/independent直接绕行。每seed三个case的实际检查点和完整物理前缀轨迹精确一致；公开历史事件数均5，输入字符数最大差4，内容语义不同，不能称严格等信息。

B的nested是有作用域和终止条件的指导：blue暂存到外层目标相反盘→伙伴实际占位检查→先yield使伙伴实际撤离→满足局部检查→finish_guidance明确终止→恢复此前外层blue目标。green仍按外层分工，可在child活动期间完成；参考故意在finish前完成green，验证终止不抹除其他进度。局部finish不移动物体、不完成全局；blue随后必须真实再抓到另一盘。direct_return连续无依赖参照采用相同暂存/检查/finish/返工操作，但返回点直接给新的明确blue目标，移除“恢复旧目标”的信息依赖；信息呈现不同，不能称严格等信息因果对照。每seed两例检查点及物理前缀精确一致，事件数均4，初始字符数差6；后续完整低层序列匹配以派生审计为准。

最终只读审计确认B每seed两例的**完整物理轨迹**SHA也精确一致；A shared/independent完整轨迹亦一致。B检查点用已有VL tokenizer计算输入长度分别为1682/1681及1681/1680，仅用于长度诊断，没有神经模型调用，不表示等信息。所有34个规范messages与当步观察精确相等，历史均为不可变前缀，输入对象/伙伴物理状态在对应真实tick精确匹配。

## 实际规则结果与验证

代码/资产/依赖/10case在执行前冻结：`cases/reference_freeze.json` SHA `d201651e151abd64079834fa03f53a5e571ed81ece5e72b136699c8ffadc1876`。10/10通过任务及scope验收，110400tick两类伙伴接触记录均0；34决策、24策略抓放、0物理失败，公共前缀另有10次真实抓放。yield6次、finish4次、request_clear0次。

**请求清道替代合法分支没有在这10例物理执行中覆盖**，允许集合不等于全路径已验证。参考每例均第一步遵守相应约束，协议拒绝0；没有神经错误恢复或真正双方协商的证据。B四例green均跨child保留、scope结束、blue恢复/新目标正确；实际finish前后全物理状态不变，finish即刻全局成功均false，返工后才完成。不能从末态成功单独推断scope理解。

24项永久回归测试通过。新增协议测试用明确的FactsWorld测试替身验证未暂存/未检查的finish拒绝、重复finish拒绝不重复恢复目标、immutable history、green保留和blue恢复；拒绝不调用物理推进、不增加伙伴事件，消耗1决策/1finish并记invalid。替身不是物理仿真证据；真实规则轨迹验证了合法finish不推进tick，但这10例没有执行非法finish分支。`input_and_pair_audit.json`核验规范messages等于当步观察、历史不可变前缀和实际tick物理状态一致，同时记录token/字符/事件长度与操作匹配，完整原始轨迹/关键帧经`results/structure_v5/raw`访问数据盘。

关键帧：`raw/reference/A_exclusive_40/frames/00000.png`为占位检查点，`00003.png`为完成；`raw/reference/B_nested_40/frames/00001.png`为blue暂存+占位，`00003.png`为green完成，`00004.png`为finish后blue仍临时盘，`00005.png`为真实返工后外层完成。图像只能支持几何/末态理解，零接触依据全tick审计。

```bash
.venv-llm/bin/python -m experiments.structure_v5.controls_v3
.venv-llm/bin/python -m experiments.structure_v5.initial_controls
.venv-llm/bin/python -m unittest discover -s tests
.venv-llm/bin/python -m experiments.structure_v5.run freeze
.venv-llm/bin/python -m experiments.structure_v5.run run
```

所有入口拒绝覆盖已有输出/冻结。旧v3/v4结果没有修改。21候选和finish新动作改变了输入，旧14B40门槛即使通过也仅为旧接口初筛；未来神经评测前需要独立的新原子/进度能力校准，覆盖finish、green保留、blue恢复及自由顺序。未来指标需分别报告任务完成、首次受约束决策正确、协议拒绝与反馈后恢复、伙伴分支暴露；不能将纠错反馈帮助后的完成当作无帮助交互推理。当前不启动神经v5或真机。
