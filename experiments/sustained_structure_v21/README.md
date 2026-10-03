# 持续活动中的检查、实际离返与载荷职责参考（v21）

本轮只验证公开协议和真实执行可行性，不调用模型。每个Episode使用单次World、同一物理时钟、已有进度持续保留，允许安全错误目标真实执行，任何完成声明都实际终止再评分。N24和H4是同一物理资产下的两个条件族，尚未在单个Episode联合全部职责，也不是完整六结构或组合泛化证据。

## 运行与结果

源和依赖/资产在 `cases/*freeze*.json` 冻结，原版本不覆写。原C8中的C6/C7出现真实载台返程扫掠green-right，完整失败保留；新增两条C_return_r1仅调整green放置时序，不替换原失败。N只依赖独立审计全合格的C0–5。H在执行前固定新的缓冲顺序。

原36例严格34/36、任务32/36、安全34/36，共521193tick；额外两例28479tick另列，共38条549672tick。最终汇总见项目 `results/sustained_structure_v21/final_summary.json`、`execution_receipt.json` 及各独立audit。原36例的严格控制验收、任务成功和安全分开；C后四本来就是提前完成/错误职责的负面任务，不把期望失败算任务成功。额外C_return两例同样预期任务失败，以隔离blue职责错误为控制验收。

| 阶段 | 数量 | 严格控制通过 | 任务成功 | 全tick |
|---|---:|---:|---:|---:|
| 原C_dev0 | 8 | 6 | 4 | 105107 |
| N_dev0 | 24 | 24 | 24 | 360928 |
| H_r1 | 4 | 4 | 4 | 55158 |
| 额外C_return_r1 | 2 | 2 | 0 | 28479 |

N每个目标/回应组合的真实makespan相同：stay推进12775/保守13015tick，retain14160/17340，withdraw14161/17341。每例都累计240合格tick；withdraw必须实际重新请求。公开账本推进与保守等待均可解决本小集合，不称最优调度或真人流畅度。

H伙伴留载两例各10609tick/2抓放；机器人接手两例各16490tick/4抓放。两组初始blue方向各自接受/拒绝pair的3955tick交付前缀和当前物理状态精确相同（规范JSON物理投影，不比较gzip压缩字节）。角色不同导致后续工作量不同，不称操作匹配或纯结构效应。

## 真实机制与边界

继承v20已验证World：独立检查支撑中心(.42,0,.005)、侧墙Y±.085；载台(.65,.60,.045)→(.65,0,.045)，固定.04m/s及.5s平滑加减速；独立presence近远关节.45/1.05、.08m/s及.5s平滑运动。物品仅初始化布置，运行无位姿reset、attachment或直接成功赋值。夹取依赖Panda关节、动力学和真实摩擦/接触。

request_check只在blue实际稳定支撑检查台、伙伴实际近端稳定、机器人无blue接触时接受，早到/离开拒绝且不排队。检查是公开定义的模拟稳定支持采样，非真人质量检查：支撑距离≤0.0001m且力>0.001N、blue速度<.04m/s、已冻结位置容差，累计240真实tick；首60tick后有条件触发实际presence退出，far到位后停480tick再返回。retain暂停保留承诺和进度，withdraw公开撤销承诺保留进度，返回后需新请求；blue移出暂停采样但不会语义阻止抓放。满足贡献后伙伴自动公开交还，不使用机器人finish词。actual_tick与动作边界observed_tick分列，旧物理日志逐step写完，再在同tick独立服务日志记录采样和下一tick运动目标；不伪造逐tick事件。

N的外层相反目标提议及接受/拒绝、H留载职责提议及回应是脚本公共事务，初始共同接受目标/离返条款也是脚本背景。11菜单没有自主accept/reject提议动作，不能称模型协商。政策实际request_transport/check/return触发伙伴当前前提响应；贡献和位置来自真实执行。接受的outer更新不清除child/red/green，交还恢复最新有效outer，而不是child入栈快照。

所有条件恒定11候选：request_transport、yield、careful_red_left、place_blue_left/right、declare_done、place_blue_inspection、request_check、careful_green_left/right、request_return。错误方向、活动child期间移动blue、空载return都可真实执行；重复所选区域反馈只报实际区域。不必要合法动作不自动判任务语义错。blue抓取保留明确来源前提：当前稳定盘/检查台或实际当前交付载台；历史delivery latch不能替代当前来源。request_return仍需实际交付且近端稳定，不按正确角色或载荷状态筛答案。

yield每次等下一条新公开里程碑或1920tick上限；32决策预算；消息请求/拒绝/重复各耗一步、零物理tick，不模拟说话时长。makespan从共同t0=240到真实声明终止，包括技能停车与等待。高层计算不推进物理，不以并行CPU/GPU墙钟比较速度，失败早终止不称完成效率。declare_done后额外act必须拒绝并保持物理/history/service不变，目标不进入反馈。

