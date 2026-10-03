# VC 具身 Pilot v1

## Material Passport

- 类型：代码实验 / 基础 demo。
- 研究方向：Human-robot Progressively Rebalanced Collaboration Benchmark。
- 范围：桌面整理中的历史依赖、理解更新和响应式伙伴贡献。
- 证据：实际仿真、视频、关节与物体状态、公开交互记录、独立终态评测。
- 边界：手写机制对照；不提供统计推断或模型能力结论。

## 第一版回答什么

这版实验验证能否在同一个具身环境中控制交互条件，并测量重组织合作后的执行结果。它不以延长任务或增加角色切换次数制造难度，也不要求策略显式输出某种统一的内部信念格式。

| 条件 | 控制内容 | 有效执行结果 |
|---|---|---|
| `history_keep` | 初始约定红杯留用；人随后把红杯移到旁边 | 保留红杯，收纳蓝杯 |
| `history_pack` | 初始约定两个杯子收纳；发生相同移杯动作和相同公开消息 | 继续收纳红杯和蓝杯 |
| `information_update` | 人收到新的用途信息，更新理解并公开澄清；更新时物体位置不变 | 接受任务更新，保留红杯并收纳蓝杯 |
| `partner_available` | 初始蓝杯由人完成；机器人发出公开请求 | 人响应请求并实际执行蓝杯贡献 |
| `partner_unavailable` | 相同初始分工；人在收到请求后拒绝 | 机器人重新承担蓝杯贡献 |

两个历史条件在初始物体布局、人体执行、机器人观察动作和干预内容上相同，仅先前公开约定不同。`summary.json` 中的 `history_pair_audits` 比较决策前物体位置、机器人关节和人体位置，防止把布局差异当作历史依赖。

模拟人根据真实执行中的末端与红杯距离触发响应，根据公开求助决定是否贡献。它不读取机器人的下一步目标、隐藏计划或策略内部状态。伙伴可用性由实验条件控制，不默认接受所有请求。当前共同观察动作是匹配对照的固定前导；它不是自由策略产生的完整协作活动。

## 复用与新增的代码

VC 的 `AvatarController`、`AvatarRobot`、拿放动画及配套 Genesis 0.3.3 分支提供人体执行。新增 `VCWorkspace` 作为局部桌面环境；没有加载城市、交通或社区日程，也没有把 VC 迁移到 Genesis 1.4.3。

| 模块 | 职责 |
|---|---|
| `src/hrc_pilot/backend.py` | 场景、VC 人体动画、机械臂关节执行、中断、传感器、视频和状态记录 |
| `src/hrc_pilot/protocol.py` | 模型可见的观测与动作接口 |
| `src/hrc_pilot/partner.py` | 根据可见执行和公开请求响应的伙伴规则 |
| `src/hrc_pilot/scenarios.py` | 不通过观测接口提供的实验条件 |
| `src/hrc_pilot/policies.py` | 三个透明的手写对照与自定义策略加载 |
| `src/hrc_pilot/evaluation.py` | 独立评测实物位置、有效约定违背和技能失败 |
| `src/hrc_pilot/report.py` | 离线 HTML 展示 |

VC 的 `vico.modules` 原本会在导入人体时连带导入城市交通模块。仓库内的 `patches/vc-pilot-minimal-imports.patch` 增加一个仅在 pilot 启用的最小导入分支；没有改变人体控制器的行为，未启用该开关时保留原始导入方式。第三方 checkout 的提交与这份补丁共同定义运行版本。

## 手写策略对照

- `memory`：保留先前约定，接受公开修正，并在伙伴拒绝后重新承担贡献。
- `static`：保留初始任务和分工，但不接受后续任务修正或分工变化。
- `reactive`：响应明确修正及拒绝，但在移杯干预后采用默认几何恢复，丢失此前红杯留用约定。

这些是人为定义的机制对照，便于检查场景和评测是否区分相应行为。它们的差异不能证明某类训练模型缺乏高阶 HRC 能力，也不能作为论文的模型实验结果。

## 观测与模型接入

`Policy.reset()` 在每个 episode 开始调用，`Policy.act(observation)` 返回 `Action`。自定义策略通过 `--policies your_module:factory` 加载。

机器人得到杯子与区域几何、机器人关节和末端状态、人体可见位置、持物状态、已完成技能、RGB 像素和公开消息。**几何来自仿真器，公开消息提供结构化类型和值；当前不是仅凭视觉和自然语言理解的基线。**

私有实验条件、人的私有理解和最终评测目标不进入 `Observation`。RGB 直接以像素数组传入，不传入会泄漏条件名称的结果文件路径；展示视频中的条件名称与字幕也不出现在机器人 RGB 观测中。

当前是同进程 Python 接口隔离，并不是阻止任意插件读文件或导入模块的安全沙箱。正式模型接入应限制在这个观测接口内；具有工具调用能力的策略需要另设进程或服务边界。

支持的动作：

- `transfer`：给定物体与目标区域，执行统一机械臂搬运技能。
- `request_help`、`acknowledge`、`wait`、`finish`：公开交互与流程控制。
- `joint_position`：9 维关节位置目标，包含 7 个臂关节和 2 个指关节，执行 6 个仿真步。

