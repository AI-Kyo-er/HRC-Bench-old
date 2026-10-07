# 动态共同活动：可执行性与神经策略进展

[真实 Sim 视频统一入口](index.html) · [关键行为分析](BEHAVIOR_REVIEW.md) · [参考协议](PROTOCOL.md) · [理想感知系统设置](SYMBOLIC_PROTOCOL.md) · [六类情境与证据门槛](SITUATIONS.md) · [整体研究设计](../dynamic_joint_activity_20261007/DESIGN.md)。

目的：检验三个具有跨主体贡献依赖的日常活动是否可执行，以及在线生成的人与真实机器人系统能否建立、维持和调整活动。此批是开发及可执行性实验，尚无冻结的正式统计评测。

人的策略为 Qwen3-14B，无抓放 LoRA；策略与执行分离，连续运动学持物约束只实现其所选贡献。机器人使用 π0.5 / LIBERO 原生 MuJoCo 场景及 7D OSC，不瞬移或吸附机器人。这里的视频是实际原生仿真，不能称为 Genesis 视频。直接 VLA、视觉协调＋VLA、理想几何协调＋VLA分别记录；共享冻结权重不共享人私有上下文。

三个完整参考：

| 活动 | 完成的参考目录 | 机器人来源 | 能说明什么 |
|---|---|---|---|
| 抽屉清理 | joint_feasibility_drawer_access_20261007 | 实际 π0.5 | 清理、打开、收纳的依赖链可执行 |
| 点心准备 | joint_feasibility_snack_service_handoff_20261007 | 实际 π0.5 | 提供、填装、携带交付可执行 |
| 饮品整理 | joint_feasibility_drink_storage_tolerant_20261007 | 既有轨迹的 OSC 反馈跟随，当前 NN=0 | 场景可执行；不能说明当前 VLA 已完成 |

神经开发条件中，抽屉原生技能接口在 10.4 秒真实打开，并发生奶酪用途修改与实际取出；后续仍有重复操作、迟滞澄清和过时指令。点心存在错误完成理解、重复提供容器、说离开但执行字段未选离开的情况。详见时间表及行为分析。

重要运行已保存完整实际 Sim 视频、逐帧时间轴、真实策略输入输出、公开交流和动作；早期崩溃有 24.1 秒部分视频并单列诊断。统一页面要求独立视频核查存在且通过，正在运行的结果不当作完成结果发布。报告索引 results_index.json 只用于浏览，不编码训练数据配对。

## 复现与独立核查

在仓库根目录运行已有 bash 启动入口；每次运行先检查 nvidia-smi，选足够显存的单卡，并按现有渲染绑定选择 EGL 设备。输出目录使用新的名称，不覆盖历史失败。

```bash
PYTHONPATH=src .venv-libero-native/bin/python scripts/audit_joint_activity.py --input-dir results/continuous_v2/joint_native_skill_drawer_access_change_use_20261007
PYTHONPATH=src .venv-libero-native/bin/python scripts/evaluate_joint_process.py --input-dir results/continuous_v2/joint_native_skill_drawer_access_change_use_20261007
PYTHONPATH=src .venv-libero-native/bin/python scripts/verify_genesis_videos.py --input-dir results/continuous_v2/joint_native_skill_drawer_access_change_use_20261007 --require-timeline
PYTHONPATH=src .venv-libero-native/bin/python scripts/build_joint_progress_report.py
python scripts/serve_reports.py --port 8123
```

独立完整解码结果保存为各运行 independent_video_verification.json；统一报告读取它，不以视频文件存在代替核查。旧名 verify_genesis_videos.py 的核查器也支持原生 MuJoCo 视频。

## Goal 验收状态

| 要求 | 当前证据 |
|---|---|
| 与 idea 对齐的设计与参考 | 已保存；尚需实际广覆盖验证 |
| 三类活动可执行 | 三类参考成立；其中饮品当前机器人不是 NN |
| 六类动态情境实际覆盖 | 已配置，未全部实测成立 |
| 可靠动态人策略与伙伴响应 | 实际神经输入／执行可审计；参与字段契约问题待修复，事实理解仍不可靠 |
| 完整双向持续重组案例 | 有局部用途更新与公开响应；完整验收尚未成立 |
| 多系统、多初始化正式评测 | 尚未开展冻结矩阵；不同开发版本不冒充正式样本 |
| 动态协调与 cobalance | 已有离返、准备、实际贡献及消息递送见证；语义约定、负担与构念效度仍未完成 |
| 视频、数据、统一报告 | 本轮已增加可执行参考、开发及失败视频统一入口；正式研究交付仍需继续 |

现有数据按 observation 同 stem 加载，动作标签来自实际执行的控制，不用未执行尾部充当训练目标。失败数据不标为专家成功。人物隐私、环境真值和评分不能直接注入被测机器人。
