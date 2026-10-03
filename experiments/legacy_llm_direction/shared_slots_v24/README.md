# 共左盘与跨盘恢复能力控制（v24）

本轮只检验现有同一组合World中red/blue/green共左盘和恢复抓放，固定8条指定控制，没有模型、GPU、下载或策略选择。没有请求检查服务，不用v23检查/green-right的任务分数判定本轮能力；通过也不等于双目标结构比较成立。验证仍先仿真、后真机。

## 固定输入与物理过程

A/B/C/D各seed120/121，全部body同时存在，完整复用v23 CombinationWorld及原Panda摩擦技能、载台和平滑参数，运行无物品reset/attachment。presence留近端不运动、不接InspectionService回调。共同前缀为请求前送→red careful-left→等待当前实际近端载荷稳定及无活动行程→blue direct检查台→请求空载返回→等待当前实际far稳定及无活动行程。单次等待上限6000tick，过去到位事件不能代替当前事实。

后续A为blue-left→green-left，B为green-left→blue-left，C为blue-left→green-left→green-right→green-left，D为green-left→blue-left→blue-right→blue-left。blue全direct、green全careful；所有后半段carrier均须保持实际far且无active。红蓝绿物体沿固定各自槽位，但槽位间距只是一项几何配置，不能作为安全证据。C/D有意增加跨盘恢复，不与A/B比较策略效率。

低层blue仍有公开稳定来源/无活动carrier前提；安全但不符合v23旧green-right目标的green-left可实际执行。控制序列耗尽即结束，不调用declare_done，不读取私有目标提前终止或清进度。反馈与观测是当前physics、循环history和公开workspace，没有检查完成或正确下一动作标签。

## 冻结和独立验收

freeze_dev0.json固定全部8序列/配置、system/menu/workspace、运行/审计/测试和依赖源码、资产及版本。完整原始ticks、边界前后状态、控制messages及每步frames保存于results/raw数据盘软链。已有目录禁止同版重跑覆盖；若失败须保版本、定位后另冻。

审计独立复算平滑载台命令、请求/循环事件与当前载荷支撑，按决策顺序处理零tick事件；完整物理内容用已有canonical比较，不比较gzip字节、不丢接触或精度。当前载荷范数仅允许1e-12独立计算舍入差。每次抓放检查实际选定槽位/速度、托盘或检查台支持接触、指爪接触和真实抬升；仅动作返回success或末态在盘内不足。

逐tick9类禁止接触单列，必要blue-carrier/blue-inspection、当前指爪和物品支撑保留；机器人技能区间按当前操纵物品审计另两物持续位移，1cm阈值与旧版本一致。C/D必须在中间命令真实支持于right，再实际移动超过0.35m回left；没有右盘实际状态、只看末态或no-op均不能通过。还检查全阶段持续非目标保持和最终三物各自左盘支撑，不以v23完整任务成功命名结果。

新增8项永久测试是纯公开事实/审计反例：旧return事件不能替代当前far、near无载荷不能满足等待、正确坐标无支持/错误托盘不能通过、缓慢非目标位移不能仅凭末态通过、C/D必须中间实际目标与有位移。它们不是物理证据。初始8focused退出0，完整200项在句柄45474实际exit0（Ran 200/OK）；不为无改动重复测试。

```bash
.venv-qwen3-v14/bin/python -m unittest discover -s tests -v
.venv-qwen3-v14/bin/python -m experiments.shared_slots_v24.run --freeze
.venv-qwen3-v14/bin/python -m experiments.shared_slots_v24.run
.venv-qwen3-v14/bin/python -m experiments.shared_slots_v24.audit
```

## 实际结果

8/8指定控制完成，8/8独立严格与安全审计通过；158408个完整物理tick（含初始化）、72次控制决策、40次真实抓放。9类禁止接触记录全0，载blue前送的真实支撑29768/29768tick；空载返程没有载荷到位事件。每次目的区域和支撑、C/D中间right支撑及实际返回均通过。最大持续非目标位移`7.75743e-09m`，按技能完整区间从该段开始位置计算的邻物最大位移`2.77777e-09m`。这是所覆盖几何下的记录，不能作为真人安全保证。

| 序列 | 每例决策 | 每例抓放 | t0到序列结束tick | 每例等待tick |
| --- | --- | --- | --- | --- |
| A/B | 8 | 4 | 16501 | 4261 |
| C | 10 | 6 | 22861 | 4261 |
| D | 10 | 6 | 22381 | 4261 |

同seed四种序列的完整物理前缀到tick10621精确相同，包含全部接触和物理精度；两组SHA及逐例成本见final_summary.json。两seed只是实例复现，不是结构留出。两种首放顺序和两种恢复路径均实际覆盖，不把技能返回成功替代接触审计，也不把所指定能力控制称自主策略或完整共同任务成功。

运行57791/PID197868、独立审计73119/PID199234均已真实exit0；派生report也实际exit0，无活句柄。执行源freeze SHA为`04a4404a04dc36eb3f432fc06304bd47de046e58f0f6a39ff7961a200c82a748`，源码/资产未变。完整数据约121MB保存在数据盘，通过raw软链引用，精确字节、包版本、原始源/产物SHA和真实终态见execution_receipt.json。

report.py是冻结后新增的只读派生源，另有独立SHA：逐命令核验抓取前的实际来源支撑（首次源区按初始实际位置/静态接触，后续盘按前一步实际放置区域），并比较两seed各四序列的完整物理前缀；它没有修改原冻结业务/能力评分，也没有重跑物理。finalize.py在report实际结束后记录最终日志SHA/终态，保留report阶段原回执，避免把正在写入的日志前缀hash冒充完整文件hash。

代表原始帧：`results/shared_slots_v24/raw/dev0/A_120/frames/00008.png`为三物共左末态，`B_120/frames/00008.png`为相反首放顺序；`C_120/frames/00008.png`、00009、00010依次为green左→右→左，`D_120/frames/00008.png`、00009、00010为blue左→右→左。图像只补充全tick支撑/接触/位移证据，不能代替审计。

新增覆盖仍不能推出任意新组合路径均已验证，尤其“green从left到right且blue已在right”没有在本8条中执行；后续关系目标恢复还需自己的固定控制。也没有检查/职责更新、模型闭环、纯结构因果或真机证据。
