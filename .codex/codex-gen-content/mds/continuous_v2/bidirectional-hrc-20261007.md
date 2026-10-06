# 2026-10-07：视觉协调器与双向模型对话实测

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent（inline）
- Origin Mode: run
- Verification Status: UNVERIFIED（完整研究效度）；输入、决定、控制与消息有独立审计
- Version Label: bidirectional_hrc_20261007

上一goal turn为progress，本轮也推进了代码与真实实验。完整goal仍active。
务必保持短分析、工具驱动；不要在分析中反复写相同概念或无意义Metadata/Root/Field词串。

## 新增能力与算法边界

机器人视觉协调层使用已缓存Qwen3-VL-8B，GPU1；π0.5执行器GPU3；
Qwen3-14B人和真实Sim GPU0。无新增模型/数据下载。
首次服务加载缺torchvision，匹配torch2.6安装torchvision0.21，软件来自清华PyPI。
协调器使用3幅实际图片（本轮初始外部、当前外部、当前腕部）、自身8维状态、公开
任务/对话及它自己生成的历史。无理想物体坐标、私有人目标或任务评分输入。
机器人可自主选execute/hold并发消息，消息进入人的后续实际模型输入。
execute调用真实π0.5；hold是明确的零增量、维持开闭的控制原语，不是VLA推理输出。
无效输出的保护保持另外标记；三条实际运行没有这类拒绝。
plan只保留文字，不由程序自动路由或定时切换，评分器不选择策略。

这是一种新增层级算法，不能把效果算到原始π0.5。不因CLI model_calls字段兼容旧格式
就把所有控制块叫真实推理。actual_vla_model_calls、hold_primitive_calls、
robot_planner_model_calls分别计数，独立verifier也区分动作来源。

人的输入新增实际可见目标标记的形状、半径与object_center关系，避免只给一个点而
让人不知道目标是区域。没有给出私有完成/得分标志。算法、区域描述、30秒预算均改变，
本批与上批不作单因素因果比较。

## 三条完整实测

task2/init0/seed0，cooperative、episode记忆；20Hz，最大30秒。
协调每20步推理，VLA/保持块最多10步，完整物理与视频证据保存。

| 条件 | VLM调用 | 真VLA调用 | 保持块 | robot | human | shared |
|---|---:|---:|---:|---:|---:|---:|
| prepare_receptacle | 30 | 0 | 60 | 0 | 0 | 0 |
| shared_workspace | 30 | 16 | 44 | 0 | 1 | 0 |
| clearance_return | 30 | 10 | 50 | 0 | 0 | 0 |

三个视觉协调输出解析错误均0，保持全部为模型输出的hold，不是JSON保护回退。
机器人发话30/22/25条，分别30/22/25次人的输入确实包含机器人消息。
所有运动/显示、模型控制、公开反馈、物理完成与双向消息链路审计通过；任务失败不改写。
clearance_return中人away1/return1/observe1/push28，但未达到实际清离/返回任务条件。

## 有意义的失败证据

prepare初始空夹爪、尚无VLA运动调用时，视觉协调器就声称“已经拿着黑碗”，持续等待。
人的确认文字也可与实际盘子中心位置不一致：例如X0.110/目标X0.0716，仍在确认而未纠正。
shared先选取碗并调用16次VLA，再连续保持，人的推物完成但机器人没有完成合法放置。
这些是原始生成模型输出，不是实际动作事实，不叫协商成功或cobalance能力已验证。

## 报告、代码与下一项必要工作

报告`experiments/bidirectional_hrc_20261007/index.html`包含3段真实Sim与同步双方发话/理由。
浏览器3视频起播、消息同步、可见链接、375px无溢出检查通过，截图存数据盘。
关键代码323ec3b、7cf5fb8、0bf8463；审计`verify_robot_coordination.py`验证图像SHA256，
原始JSON选择、实际控制来源和消息传递，不能据此说模型理解已验证。
当前非归档回归150通过、2跳过；编译和diff检查通过。旧归档测试不在通过范围。
所有实验进程完成，自己的模型/HTTP服务在汇报前停止，用户COOPERA PDF不提交。

原始分工仍固定，不是完整角色协商；人只能受力推物/离返，身体显示不碰撞。
开放目标、持续世界、真实手/身体物理、更多任务与人格、统计协议、WLA评测仍未完成。
不要把本轮仅双向消息接通当成熟Benchmark，也不要连续换提示跑同一小问题。
下一步应从结构上分开“自己真正执行过什么”的反馈与生成的计划/记忆，明示自身
夹爪/执行状态等感知语义，防止未行动却自认为已抓持。同时完善人的操作执行和
任务表达，向真实操作、依赖、协商与持续场景扩展；不是用评分器替模型选择策略。
