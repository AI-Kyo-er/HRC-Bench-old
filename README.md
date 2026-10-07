# Human-robot Progressively Rebalanced Collaboration Benchmark

当前仓库同时包含 **VC + 配套 Genesis 的 v1 具身 pilot** 和 **HRC-Continuous v2 持续协作运行时**。v2 将人和机器人放在同一时间轴内逐 tick 推进，用可组合场景、动作块和公开观测测试合作如何随双方行为变化而重新组织。

研究对象是共同活动如何在指导、协作和干预交织时被重新组织。时长和模式切换次数不是第一版的主要变量；理解更新也可以发生在物体和人体动作尚未改变时。

新Goal已转向动态共同活动：人策略重在意图和参与，执行采用明确标注的连续运动学持物约束；机器人保持真实模型控制。三类活动已有完整可执行参考，其中抽屉／点心操作由实际π0.5完成，饮品成功参考使用既有轨迹反馈控制，当前机器人神经推理为零。神经开发出现实际用途修改，也暴露了重复搬运、过时安排和参与字段未兑现的问题；尚无完整Benchmark验收结论。

- [本轮可执行性与神经策略进展：真实Sim视频统一入口](experiments/joint_feasibility_20261007/index.html)
- [本轮关键行为、失败原因与证据边界](experiments/joint_feasibility_20261007/BEHAVIOR_REVIEW.md)
- [本轮设置、复现与七项Goal验收状态](experiments/joint_feasibility_20261007/README.md)
- [动态共同活动统一入口](experiments/dynamic_joint_activity_20261007/index.html)
- [与idea对齐的整体设计、信息边界及参考依据](experiments/dynamic_joint_activity_20261007/DESIGN.md)
- [实际进展和七项Goal验收状态](experiments/dynamic_joint_activity_20261007/README.md)

最新完成接触历史、空间动作与机器人活动数据学习：新增12条真实Sim数据生成轨迹、200步Qwen3-14B LoRA训练及三场60秒模型闭环实测，15段完整视频均通过核验。
独立场景只完成碗，两个共同活动机器人期末任务成立、人目标均失败、共同满足0秒；模型没有选择新增空间动作，尚未形成可靠交互恢复能力。

- [最新真实Sim视频报告：三场模型评测与12段数据生成](experiments/interaction_learning_20261007/index.html)
- [目的、设置、实际结果及限制](experiments/interaction_learning_20261007/README.md)

此前完成真实接触范例与神经伙伴动作学习：16条两物品教师轨迹、480对训练范例、实际Qwen3-14B LoRA参数更新，并完成3场神经资格检查与1场原生π0.5共同活动，均有完整真实Sim视频。
最终权重在未见init4的碗／酒瓶场景首次完成两物品释放稳定整理；未见餐盘组合和机器人共同活动仍失败，不能称为可靠通用伙伴或成熟Benchmark。

- [动作学习与闭环实际行为最新报告](experiments/human_action_learning_20261007/index.html)
- [目的、数据、训练、实际结果与限制](experiments/human_action_learning_20261007/README.md)
- [16条真实接触训练范例与核查](datasets/human_contact_teacher_20261007/README.md)

本轮已加入机器人活动范例和直接接触感知，实际效果见最新报告。没有实际发生的动态条件不计覆盖，cobalance构念及完整人体效度仍未验证。

此前完成联合意图动作推理的三场真实活动，以及修补后完整60秒自主操作复测，共4段运行时三机位Sim视频。
炉面场景出现3次自主目标集合变化，但人个人目标未完成；奶酪场景38秒从等待转为请求抓接收碗，实际没有人抓持碗的见证。共同目标满足时间仍为0。
发现并修补了旧放置请求在完成后重新启动的问题；真实复测321次缓存请求保持终止、没有原先的重启见证，但人仍未处理第二件物品。

- [联合推理与真实共同用餐最新报告（4段完整Sim视频）](experiments/joint_deliberation_20261007/index.html)
- [目的、设置、实际行为与后续动作学习](experiments/joint_deliberation_20261007/README.md)

可靠生成式伙伴、更多初始状态与任务的正式评测、完整人体动力学及cobalance效度仍未完成。

