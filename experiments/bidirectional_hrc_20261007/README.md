# 双向视觉协调与真实执行

[打开报告](index.html)。新增Qwen3-VL-8B机器人协调器，读取初始/当前外部相机、
当前腕部相机、机械臂自身状态、公开任务与对话；自主选择execute或hold并输出公开消息。
execute调用真实π0.5，hold为零增量与维持夹爪开闭的低层原语。
文字计划不由程序自动路由，无效输出保护保持单独标记，不算模型主动等待。

人使用真实本地Qwen3-14B选择推物、观察、离返等意图。新增的机器人消息进入人的下一次
实际模型输入，原始双方决定与公开对话全部保存。人的输入另提供渲染标记的实际形状/半径，
解释目标是有面积的区域与物体中心关系；不是私有得分或完成标志。

本组合是新增层级算法，不代表原始π0.5能力。相比上批，算法、公开区域描述、30秒预算都改变，
不作单因素因果比较。只有同一布局、一个合成人格与少量任务，不能当作通用排名。
身体仍为非碰撞骨骼显示，实际物体操作仍为受力指尖代理，完整手与身体动力学尚未完成。

## 场景与设置

- prepare_receptacle：人准备接收盘，机器人放置需遵守前置条件。
- shared_workspace：人移动cookies，机器人操作邻近碗与盘子。
- clearance_return：人退离后返回准备盘子，机器人需协调动作时序。

均task2/init0/seed0、20Hz、最多30秒；人episode记忆、cooperative。
视觉协调每1秒推理，VLA/保持块每10步重新执行。双方时机由模型选择，不由评分器安排。
机器人没有理想物体坐标或私有任务成绩；人使用理想几何与自己的执行反馈。
物体保持实际碰撞/受力运动，无吸附或控制期坐标写入，视频直接记录Sim。

## 运行与审计

模型均复用本地共享目录。没有本轮模型/数据下载；匹配torch2.6的torchvision0.21软件
依赖来自清华PyPI。视觉协调器GPU1、πGPU3、人/Sim GPU0，启动前必须检查nvidia-smi。

```bash
bash scripts/run_native_libero_server.sh
bash scripts/run_robot_coordinator.sh
bash scripts/run_bidirectional_hrc.sh
```

结果在数据盘`results/continuous_v2/bidirectional_hrc/<family>`，仓库软链接访问。
`robot_planner_io.jsonl`保存原始视觉模型输出、图像SHA256、公开输入、模式及指令；
`public_dialogue.jsonl`保存双方实际发出的消息；`model_calls.jsonl`区分学习VLA与保持原语。
`actual_vla_model_calls`才是真实VLA推理数，`model_calls`为兼容的控制块序号/计数。

原生控制/视频、人物、人的输入反馈、释放稳定判据继续独立核查；
`scripts/verify_robot_coordination.py`另验证初始/当前/腕部图像、模型原始选择、
动作来源以及机器人消息真的进入人的模型输入。核验通信链路不等于确认模型理解。

```bash
python experiments/bidirectional_hrc_20261007/build_report.py
```

## 当前边界

首条中协调器初始声称已抓碗，却只选择保持，没有任何VLA运动调用；
人的位置确认也可与实际几何矛盾。原始输出和物理状态并列显示，不升级为事实。
需要进一步区分模型自己实际执行的历史和生成的意图/记忆，改善感知可靠性。
原始分工仍固定，当前只是双向时序交流，没有完整角色协商、开放目标或持续世界。
完整Benchmark目标保持active，不能把新增协调器/消息链路当作完成。
