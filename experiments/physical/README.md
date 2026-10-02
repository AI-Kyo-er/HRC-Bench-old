# 持续桌面整理物理原型 v3.1

本轮补齐可恢复公开动作接口和真实物理承载层，是小规模探索性诊断，不是论文主实验或组合结构留出。旧 `language_v2` 的提示、数据和评分没有修改；新接口、恢复规则、自由子任务选择、物理执行和步预算同时改变，新旧分数不能作公平同比。

## 后端和真实执行边界

实际安装并检查了 [ManiSkill 官方安装流程](https://maniskill.readthedocs.io/en/latest/user_guide/getting_started/installation.html)：`mani_skill 3.0.1 / sapien 3.0.3` 的 `PickCube-v1` CPU状态reset和GPU渲染均成功，帧shape为 `(1,512,512,3)`，原始日志在 `results/physical_v3/raw/backend_probe.log`。ManiSkill并非不可用。选择 [Bullet 官方物理引擎](https://github.com/bulletphysics/bullet3) 的 `pybullet 3.2.7`，理由是本轮最小Panda任务可以在CPU运行物理与TinyRenderer，不占用模型GPU，并直接保存每个240Hz物理步的关节、末端、物体位姿/速度和接触。

场景有一台标准Panda、三个0.06kg方块和两个浅托盘。每物品在每托盘有独立槽位。关节通过位置电机控制，夹爪通过摩擦接触抓取，没有运行期物体位姿重置、抓取attachment、物体瞬移、写入成功标志。初始化允许设置关节初态。IK只生成关节电机目标；成功从物体落点、高度与线速度计算。每次抓放后共享电机停车动作释放伙伴滑轨。伙伴是独立滑动关节驱动的几何占位块，不是人体、真人动作分布、搬运伙伴或经过验证的人身安全系统。

公共路径有一个中央waypoint。控制器由伙伴当前真实AABB与55mm近似探针判定该waypoint是否被占用，`direct_blocked`拒绝标为 `physical_attempt=false`；它不是已经发生的机器人碰撞。绕行路径和直接路径的实际接触都记录在物理轨迹中，不能把此粗略屏障称为完整碰撞规划或人身安全验证。伙伴轨迹记录电机目标到位与实际AABB变化；不到位独立记失败，不以任务完成掩盖资源事件未发生。

开发中保留了两项真实修复证据：初版占位块底部碰托盘而停在y≈0.395（未进入中央通道）；提高占位块后，右盘上方的机器人停车姿势又可能阻挡滑轨。最终加入统一home停车并检查伙伴到位。`control_initial_summary.json`属于修复前尝试，不作为最终低层验证；最终 `control_summary.json`对应修复后12次基础控制和8次连续控制。

## 公开接口、恢复和观察

策略每步自主选择三件物品、两个区域及三种抓放方式，另有 `request_clear` 和 `yield`，共20个候选。所有对象×目标×方式始终列出，包含错误目标、未授权assisted及暂不可执行动作，不由评分目标、隐藏回应或完成标签筛选。自然语言释义和语义ID同时公开，模型仅输出 `{"choice":"..."}`。

- `place`：独立直接抓放；`careful`：独立绕行抓放。
- `assisted`：已有接受的清道协助后直接抓放，伙伴贡献是清道而非扶持物品。
- `request_clear`：请求伙伴撤离占位块，不执行搬运；接受后实际电机撤离，拒绝后仍可绕行。
- `yield`：履行伙伴已公开的“先让我撤离”请求；只改变伙伴几何状态，不完成物品。

多余求助、重复请求、错误目标、无效JSON和操作失败均给真实反馈、计1次决策并可恢复，不跳过下一物品。通用执行器会拒绝与已接受目标冲突、重复已完成物品、未授权协助或违反明确先让行要求的抓放；这些是协议拒绝，未执行的错误目标不算实际放错物品。反馈中的目标纠正属于有记录且计决策成本的显式接口帮助，因此本版也不衡量完全无帮助的自主纠错。

模型观察只有完整公开事件历史、原始物品位姿/速度、伙伴实际位置、物理区域检测和候选。`physical_placements`表示实际落在哪个固定槽位，与评分目标无关；不提供按当前隐藏评分规则计算的已完成/未完成标记，也不提供未来伙伴回应。模型自己结合已接受指令与区域判断进度。规则参考也只接收同一公开观察并归约历史，不直接读case/目标字段。

## 开发与冻结

独立16个单调用开发接口控制：solo、已接受清道协助、明确先让行、拒绝后绕行，各交叉left/right目标和菜单正常/反序。正常与反序候选内容相同，存在多个可接受动作时按集合判定。v3.0为14/16；只增加一次“ID末尾目标匹配、顺序不改变目标”的开发说明后v3.1为15/16：solo、assisted、yield各4/4，refusal 3/4。剩余错误为left目标+反序选择right。两版均无JSON错误或生成截断，原始输入输出完整保存。不继续针对错误调提示，不声称基础校准完全通过。

最终低层开发：基础direct与实际占位下careful各6次，12/12成功；6次占位时direct拒绝且没有执行；8/8连续公开规则策略成功，伙伴运动到位失败0。seed0/1用于开发。接口仍有基础误选，因此冻结模型pilot定位为探索性物理诊断，不能把条件差异归因于交互结构。

正式冻结文件 `cases/freeze.json`包含8个实例、源码/资产/依赖/提示校验及开发结果校验。seed10/11与接受/拒绝回应、upfront/revision交叉。seed同时关联目标反转和菜单反序，本pilot不能单独估计菜单或种子效应。

- upfront起点公开最终目标；首次物理放置成功后仅确认目标。
- revision起点blue目标与最终目标相反；首次物理放置成功后公开接受blue局部修正，另外两件物品约定与世界保持。
- 两条件都在首次成功后让伙伴进入同一个真实通道；回应仅在请求后出现。两件按当前目标完成后再次占位并请求先让行。
- 每例最多12个高层动作；当前最终目标的三件物品均物理满足时提前结束，否则预算耗尽。失败不重置世界；物理tick数、抓放尝试和协调次数另外统计。

两条件最终目标和底层事件逻辑相同；规则策略red→blue→green时低层动作匹配。若模型选择不同物品顺序，修正可能使已经放置的blue重新成为未完成任务，实际轨迹/操作成本就会不同。这是自由策略的实际后果，不表示各轨迹长度、信息和操作难度严格匹配。指令时点比较还混有历史表达差异；8例没有显著性或可推广的因果估计。

本版有持续同一世界、公开局部目标更新保留其他约定、自主子任务选择，以及请求/拒绝/让行改变物理资源。未实现动作中途挂起再恢复子任务栈、伙伴搬运、人体运动、真人协同、视觉感知、六类交互结构、真正组合留出或长度/信息匹配。Moving Out等已有物理协作工作，因此物理、多交互和3D本身均不是本研究的新贡献。

## 复现与存储

本地3B使用原固定revision `aa8e72537993ba99e69dfaafa59ed015b17504d1`，BF16/greedy/seed0，96输出token，torch2.6.0+cu124、transformers4.49.0没有升级。实际包全集在 `environment-lock.txt`；模型权重仍使用已有数据盘链接，未重复下载。新增仿真依赖装入同一个数据盘venv，旧v2原始包锁与结果保留。PyBullet在Python3.12现场构建，构建时间在日志；本轮物理与渲染均CPU，模型GPU3，启动前重查空闲显存（预计<12GB）。

环境、下载缓存、仿真资产和完整轨迹都位于 `/data1/sieniwgroup/sieniw/HRC-Bench/`。项目的 `results/physical_v3/raw`是数据盘结果链接；无需生成配对manifest，稳定case ID关联轨迹、调用、帧与摘要。每条episode的 `ticks.jsonl.gz`保存每一个物理step，`decisions.json`保存原始prompt/response/反馈，`summary.json`记录最终状态与成本。物理body ID固定为table0、robot1、red2、blue3、green4、left托盘5/right托盘8、partner11（其余为托盘墙）；接触字段同时保留link ID。

```bash
.venv-llm/bin/python -m unittest discover -s tests -v
.venv-llm/bin/python -m experiments.physical.run controls --output-dir results/physical_v3/raw/new_dev_controls
nvidia-smi --query-gpu=index,memory.free --format=csv
CUDA_VISIBLE_DEVICES=3 .venv-llm/bin/python -m experiments.physical.run calibrate --output-dir results/physical_v3/raw/new_dev_calibration
.venv-llm/bin/python -m experiments.physical.run formal --policy reference --output-dir results/physical_v3/raw/reproduce_reference --render
nvidia-smi --query-gpu=index,memory.free --format=csv
CUDA_VISIBLE_DEVICES=3 .venv-llm/bin/python -m experiments.physical.run formal --policy model --output-dir results/physical_v3/raw/reproduce_model --render
```

正式执行核验冻结源码、依赖与机器人资产，拒绝非空结果目录，避免覆盖旧尝试。`freeze`只执行一次，禁止覆盖已有冻结文件。此处已冻结，因此重跑只需formal入口；改变协议或代码必须用新的版本目录，而不能覆写当前原始结果。运行结果与代表视频见项目 `results/physical_v3/` 的小摘要和README追加实测部分。

## 冻结物理诊断实测与失败证据

| 策略 | 完整任务 | 物品进度 | 高层决策 | 协议拒绝 | 真实抓放/抓放失败 | request/yield |
|---|---:|---:|---:|---:|---:|---:|
| 公开历史归约规则参考 | 8/8 | 24/24 | 40 | 0 | 24/0 | 8/8 |
| Qwen2.5-3B新接口 | 0/8 | 8/24 | 96 | 88 | 8/0 | 0/0 |

模型每例只完成green，随后继续选择green耗尽预算。88次协议拒绝中，24次是错误目标，64次是重复已完成物品；seed10还反复改选green的错误目标，不是一次纠正后就永久改对。没有JSON错误、输出截断或伙伴电机不到位。接受/拒绝两种回应条件在模型运行中都没有被实际请求，因此不能据此估计伙伴类型效果。单物品开发校准15/16不能替代多物品进度能力校准；本版失败发生在继续选择子任务之前，不支持结构组合归因。规则参考的upfront/revision动作序列与成本相同。

**规则任务完成不代表安全通过。** 全240Hz轨迹审计发现4个拒绝case各有4个robot-partner接触tick，全部发生在careful抓放后的直接关节park阶段，最大法向力约910.75–1075.13N；4个接受case无此接触。原始占位块运动与抓放确实发生，但中央waypoint屏障未覆盖完整机械臂停车路径。这是明确的低层控制缺陷；必须在新版本中修复并验收全轨迹接触后再扩展物理实验，不能用于真机安全结论。物理完成评分并未将接触自动计作抓放失败，二者单列在 `trajectory_audit.json`。

完整调用和轨迹在数据盘；小摘要、代表原始调用与执行校验在项目 `results/physical_v3/`。代表可视化：

- 规则完成但存在停车接触的case：`raw/formal_reference/formal_revision_10_0/contact_sheet.png`和同目录`rollout.mp4`。
- 模型只完成green的失败case：`raw/formal_model/formal_revision_10_0/contact_sheet.png`和同目录`rollout.mp4`。
- `representative_calls.json`保留一条规则成功和一条模型失败的原始输入、输出、反馈和末态；`trajectory_audit.json`包括所有case的轨迹校验、动作类型、伙伴运动到位与实际接触。

规则句柄51603与模型17294均exit0；只读分析25077 exit0。GPU3在模型退出后恢复约48GB空闲。未重跑覆写原始神经轨迹，不声明模型输出已独立验证完全确定性。