此前完成当前意图输入契约修正后的三场真实活动，全部提供运行时三机位Sim视频和同步模型输入。
一个机器人泊车的自主操作资格场景、两个直接π0.5共同活动；两场机器人期末任务成立，但三场人个人目标均未完成、目标变化均0，共同满足时间均0。
抽屉场景物体峰速超过现行阈值，明确保留为诊断，不能计作合格Benchmark成绩。

- [当前意图与真实共同活动最新报告（3段完整Sim视频）](experiments/current_intentions_20261007/index.html)
- [目的、设置、实际行为与未完成项](experiments/current_intentions_20261007/README.md)
- [上一批模型空间动作与真实共同活动（3段完整Sim视频）](experiments/spatial_coordination_20261007/index.html)

最新两共同活动数据保存240组观测／2400学习动作，120组合格、120组诊断；按stem独立加载全部通过，失败轨迹不作专家示范。可靠生成式伙伴、完整成熟Benchmark及cobalance效度仍未验证。

每次重要实验都保存运行时真实Sim场景视频及video_timeline.json，在正式HTML生成前逐帧解码核验。报告优先展示实际场景视频，轨迹用于辅助审计；视频缺失、损坏或时间轴不一致会阻止正式报告生成。

已增加独立的生成式伙伴操作资格检查：机器人经真实控制泊车后保持零末端增量，
人自主生成整理目标和动作。该条件不产生机器人HRC成绩；完整视频与实际控制、原始推理、
目标关系及运动资格分开核验。正式启动入口为 `scripts/run_neural_human_qualification.sh`，
本地中国源权重、一次初始化、60秒活动，没有外部人动作清单或定时目标更新。

- [总体进展报告：目的、设置、结果与真实Sim视频](experiments/progress_20261007/index.html)
- [本次操作资格检查结果与边界](experiments/progress_20261007/README.md)

本次餐盘26.4秒曾满足个人区域的释放稳定关系，后续再次操作导致期末失效，另一物品未整理。
物体峰速超现有阈值，作为诊断保留；不能计作可靠伙伴或成熟Benchmark验证。

最新完成可信感知／推理模式人策略、三类持续活动与一次神经双向协调，4段完整60秒三机位Sim视频。
抽屉场景人的当前目标集合自主变化2次，仍未完成个人整理；其他场景存在实际手／机械臂接触与行动阻挡。
视觉协调器产生回应及等待选择，但本例主要保持姿态，尚未形成共同完成。不能把对话、目标变化或接口可用称为cobalance证据。

- [可信感知与双向共同活动最新报告（4段三机位真实视频）](experiments/grounded_reciprocal_20261007/index.html)
- [实际结果、接触反馈与公开／私有边界](experiments/grounded_reciprocal_20261007/README.md)

此前完成较长期意图反思／当前动作两次独立推理、三类持续活动与π0.5／OpenVLA实测，9段同步三机位真实Sim视频。
4模型场景各60秒，人的个人目标均未完成、语义变化0，不能把分层接口运行称为有效动态意图重组或cobalance。
两种上桌条件均有实际双指接触抬高，但没有后续place；π条件还受到旧握持反馈确认过晚影响。
后续独立暂停／接续校准验证修正的握持反馈，原4模型结果保留，修复后模型效果未复测。

- [分层人策略与持续共同活动报告（9段同步三机位视频）](experiments/reflective_activity_20261007/index.html)
- [任务、原始推理、实际结果与能力边界](experiments/reflective_activity_20261007/README.md)

此前完成相对接收物放置、四种物品的接触校准与真实π0.5／Qwen共同活动，5段完整Sim视频、1段不完整接口诊断。
奶酪／薄盘校准形成真实抓放，瓶／碗仍受掌部碰撞阻挡。模型10.50秒完成奶酪原生关系，持续运行26.60秒却有酒瓶离开桌面的附带损失；
人20次重复grasp，实际相对放置0次、无可评分个人目标，不能记作双方协作成功。空夹开口与实际物体释放分开审计，旧结果保留。

- [相对放置与完整场景行为报告（5段完整真实Sim视频）](experiments/relative_placement_20261007/index.html)
- [校准、真实模型行为与未完成项](experiments/relative_placement_20261007/README.md)

