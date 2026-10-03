# 同一World的真实载台重装与循环运输（v22）

本轮补齐v21检查与载荷职责未来组合的两项物理前提：blue从检查台/左右盘真实重装近端载台，以及保持历史的多轮前送/返程。8条均为指定控制，不是模型、策略任务或完整结构实验。没有调用GPU/模型/下载权重；仍先仿真后真机。

所有运行源码、依赖、资产、完整8序列和判据在 `freeze_dev0.json` 冻结；原v20/v21及其它冻结不改。独立 `CycleWorld` 一次初始化，每次运动只通过原载台电机/动力学和摩擦承载，抓放使用原Panda低层控制器，没有运行期物品reset/attachment/直接成功赋值。`carrier`新增释放姿态[.65,0,.073]通过真实抓放实测，不根据坐标推断成功。

## 固定控制和事件

A6是来源inspection/left/right×seed120/121：forward→red-left(careful)→实际交付→blue至指定来源→重装载台→带blue return→第二forward→第二实际交付→blueleft。每条10决策/4抓放；5条19981tick，一条A_left121为19982tick，实际端点稳定多一tick，如实保留。

B2是两seed：forward→red-first→交付→blueinspection→empty return→empty forward→重装→loaded return。两空载运动各经过1000tick时同向重复、反向拒绝；到位后各等待480tick确认无自动排队请求，再明确发下一请求。单次等待上限6000tick。每条19决策/3抓放/21722tick。

每次新方向接受产生单调leg_id，旧行程、请求和事件永久保留。forward仅当前远端稳定且无活动运动，return仅近端稳定且无活动运动。运动中同向重复只反馈already_running，不重启或重新接受；反向拒绝且不排队。完成后必须新请求才开始下一行程。每次接受、重复、拒绝各1决策0tick，不模拟交流时长。

运动沿原0.04m/s、0.5s平滑加减速曲线。完整曲线结束且实际端点误差<0.005m、速度<0.005m/s才产生carrier_arrived。payload_arrived另要求本行程请求时确有当前合格blue承载，且到位时真实支持、相对XY<.025m、相对Z在(.025,.035)m、blue世界/相对速度<.01m/s。载blue运动须等本行程载荷到位才结束；空载运动只等载台。空载到位后再装载不会回填旧行程payload事件，旧第一delivery/return字段仅历史兼容，不是当前来源或循环成功依据。

菜单/通用workspace在每步规范messages固定公开，含载台两端坐标/尺寸、检查台/盘坐标尺寸，以及right盘位于扫掠方向的限制。green保持源处直到所有循环结束；没有私有正确目标筛选。blue抓放只接受已核验稳定盘/检查台或当前近端承载，远端blue不能直接抓；重装还要求当前近端稳定。本低层版本对blue技能保留“载台无活动运动”的保守执行前提，未宣称运动中从无关支撑抓blue已验证。末blueleft/远端载荷只用于控制审计，不作执行门槛。

## 实测与复现

独立审计36741/PID176077真实exit0：8/8严格及安全、165251tick；全部9种禁止接触记录0，载blue运输支持81851/81851tick。26个行程产生26个carrier到位及22个payload到位，4个空载行程无载荷事件；共98决策/30真实抓放，green最大漂移2.47552e-11m。结果、全tick接触/支撑/事件/输入审计及真实句柄终态见项目 `results/transport_cycle_v22/control_summary_dev0.json`、`control_audit_dev0.json`、`execution_receipt.json`。运行44035真实exit0，8/8序列完成；安全/事件通过以独立审计为准，不能只凭skill success。

完整physics gzip、每步原messages/前后状态、接触距离/双方位置/力、关键帧保存在 `results/transport_cycle_v22/raw` 数据盘软链。规范完整物理投影复用已验证canonical函数，tuple/list仅容器规范化，不截字段/精度，不比较gzip文件字节。独立audit逐tick用实际位置、速度和接触复算承载/到位、原曲线命令、重建请求—回应和全部循环事件，并区分目标/非目标、必要blue-carrier/blue-inspection接触和全部禁止类别。

每个重装/抓放还核实际目标、真实指爪接触与抬升，不只核返回success。非目标区间保持阈值沿既有1cm，green持续源处保持；精确物理/input比较不放宽。独立标量事实复算因numpy与Python范数舍入差允许1e-12，布尔事件/来源、规范完整physics仍精确；此不是接触或成功阈值放宽。

10项新增永久反例测试检查循环历史锁存、不排队/重复不重启、空载不能继承payload、完整profile未完不能到位、当前承载失败、序列化容器等价且真实差异仍失败、远端/运动来源拒绝。它们是纯公开事实替身，不代替物理证据；最终全套180项通过（90219真实exit0）。没有为了观察结果新增条件或重抽种子。

```bash
.venv-qwen3-v14/bin/python -m unittest discover -s tests -v
.venv-qwen3-v14/bin/python -m experiments.transport_cycle_v22.audit
.venv-qwen3-v14/bin/python -m experiments.transport_cycle_v22.report
```

实际重装/返程/第二交付关键帧可看raw/dev0/A_inspection_120/frames/00005.png、00007.png、00009.png；B空返/空前送可看raw/dev0/B_empty_120/frames/00009.png、00015.png，重装及带载返程看00017.png、00019.png。图像只补充全tick审计。

原run禁止覆写既有dev0轨迹；新的物理失败修复必须独立冻结/输出版本，不能重新运行同目录。makespan是共同t0=240至固定控制序列结束，含技能停车/等待；不把并行CPU实现/审计的墙钟当团队效率。

通过这些控制仍不等于检查与伙伴接回已在同一活动真正组合。下一研究任务需将实际检查自动交还、最新outer/职责更新、留载/机器人接手及真实离返放入同一持续Episode，并保留公开账本/简单安全等待/暂存基线。当前只有两seed实例复现，没有模型、结构留出、自然人检查或安全验证。
