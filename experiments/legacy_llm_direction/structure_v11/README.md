# 第十一轮：活动局部指导期间更新外层约定

16条新真实规则reference均完成，首次blue返回尝试正确且实际抓放成功16/16。204480个物理tick中robot–partner、object–partner接触记录均0。八个timing配对的完整物理轨迹、finish checkpoint和所有实际primitive动作相同；区别仅为同一个公开提议/回应二事件块的位置。这是协议与物理承载可行性，不是模型效果、组合泛化或纯scope因果证明。

没有模型、GPU、下载或新的低层控制路径。旧v7/v8/v9/v10冻结保持原样，14B旧基础gate未通过的状态不变。新system明确最新有效外层语义，无具体合法action示例；不将未来新prompt成绩与旧v9作提示或结构的单因素因果比较。

## 16例与双层公开约定

独立交叉seed60/61 × before_child/during_child × accepted/rejected × initial_blue left/right，共16例；正常22菜单固定。red外层目标left、green外层目标right。提议将blue外层投递改到初始目标的另一盘，以保证是实际改变提议；接受后的有效目标与拒绝后的有效目标各自左右平衡。二元目标下提议与初始目标必然反向，此轮不含同目标重申或其他目标域。

公开事件为：

```json
{"kind":"update_proposed","proposal_id":"u1","item":"blue","destination":"right","content":"只调整blue检查结束后的外层投递；neutral检查与red/green约定不变。"}
{"kind":"proposal_reply","proposal_id":"u1","decision":"accept","content":"对该提议：接受。"}
```

目标反平衡；拒绝时使用reject与“拒绝。”。回应绑定尚未回应的proposal_id；提议本身不生效。独立dual-ledger只归约公开事件：接受修改outer.blue，拒绝不修改。child活动期间有效blue仍neutral，finish退出后取最新有效outer，不用进入child时的目标快照。red/green约定与物理进度不重置。重复finish拒绝，不能再次恢复旧目标或弹出作用域。

观察只含原始history、真实physical、几何physical_placements、剩余决策预算和完整候选，不添加active/scope/currentgoals等已归约答案，也不传case/seed/timing/reply标签。规则策略只读取公开观察；case只用于初始化及外生脚本安排。公开提议/接受拒绝由脚本注入，不是模型亲自协商或自然人的行为。

## 事件位置与机械匹配

共同机械序列为：red真实入left → 接受blue child → stage_blue_neutral真实暂存 → 伙伴实际占位检查 → yield实际撤离/检查通过 → green在child期间真实入right → finish → blue按最新outer真实返回left/right。

- before_child：red公共前缀完成后、accepted_child之前注入二事件块，实际tick3120。
- during_child：yield的实际撤离/检查/动作反馈之后、child仍活动且green动作之前注入相同块，实际tick6900。

每次注入前后完整实际状态精确相同，不推进物理tick，不消耗机器人决策。两事件作为外生消息数量单列，合计32；这不是自然交流延迟模型。机器人继续自主选物品的协议允许多解；reference固定先green后finish便于机械匹配。D3检查通过后提前finish仍合法，不把green完成虚构成finish前提。

实际finish后均tick9840、预算8、15公开事件，blue仍neutral，red-left/green-right已完成，整个任务仍未完成。同seed/初始目标/回应的timing对，非更新事件逐项相同、二事件块内容相同、事件多重集相同，仅块位置不同。新共同system下每组字符数4330相等；seed60为2090tokens、seed61为2089tokens，两timing及初始左右/接受拒绝均同token长度。

八个timing对的整个12780tick规范物理轨迹SHA也相同，不只相同末态或finish前缀。SHA对解压后的规范内容计算，覆盖对象/关节/伙伴/全部接触，避免gzip时间头造成伪差。接受/拒绝的八个配对finish物理同，而blue有效返回集合不交。共同合法yield/request no-op保留；错误目标仍被协议拒绝、消耗决策并显式反馈当前目标。因此首次未获目标反馈的选择与可借反馈恢复的整段成功必须分开。

## 真实结果与公开策略诊断

|验收|结果|
|---|---:|
|新规则整段reference|16/16|
|首次blue返回正确、此前无目标纠错|16/16|
|首次blue真实抓放成功|16/16|
|物理tick|204480|
|robot–partner / object–partner接触记录|0 / 0|
|8组timing完整物理轨迹/输入配对|8/8|
|接受拒绝同几何且返回集合不交|8/8|