此前扩展奶酪包入碗、酒瓶放酒架、碗放炉面及中层抽屉四类真实任务，8段Sim视频含4个基础操作参照。
无人物参照4/4；生成式伙伴条件仅抽屉原生任务成立，人个人整理目标均未满足。
输入/控制/时钟/速度/显示核查通过；酒瓶场景机器人却夹起奶酪，需区分角色/话语与低层适配混杂。
四条人的目标集合未改变，不能把可变接口称为已验证动态意图重组或cobalance能力。

- [跨物体、容器与关节任务报告（8段真实Sim视频）](experiments/native_scene_catalog_20261007/index.html)
- [任务、模型、边界与实测数据说明](experiments/native_scene_catalog_20261007/README.md)

此前增加真实双指摩擦抓放、实际高8cm的收纳台与两种生成式共同活动，4段真实Sim视频含独立校准。
点心收纳在14.95s首次双方释放稳定完成，但人重复抓放、末帧仍夹持，严格期末共同完成0；
共同上桌人误抓机器人黑碗且受旧抓点适配影响，未共同完成。本批手峰速约0.196m/s、两条显示/运动合格。
执行器可用不等于完整人体/手部效度；原始位置评分与严格释放审计分开保留，不能单独归因于HRC推理。

- [上一批真实抓放与高台共同活动报告（4段Sim视频）](experiments/articulated_hrc_20261007/index.html)
- [接触手、校准、任务与数据说明](experiments/articulated_hrc_20261007/README.md)

此前接入人类自选个人目标和公开协商提案，π0.5/OpenVLA各运行两种个人背景，4段真实Sim视频。
π0.5两条放置完成；OpenVLA两条未放置。点心桌人自选双目标后停留在饼干操作；
π工作空间人持续观察、不可评物体目标；OpenVLA工作空间有两次自主目标变化，但人手超速/显示误差只留诊断。
共1980次真实模型调用；3条运动/显示合格，1条不合格。没有把自主接口接通称为可靠动态人类或cobalance验证。

- [上一批自选个人目标与两种学习机器人报告（4段真实Sim视频）](experiments/autonomous_human_20261007/index.html)
- [自主目标场景、资格与数据说明](experiments/autonomous_human_20261007/README.md)

此前完成三类不重置世界的动态工作要求实测：接收盘反复变化、整理对象优先级变化、暂离与返回。
人的阶段完成分别2/3、0/3、3/4，最终共同完成0/3；270次真实π0.5推理、三段45秒Sim视频核验通过。
发现旧目标持续、错误操作对象和提前恢复工作；人的策略遵从及初始旧安排混杂单独披露。
已导出270组真实观测和2700个动作，失败保留，不当作专家示范或通用HRC排名。

- [上一批动态人类工作要求与持续世界报告（3段真实Sim视频及同步审计）](experiments/native_dynamic_activity_20261007/index.html)
- [原生实测数据与加载说明](experiments/native_dynamic_activity_20261007/README.md)

此前完成两项“实际执行反馈与生成意图分离”实测，真实Sim视频2/2通过核验。
准备接收盘：VLA调用0次、人和机器人均未完成；共享空间：VLA调用4次、人完成、机器人未完成。
两项共同完成均为0，模型仍出现未抓取却声称已抓取、随后持续等待的行为。

- [上一批实际执行反馈与生成意图报告（2段真实Sim视频及同步审计）](experiments/grounded_coordination_20261007/index.html)

此前新增Qwen3-VL视觉机器人协调器和双向公开消息，实际选择VLA执行或保持姿态。
3条真实模型运行均未共同完成；原始文字确认与物理执行并列展示，保持原语不计作VLA推理。
这是新增层级算法实测，不归为原始π0.5能力，也没有把对话接通当作cobalance验证。

- [上一批双向视觉协调与实际执行报告（3段真实Sim视频）](experiments/bidirectional_hrc_20261007/index.html)

此前已经完成两种学习机器人与动态伙伴的三层实测。OpenVLA官方图像流程已对齐并逐像素重建。
两种模型基础释放稳定参照各4/4；静态人物条件π0.5完成/OpenVLA未完成，动态协作各0/3。
这是小样本系统行为，不把静态场景失败归因为人策略，也不作通用算法或cobalance排名。