基础接入示例：

```python
from hrc_pilot.protocol import Action

class MyPolicy:
    def reset(self):
        self.history = []

    def act(self, observation):
        # observation.rgb: uint8 RGB array
        # observation.robot_qpos: 9 joint positions
        # Real models must manage their own context and match the robot/action space.
        return Action("transfer", object_id="blue", destination="tray_blue")

def factory():
    return MyPolicy()
```

高层 VLM/规划器可以调用统一技能；底层 ACT/DP/VLA 可以从关节入口进一步接入，但当前尚未实现其权重、动作块、夹持映射或训练管线。关节入口自身不会自动执行物体附着。禁止把不同层级策略的结果直接解释为公平的统一模型排行榜。

## 执行抽象与限制

机械臂通过 Genesis 的 IK 和关节位置控制器移动；每个技能记录实际末端跟踪误差，超过阈值计为技能失败。人为抓取附着后，杯子沿实际末端运动，终态通过读取场景实体位置评测；`finish` 不能使未完成的任务自动成功。

杯子是固定、无碰撞的任务道具；机器人搬运和 VC 人体拿放采用运动学附着抽象。人体采用 VC 的动画与简化碰撞体，当前不启用人体碰撞响应。机械臂与桌面仍在刚体仿真中。第一版不验证接触式抓握、共同承重、物理阻挡或安全距离。

暂停与重规划目前发生在共同观察阶段和统一技能边界；尚未支持任意抓取阶段的安全撤销与恢复。伙伴目前是响应式规则系统，尚未接入真人、生成式人类策略或独立视觉感知。任务更新场景是一种最低限度的 repair/reground 实例，不代表完整覆盖。

## 环境与可复现性

固定版本：

- Virtual Community：`b1ace3b2d130746a52cac1ec0c1de05f4f90deec`。
- 作者 Genesis 分支：`cdbe596f23220b8134434dd0946039c4f493ab5a`，版本 0.3.3。
- VC 资产：`2325ce34be748231ab6d4197a2b525eef16cc10f`，仅一名人物和约 40 MB 动作文件。
- Python 3.11；PyTorch 2.5.1 + CUDA 12.1；NumPy 1.26.4；gstaichi 2.3.1。

本环境使用比 VC 原完整依赖更新的 PyTorch，以独立最小环境实际验证；没有安装城市生成和模型训练的全部依赖。实际包版本固定在 `requirements.lock.txt`，资产有 SHA-256 校验。安装工具需已有 `uv` 和 `/usr/bin/python3.11`。

运行：

```bash
bash scripts/setup_vc_pilot.sh
bash scripts/run_pilot_demo.sh
```

测试：

```bash
./.venv-vc-pilot/bin/python -m unittest discover -s tests -p test_pilot_protocol.py -v
./.venv-vc-pilot/bin/python scripts/verify_pilot_results.py --result-dir results/pilot_v1/formal
```

程序在 GPU 初始化前读取 `nvidia-smi`，要求所选卡至少 4 GB 空闲显存。未指定 `CUDA_VISIBLE_DEVICES` 时选择空闲显存最多的卡，仅使用该卡。CLI 支持 `--backend cpu`，但当前验证以 GPU 0 为准。

## 结果与查看方式

正式验证目录是 `results/pilot_v1/formal/`，启动脚本的新运行目录是 `results/pilot_v1/demo/`。非空目录不会被覆盖。

| 文件 | 内容 |
|---|---|
| `index.html` | 可按条件和策略筛选的视频展示 |
| `episodes.csv`、`summary.json` | 实际 episode 指标、完整性状态、历史对照核查 |
| `provenance.json` | 固定版本、实际包版本、源码哈希、设备和运行参数 |
| `verification.json` | 视频／轨迹一致性、实际机制对照与历史 RGB 核查 |
| 每个 episode 的 `demo.mp4`、`preview.png` | 仿真视频及预览 |
| `events.jsonl` | 公开消息、理解更新、中断、实际搬运和技能失败 |
| `policy_io.jsonl`、`observation_*.png` | 每次决策的实际输入输出与机器人 RGB |
| `trajectory.npz` | 视频采样时刻的机械臂、物体和人体姿态状态 |
| `metrics.json` | 基于实际终态的任务与协调指标 |
| `post_intervention_state.json` | 策略决策前的物体与双方状态 |

直接打开展示页即可查看。也可在本机提供静态访问：

```bash
./.venv-vc-pilot/bin/python -m http.server 8765 --bind 127.0.0.1 --directory ./results/pilot_v1/formal
```

浏览器访问 `http://127.0.0.1:8765/`；远程机器可通过 SSH 端口转发访问。

`trajectory.npz` 保存的是渲染采样时刻的状态，不是能够精确恢复物理积分器的 checkpoint。MP4 可直接回放；没有声称跨机器的动力学逐位重现。

## 后续实验需要补充

这版先让环境和指标可运行、可检查。要验证论文假设，还需加入真实模型、基础技能与长度匹配的对照、未见交互组合、多 seed 与布局、信息不确定性及澄清选择；进一步验证模拟协调成本与真人行为是否对应。正式模型实验应将操作失败与合作失败分别报告。