80决策：stage16、yield16、green抓放16、finish16、blue返回16；48次决策期抓放加16次red公共前缀共64次真实抓放。协议拒绝、目标纠错、物理抓放失败均0；request0，不把菜单有request/assisted当作这些分支物理覆盖。finish前后green保持right，blue返回后任务仍按实际物体状态判定。

以下策略仅从实际finish观察的公开history计算一个blue返回choice，与公开有效集合离线匹配，**没有执行错误动作**。有效集合为place/careful_blue_目标；非blue或错误目标第一次尝试不会从评分中删除。

|公开历史策略|before_child|during_child|总首次返回集合匹配|
|---|---:|---:|---:|
|first_outer：始终取最初目标|4/8|4/8|8/16|
|last_proposal：忽略接受拒绝，取最后提议|4/8|4/8|8/16|
|snapshot_restore：child入栈快照在退出覆盖当前outer|8/8|4/8|12/16|
|last_accepted_outer：正确公开ledger|8/8|8/8|16/16|

这些是基于16实际检查点的实测计数，不是预设得分或整段失败率。简单last-accepted-outer解析能正确解决，应作为有效参照保留。多个接受更新的最新值保留和提前finish只在协议替身回归覆盖，不冒称16真实轨迹含这些分支。

## 验证、冻结及局限

新增六项永久测试均使用FactsWorld替身，验证接受拒绝、child保持neutral、更新只在实际yield反馈后出现、终止恢复最新outer/green保留、多接受更新不回滚、提前finish仍合法。focused6/6及一次全套52/52通过。首focused一次失败仅因为测试误将FactsWorld初始green期待为initial字符串，而该替身实际为None；修正测试断言，业务协议不因该失败改变，原traceback保留raw/focused_tests_attempt001.log。不将替身位置写入当作真实物理证据。

正式运行复用v7已验证neutral→左右direct/careful来源控制，几何、停车与摩擦控制源码未改。所有16reference新建独立Bullet实例实际执行，运行期没有物体位姿reset、attachment或直接写成功。

冻结前prefreeze_design_audit使用旧真实checkpoint承载拟议事件，只是设计检查。独立执行后审计重新核对16新轨迹80规范messages：当步真实位姿/区域、历史不可变/反馈一次、更新的实际到达时刻及无未来泄漏、预算/完整菜单、finish不重述目标、scope期间green进度保留、首次返回指标和全tick接触。最终all_passed=true，在线与离线接触计数一致，接触距离字段完整。

freeze：`cases/reference_freeze.json`，SHA256 `3449cd36abb8a9d07b3534fd8e045a27c7c08fd2fe5d1c3ffa27919896570be5`，绑定运行依赖源码链、Panda资产/环境版本、旧控制证据、设计审计和CPU tokenizer资产hash。postfreeze新增audit.py、strategies.py、receipt.py只是只读派生审计，各自单列hash；没有改变运行评分/源码或旧冻结。

timing移动也改变消息新近程度与早期决策上下文。共同最终检查点等事件/等长度不代表全程等信息：before_child的前两决策已经包含更新，during_child前两决策尚未收到更新。这里只是单层child、一个正式外层更新，且脚本接受/拒绝，正常菜单固定、两seed实例复现；不是结构留出或一般组合泛化。单独接受/拒绝是约定维护；child活动期间接受外层变化、退出后取最新outer才体现跨作用域依赖，但仍容许简单正确ledger，不证明模型内部机制。

## 产物与复核

小产物为results/structure_v11的reference_summary、prefreeze_design_audit、input_and_pair_audit、public_strategy_diagnostic、execution_receipt；完整gzip全tick、messages、决策、成本和日志存raw软链接的数据盘目录。实际关键帧位于`raw/reference/B_update_{before_child,during_child}_accepted_left_60/frames/00000.png`至`00005.png`；00001实际占位、00002撤离后、00003green入盘、00004finish蓝仍neutral、00005蓝按已接受新约定入right。图像不能替代接触审计。

```bash
# 已执行；freeze/run禁止覆盖原结果。
.venv-llm/bin/python -m unittest tests.test_structure_v11
.venv-llm/bin/python -m unittest discover -s tests
.venv-llm/bin/python -m experiments.structure_v11.run freeze
.venv-llm/bin/python -m experiments.structure_v11.run run
.venv-llm/bin/python -m experiments.structure_v11.audit
```

freeze83101、真实reference97583、后审计23788均已续接确认exit0。无活run/audit句柄，无GPU/模型/下载资源占用；句柄与全部源码/资产/产物hash见execution_receipt。后续复现实验另建版本目录，保留本轮原始证据。