- [两种学习机器人与动态伙伴最新报告（16段真实Sim视频）](experiments/two_model_hrc_20261007/index.html)

此前已接入实际人类执行反馈、模型自主规划与命令拒绝反馈，并增加不同协调关系。
后四条生成式人的实际推物全部完成，但不能把它解释为完整HRC成功。
旧8.5秒原生几何成功片段末帧仍夹持；新入口增加接触、释放和持续稳定判据，
严格判据实测20秒未共同完成。OpenVLA已接通真实原生动作，仅作未匹配官方裁剪的接入诊断。

- [动态人类执行反馈与物理完成最新报告（8段真实Sim视频）](experiments/native_dynamic_feedback/index.html)

此前人物阶段已复用VICO完整贴图、65骨骼和动作资产，增加连续退离/返回与有时序约束的协作任务。
完整人物的机器人操作参照3/3，显示指尖与实际接触点偏差约3mm；本批生成式协作仍因人的持续观察而未完成。
这些是实际结果，外观改善不等于代理策略或HRC能力提升。身体仍是运动学显示，接触仍用力驱动代理。

- [完整人物、离返与协作时序最新报告（8段真实Sim视频）](experiments/avatar_dynamic_hrc_20261006/index.html)

此前已新增匹配原生LIBERO的学习模型参照与“移动接收盘”联合任务：无人的参照3/3、
有人体的静态参照3/3。真实π0.5与Qwen联合运行原始结果为机器人2/3、人2/3、共同1/3；
共同成功片段通过运动核查，另一失败片段因指尖超速只保留诊断。
这是单任务族、合作型伙伴的小样本系统实测，人体外观与接触执行器仍为简化代理，
完整Dynamic Human Policy HRC Benchmark目标尚未完成。

- [最新原生模型与动态人类协作报告（12段真实Sim视频）](experiments/native_dynamic_hrc_20261006/index.html)
- [经核验的共同完成视频（7.35秒）](results/continuous_v2/native_qwen_grounded_activity/task_02/init_000/demo.mp4)

- [实验设计、接口与运行说明](experiments/pilot_v1/README.md)
- [持续运行时、六类场景与当前边界](experiments/continuous_v2/README.md)
- [v2 实验设计与数据契约](experiments/continuous_v2/design.md)
- [已经生成的正式展示页](results/pilot_v1/formal/index.html)
- [v2 六场景报告与轨迹动画](results/continuous_v2/formal_v6/index.html)
- [v2 三种伙伴配对报告与轨迹动画](results/continuous_v2/paired_v8/index.html)
- [v2 Genesis 六场景报告（含真实 Sim 视频）](results/continuous_v2/genesis_v10/index.html)
- [v2 Genesis 三种伙伴条件报告（18 个 episode，含真实 Sim 视频）](results/continuous_v2/genesis_paired_v10/index.html)
- [v2 九类任务族动态伙伴正式报告（9 条真实 Sim 视频、9/9 时间轴核验）](results/continuous_v2/task_catalog_genesis_v2/index.html)
- [真实接触、生成式伙伴与模型适配进展（2026-10-06，含真实 Sim 视频）](experiments/dynamic_contact_20261006/index.html)
- [可见目标表面与96条实际示范的采集进度](datasets/visible_surface_demonstrations/progress.html)
- [96条可见区域真实接触示范正式报告](datasets/visible_surface_demonstrations/index.html)
- [96条示范训练后的六条独立操作测试（真实视频，0/6）](results/continuous_v2/pi05_visible_contact_atomic/index.html)
- [历史反事实 Genesis 报告（含真实 Sim 视频）](results/continuous_v2/history_counterfactual_genesis_v1/index.html)
- [v2 Genesis 验证记录](experiments/continuous_v2/genesis_validation.md)
- [运行脚本](scripts/run_pilot_demo.sh)

所有环境、第三方仓库、资产、缓存和结果实际存储在 `/data1/sieniwgroup/sieniw/projects/HRC-Bench/`，通过软链接访问。此前的 `legacy_llm_direction` 内容保留归档状态。

日常查看和运行使用仓库内的 `results/pilot_v1/`、`results/continuous_v2/`。
它们是指向数据盘对应目录的软链接，报告、动画及原始记录都从这些入口访问。
新工作区若缺少 v2 入口，可在仓库根目录执行：