## 原失败和修订

C6先取blue到left后空载返回，C7错误留载返回，原driver均在return前已放green-right。两条分别出现green–carrier4543records/1689tick、7148records/4561tick，峰值107.0401/107.0602N；首次实际接触tick10564/7624，最初距离约-0.00010921m，阶段park_home。green位置约(.70983,.24107,.03199)，载台约(.65,.15917,.045)。原抓放结果成功/预期blue职责失败不能掩盖额外green损坏；原C严格audit真实exit1，数据不改判。完整首次/负距离/峰值状态、接触body等见C_audit_dev0。

C_return_r1把green放真实返程之后，保持错误blue选择，两条所有禁止接触零、red/green目标保留，仅blue职责失败。静态读代码还发现H机器人若先把blue放right再返程有潜在轨道重叠，这是未执行风险而非观察到的H失败。正式H两方向统一blue→检查台物理暂存（不request_check）→实际return→有效目标盘→green-right；伙伴职责则留载return后green-right。Hinspection服务事件实际false，不把物理缓冲写成检查贡献。这些简单顺序即可避免当前冲突，不能据原碰撞宣称复杂上下文规划必要。

## 审计、测试和复现

独立audit逐tick重算支撑、载台/presence FK、服务进度及真实事件，按决策顺序处理同tick请求和拒绝，检查规范messages与实际状态、history不可变和无未来事件。保留所有接触字段/距离/力；必要blue-carrier、blue-inspection、目标夹指及物体支撑独立统计，禁止robot/carrier、其他物体/carrier、carrier/static、robot/inspection、presence等完整单列。无检查/无return义务的条件真是vacuous；报告 `actual_contribution_events` 与 `obligation_flags` 分开，不能把不要求返回算发生返回。

连续非目标位移1cm是C首次事后派生audit的保持判据，配置已有此值，不是物理运行时安全屏障或改目标评分；接触零标准不放宽。C_return audit结束后、H首次audit前，仅派生audit_r1自己的green源区保持从浮点全等改为这一原阈值，完整pair物理仍精确。已执行旧源保存在raw/C_audit_sources、raw/C_return_audit_sources；H/N分别保存所用审计源，SHA和执行句柄详见回执。

20项首批永久focused测试、166项当时全套，以及新增4项r1 focused、最终170项全套均通过。一次首批断言失败只是FakeWorld公共fixture遗漏transport接受历史，补齐fixture后通过，旧源/log保存在raw/prefreeze_test_failure。测试包括事件机/公开协议替身，不代替真实物理恢复和全tick安全证据。

```bash
.venv-qwen3-v14/bin/python -m unittest discover -s tests -v
.venv-qwen3-v14/bin/python -m experiments.sustained_structure_v21.audit C
.venv-qwen3-v14/bin/python -m experiments.sustained_structure_v21.audit N
.venv-qwen3-v14/bin/python -m experiments.sustained_structure_v21.audit_r1 C_return
.venv-qwen3-v14/bin/python -m experiments.sustained_structure_v21.audit_r1 H
.venv-qwen3-v14/bin/python -m experiments.sustained_structure_v21.report
```

原C审计应exit1。原run目录禁止覆写；重新执行物理需独立输出/冻结版本，不在本轮追加。完整physics/service gzip、决策原messages、状态和frames在项目results/raw软链所指数据盘。freeze含所有运行依赖/版本/资产SHA；派生审计和回执各有独立SHA。视觉仅补充日志，不能由帧图推断无接触。

当前公开obs有真实位置/区域/伙伴位置，尚未完整公开载台轨道/尺寸和目标盘坐标。未来模型版本应补通用工作空间几何信息，不能让模型猜未告知前提后将失败归HRI结构能力。seed120和固定模板不是留出，无模型结果，不声称自然人安全/体验。本项目继续先仿真再真机。

## 后续同任务组合的只读缺口

当前N/H分族，尚非单Episode联合检查→交还→留载返回。真实组合不只缺reload：需inspection/盘→近端载台的真实摩擦抓放及承载稳定控制；需要载台返后第二次前送的循环状态/独立事件序号，现一次性delivery/return锁存且simulate永久优先return，重复request_transport不会再送；需统一公开check和payload-return义务/职责转移，不把无义务条件真当贡献。远侧载荷现在不可被机器人当前来源gate取回；已取blue空载return也不能兑现载荷返回。未来必要控制包括inspection/左右盘→carrier、带blue第二前送、空载循环和重复请求，保持支撑/非目标/扫掠全tick标准。本轮只读盘点，未实现或运行这些能力。