```bash
ln -s /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2 results/continuous_v2
```

## 运行

原生环境路径与依赖说明见
[本阶段说明](experiments/native_dynamic_hrc_20261006/README.md)。模型服务
仍使用中国源本地π0.5-LIBERO权重；原生Sim通过PCI地址绑定同一进程的CUDA与EGL，
避免将两套编号误当作相同。此前被中止的多卡进程仅保留诊断，不纳入成绩。

最新实测新增世界无重置活动流：一次初始化，保留物体、机器人、人及双方历史，
以公开任务更新切换活动。86.4秒实际运行完成首项、后两项未完成，另有两处持握速度
超阈值，作为诊断保留。π0.5-LIBERO已完成7维末端动作的6秒真实场景接口运行与
像素/动作/请求核查，尚未完成相机和坐标域匹配校准，不能解释为HRC成绩。
96条采集正式完成，22,768个样本与96条视频核验通过。后续3000步学习训练已完成，
22,017帧训练/751帧验证；真实8维动作loss与24维填充辅助loss分别计量，
未记录未来步同时排除注意力与监督。固定64个验证输入loss从0.671到0.0080，
六条独立布局操作仍0/6、无合法接触抬起。678次模型调用/2700个动作的像素、
请求、视频和运动核查通过。报告不将低loss或教师成功当作学习模型的HRC能力。

新运行入口为 `scripts/run_visible_contact_training.sh`、`scripts/run_visible_contact_server.sh`
和 `scripts/run_visible_contact_evaluation.sh`；训练/模型服务/Genesis分别使用GPU3/2/0，
启动前必须重新核对显存。接触手速度控制诊断40秒未完成抓放，未采用为默认基线。
连续活动上下文已修订任务板与旧目标年代标识，仅通过接口回归，尚无新的生成式实测。

新入口：`scripts/run_activity_stream.py`、`scripts/run_pi05_libero_benchmark.py`，
模型服务 `scripts/serve_pi05_libero.py` 使用已下载中国源权重，需设置Torch overlay
`PYTHONPATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/openpi-torch-transformers:src:.`。
GPU作业运行前均须先确认单卡空闲显存足够，模型服务和Genesis使用不同GPU。

在仓库根目录执行：

```bash
bash scripts/setup_vc_pilot.sh
bash scripts/run_pilot_demo.sh
```

运行前程序使用 `nvidia-smi` 检查所选 GPU 的空闲显存。启动脚本指定 GPU 0；若该卡不足 4 GB，程序会停止并说明原因。需要切换 GPU 时修改脚本中的 `CUDA_VISIBLE_DEVICES`。首次运行包括内核编译，耗时比后续运行长。

默认脚本输出到 `results/pilot_v1/demo/`，已完成的验证结果在 `results/pilot_v1/formal/`。程序拒绝覆盖非空输出目录；重复运行请在启动脚本中设置新的输出路径。

这是一版**机制与工程验证**：使用手写策略、仿真语义几何观测和运动学抓取抽象。它尚未评测训练后的基础模型，也不验证接触力、真实抓握、人体安全或真人协作效果。

v2 的参考运行可直接生成 HTML 报告：

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --output-dir results/continuous_v2/formal
```

这次 v2 报告验证的是连续协议、动态伙伴和独立记录逻辑；参考报告使用
`ContinuousWorld`，Genesis 报告使用 VC/Genesis 逐 tick 后端。两者都不把手写
伙伴或 `GreedyPublicPolicy` 的成功率当作模型结果；Genesis 仍采用运动学夹持和
 Avatar 拿放抽象，真实接触安全、训练后的 VLA/WLA 推理和真人协作仍需后续实现。

重要 Genesis 实验的正式报告以运行时非空 `demo.mp4` 作为产物门槛，并在
`replay_verification.json` 中记录视频覆盖率。新运行还保存 `video_timeline.json`，
用于把真实 Sim 视频与 benchmark 时间和事件逐帧联动；旧快照若只有视频仍可播放，
但会明确标出缺少时间轴。`ContinuousWorld` 是参考后端，不要求真实 Sim 视频。

连续 benchmark、原生 OpenPI、恢复、关节校准、历史诊断和 Dataset 的 Genesis
入口都会在生成 HTML 前自动逐 episode 解码视频，严格核对帧数、FPS、尺寸与时间轴。
核验失败会保存失败详情并阻止生成正式报告。也可以独立复核已经保存的结果：

```bash
PYTHONPATH=src .venv-vc-pilot/bin/python scripts/verify_genesis_videos.py \
  --input-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/my_genesis_run
```

命令在结果根目录写入 `video_verification.json`，任一 episode 缺视频、无法解码或
时间轴不一致都会以失败退出；旧运行缺少时间轴时会标记警告但仍核验视频本身。
需要把时间轴缺失也作为正式门槛时，加上 `--require-timeline`。HTML 报告将真实 Sim
视频放在轨迹画布之前，并显示每条 episode 的核验状态；轨迹画布仍用于逐 tick 事件
审计，不能代替 Sim 视频。

原生MuJoCo学习模型入口`run_libero_native_reference.py`与接触手校准入口`run_native_hand_validation.py`
也强制先核验真实视频再生成正式HTML。重要实验以运行时相机视频为主要观看材料，保留原速模拟时间、逐帧时间轴、
成功与失败，并将模型意图／实际动作／物理完成分开。没有完整视频或时间轴的中断只标作诊断，不计入正式覆盖率。

需要把某次运行作为重要实验时，显式使用 `--experiment-tier important`（或快捷选项
`--important`）。该等级只允许 `--backend genesis`，并把每个 episode 的运行时
`demo.mp4` 作为报告生成门槛；参考后端适合快速探索，不会被误当成重要实验的视觉证据：

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --output-dir results/continuous_v2/important_demo \
  --backend genesis --experiment-tier important --suite --count-per-condition 1
```

重要实验默认在任务结束后继续录制 `1.5` 秒，并让每个搬运阶段至少持续
`0.2` 秒，避免成功动作在视频中瞬间消失。需要调整时可使用
`--video-settle-seconds` 和 `--minimum-transfer-phase-seconds`；这些值会写入
`provenance.json`，便于复现实验。

2026-10-06 新增 `--robot-grasp-model friction_contact`，原生模型入口默认采用它：机器人只能提交底层
关节动作，操作对象为受重力和碰撞影响的自由刚体；双指摩擦抓取与稳定释放由实际
物理状态核查。保存 `contacts.jsonl`、`robot_control.jsonl`、`physics_contract.json`
和 `motion_verification.json`。人体选项 `--human-manipulation-model auto` 在该后端使用
`articulated_contact_hand`，以关节受力完成持握与释放；人物显示采用动作数据和躯干 IK。
可显式选择旧 `avatar_kinematic_attachment` 执行器复盘历史。新的接触手已通过连续性
与显示手腕对齐检查，仍是简化代理，不能宣称完整人体动力学或真人效度。
三类 π0.5 + Qwen 实测、基础操作 Dataset 和执行边界均已保存；
具体设置、视频、贡献归属与未完成项见[本阶段报告](experiments/dynamic_contact_20261006/index.html)。

原生 OpenPI 入口现在支持 `--scenes`、`--task-catalog`、`--scenario-dir` 与 `--seeds`，
并可使用本地 Qwen 生成式伙伴。使用已有本地权重时可复现以下诊断：

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  .venv-vc-pilot/bin/python scripts/run_openpi_benchmark.py \
  --robot-grasp-model friction_contact --partner-mode qwen_llm \
  --human-persona cooperative --scenes relay concurrent_overlay robot_induced_rebalance \
  --ticks 300 --resolution 640 --render-stride 4 \
  --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/new_contact_run
```

先按 [OpenPI 服务说明](experiments/continuous_v2/README.md)启动独立模型服务。
Genesis 与 Qwen3-14B 组合预估需要约 36 GB 空闲显存，程序会按本地权重文件大小
核查；OpenPI 单独使用另一张 GPU。本轮 VC 环境增加 `transformers==4.57.1` 和
`accelerate==1.10.1`，来自清华 PyPI 镜像。模型与数据集仍只允许从中国大陆镜像或
本土服务获取，禁止通过 VPN 下载；本轮未新增下载模型或数据。

实际接触示范 Dataset 包含双相机、本体状态及下一物理控制步的动作目标。
它使用输入 stem 匹配 `_wrist.png`、`.state.npy`、`.action.npy`，不使用配对 manifest。
[按文件名加载的接口](experiments/continuous_v2/physical_frame_dataset.py)输出带有效时段
的 `15×8` 动作块；这些是数据生成教师示范，已用于一次实际 π0.5 LoRA 域适配训练。
训练 400 步，仅更新约 5000 万个 LoRA 参数，保留官方 DROID 归一化与动作标度。
固定 16 个 dev 样本上的 loss 从 1.674 降到 0.031；独立红、蓝、绿闭环测试为 0/3，
没有合法接触搬运贡献。拟合示范和实际操作能力分别报告，不能把训练下降称为 HRC 提升。
训练记录在 [results/contact_training/pi05_lora_v1](results/contact_training/pi05_lora_v1/summary.json)，
评测的真实视频见 [基本操作报告](results/continuous_v2/pi05_lora_atom_evaluation/index.html)。

训练入口是 `bash scripts/run_contact_lora.sh`，会拒绝覆盖已有权重/记录目录；
重跑前改脚本中的输出目录，并用 `nvidia-smi` 确认 GPU 3 的空闲显存至少能容纳
约 32 GB 的训练分配。权重保存在共享 models 目录，训练记录与缓存位于项目数据盘。
训练时只解析已有本地文件/缓存，不隐式下载模型。
启动前先用 `nvidia-smi` 确认独立 GPU 至少有约 20 GB 空闲显存。例如使用 GPU 2：

```bash
CUDA_VISIBLE_DEVICES=2 XLA_PYTHON_CLIENT_MEM_FRACTION=0.4 PYTHONPATH=src:. \
  OPENPI_DATA_HOME=/data1/sieniwgroup/sieniw/models/Physical-Intelligence/openpi-cache \
  HF_HUB_OFFLINE=1 .venv-openpi/bin/python scripts/serve_openpi_droid.py --contact-lora \
  --checkpoint /data1/sieniwgroup/sieniw/models/HRC-Bench/pi05_droid_contact_lora_v1/400
```

生成式伙伴新增带时间的公开观察历史，以及 Qwen 自己生成的解释和经验记忆；
每次决定检索最近 12 条经验，完整内容保存到 `human_memory.jsonl`。
早期只在单episode内保留；后续session与无重置活动流会保留跨活动经历，
尚无跨天长期记忆、真人校准或效用消融证据。
独立基本操作可选 `--partner-mode observing`，用于隔离人的接管行为。

后续已完成完整动作专家的位置域适配：1200步、457,967,648个训练参数，使用实际
施加的位置目标、train-only相对位置归一化与末尾动作mask。固定验证loss降到0.0041，
独立旧中心点任务仍0/3，仅蓝块有真实接触抬起证据。低loss不能替代闭环操作成绩。
新联合运行采用 `--visible-surfaces --human-memory-scope session`，40秒预算，
接力完成而另外两项失败，机器人贡献全部0。伙伴跨活动经验实际进入输入，但后续
出现整段观察停顿；物理世界仍在每个episode重新初始化，尚不是世界无重置的活动流。

可见目标场景由[同一份表面几何](src/hrc_pilot/goal_regions.py)控制显示与评分，检查
实际物体完整足迹、释放、支撑和稳定。接触生成校准与96条独立布局示范采集
已完成；这是几何教师数据生成，不计成学习模型成绩。采集启动脚本为
`scripts/run_visible_surface_collection.sh`，已完成视频可用以下命令生成独立进度快照：

```bash
PYTHONPATH=src:. .venv-vc-pilot/bin/python experiments/continuous_v2/build_visible_surface_progress.py
```

π0.5-LIBERO权重已通过直连中国ModelScope获取并完成SHA256核验，位于
`/data1/sieniwgroup/sieniw/models/lerobot/pi05-libero/`；仓库的 `models/pi05_libero`
为软链接。它使用7维末端增量动作与不同的状态接口，已完成6秒实际运行与链路核查；
相机、坐标和接触域匹配尚未充分校准，不能接到DROID接口后直接当作有效能力排名。
下载脚本 `scripts/download_modelscope_policy.py`
禁用环境代理，限制重定向为ModelScope/中国区阿里云OSS，没有HuggingFace或VPN回退。

```bash
CUDA_VISIBLE_DEVICES=3 PYTHONPATH=src:. .venv-vc-pilot/bin/python \
  scripts/collect_contact_demonstrations.py \
  --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/new_contact_demonstrations
```

`generate_scenarios` 生成可改变布局、分工和伙伴条件的任务实例，策略通过 `ExternalPolicyAdapter` 接入模型。每个 episode 产生可按目录和稳定文件名配对的 `scenario.json`、公开观测、策略输入输出、轨迹、事件和独立指标；`GreedyPublicPolicy` 只是协议基线。摩擦接触后端已实际运行，但模型基础操作、任务覆盖和研究效度尚未达到正式排行榜要求。

可以先生成一个按 `train/dev/test` 结构划分的数据集，再用同一批场景批量评测模型：

```bash
PYTHONPATH=src python scripts/run_hrc_dataset.py generate \
  --output /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/continuous_v1 \
  --count-per-condition 10 --repeats 3

PYTHONPATH=src python scripts/run_hrc_dataset.py evaluate \
  --dataset /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/continuous_v1 \
  --output /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v1/my_model \
  --policy my_adapter:make_policy --split test
```

Dataset 生成和评测也可选择 Genesis 后端：

```bash
PYTHONPATH=src python scripts/run_hrc_dataset.py generate \
  --output /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/continuous_genesis \
  --count-per-condition 1 --backend genesis
```

数据集 CLI 在 Genesis（尤其是 `--experiment-tier important`）运行结束后，会自动先解码
每个 episode 的 `demo.mp4`、严格核对 `video_timeline.json`，再生成 `index.html`；核验结果
保存在运行根目录的 `video_verification.json`。任一视频缺失、为空、无法解码或时间轴不一致，
命令会失败并不生成通过状态的报告。这样批量数据集评测和单次 benchmark 使用同一条真实 Sim
视频门槛。

正式扩展基准也可以直接生成九类任务族；`--task-catalog` 会让数据集入口和
连续运行器使用同一套任务定义，每个 episode 仍按稳定的 split/family/name 路径保存：

```bash
PYTHONPATH=src python scripts/run_hrc_dataset.py generate \
  --output /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/continuous_catalog \
  --task-catalog --count-per-family 5 --repeats 3 --partner-mode dynamic
```

也可以用 `--scenario-dir path/to/scenarios` 把自定义的 JSON 活动契约目录直接
生成成同样的数据集；每个文件声明对象、区域、工作项和前置关系，不需要固定事件脚本。

`my_adapter:make_policy` 工厂可以返回实现 `reset()`/`act(observation)` 的策略，或返回用 `ExternalPolicyAdapter` 包装的 `predict(public_observation)` 模型。VLA/WLA 只收到公开 observation，不能读取 `scenario.json` 中的目标和伙伴潜变量；每次调用的动作校验、耗时、原始输出和异常会写入 `policy_io.jsonl`。批量结果会按结构划分、条件、伙伴和策略聚合任务成功、恢复时间、重新分工、冲突率、cobalance 代理指标以及人类信任/依赖变化，并报告多 seed 的 bootstrap 95% 区间。

可以用 `--suite` 生成 isolated、matched_serial、compositional 和 held_out 结构条件，并用 `--partner-mode fixed_replay|reactive|adaptive` 做伙伴信息边界对照。held-out 的依赖关系写在每个 episode 的 `scenario.json` 中，不依赖 `manifest.json`。

要在完全相同的场景实例和 seed 上配对三种伙伴条件，可运行：

```bash
PYTHONPATH=src python scripts/run_continuous_benchmark.py \
  --output-dir results/continuous_v2/paired \
  --suite --count-per-condition 5 --paired
```

运行时会在动作启动后在线采样场景动力学中的延迟或失败；公开的 `action_delayed`、`action_failed`、`reassignment` 等消息会进入下一轮模型决策。这样可以测量机器人是否能承认未完成、求助并与伙伴重新分工，而不依赖固定的第 N 步脚本。
