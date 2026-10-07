# 动态共同活动：可执行性与神经策略进展

[真实 Sim 视频统一入口](index.html) · [关键行为分析](BEHAVIOR_REVIEW.md) · [参考协议](PROTOCOL.md) · [理想感知系统设置](SYMBOLIC_PROTOCOL.md) · [六类情境与证据门槛](SITUATIONS.md) · [整体研究设计](../dynamic_joint_activity_20261007/DESIGN.md)。

[参与契约修复协议](CONTRACT_PROTOCOL_20261008.md) · [第二视觉系统协议](VISUAL_SYSTEM_PROTOCOL_20261008.md) · [可选技能与具体情境协议](SKILL_BANK_PROTOCOL_20261008.md) · [正式评测计划与当前准入状态](EVALUATION_PLAN.md)。当前44段视频均通过独立解码／时间轴核查，含43条完整120秒轨迹和1条部分崩溃诊断；44段全部通过浏览器播放／拖动／Range、407个链接及375px手机布局核查。280项有效回归通过、2项跳过；测试不证明策略效度。

目的：检验三个具有跨主体贡献依赖的日常活动是否可执行，以及在线生成的人与真实机器人系统能否建立、维持和调整活动。此批是开发及可执行性实验，尚无冻结的正式统计评测。

人的策略为 Qwen3-14B，无抓放 LoRA；策略与执行分离，连续运动学持物约束只实现其所选贡献。机器人使用 π0.5 / LIBERO 原生 MuJoCo 场景及 7D OSC，不瞬移或吸附机器人。这里的视频是实际原生仿真，不能称为 Genesis 视频。直接 VLA、视觉协调＋VLA、理想几何协调＋VLA分别记录；共享冻结权重不共享人私有上下文。

最新init2 / seed63三类固定人参考均由实际π0.5完成：点心20.8秒填装、饮品27.45秒上架、抽屉17.8秒打开。此前早期参考来源保留如下，不把轨迹反馈与当前模型推理混同。

三个早期完整参考：

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
PYTHONPATH=src .venv-libero-native/bin/python scripts/export_joint_development_dataset.py
python scripts/serve_reports.py --port 8123
```

独立完整解码结果保存为各运行 independent_video_verification.json；统一报告读取它，不以视频文件存在代替核查。旧名 verify_genesis_videos.py 的核查器也支持原生 MuJoCo 视频。

## Goal 验收状态

| 要求 | 当前证据 |
|---|---|
| 与 idea 对齐的设计与参考 | 已保存；尚需实际广覆盖验证 |
| 三类活动可执行 | init2三类参考均实际π0.5成立；人NN=0，不是动态策略成绩 |
| 六类动态情境实际覆盖 | 已配置，未全部实测成立 |
| 可靠动态人策略与伙伴响应 | 实际神经输入／执行可审计；返回＋搬物契约及抽屉底面支撑漏报已修复；新伙伴条件仍待实测，事实理解仍不可靠 |
| 完整双向持续重组案例 | 有局部用途更新与公开响应；完整验收尚未成立 |
| 多系统、多初始化正式评测 | 尚未开展冻结矩阵；不同开发版本不冒充正式样本 |
| 动态协调与 cobalance | 已有离返、准备、实际贡献及消息递送见证；语义约定、负担与构念效度仍未完成 |
| 视频、数据、统一报告 | 本轮已增加可执行参考、开发及失败视频统一入口；正式研究交付仍需继续 |

现有数据按 observation 同 stem 加载，动作标签来自实际执行的控制，不用未执行尾部充当训练目标。失败数据不标为专家成功。人物隐私、环境真值和评分不能直接注入被测机器人。

[开发行为数据](../../datasets/dynamic_joint_activity_dev_20261008/README.md)已经全量加载核查：43条完整轨迹、12480组观测、103200步动作。相同stem在不同run下有独立sample_id，目录软链避免重复大文件，不创建配对manifest。后续新增轨迹后的实际数量以dataset_verification.json为准。

新开发批针对点心临时饮品需要、饮品具体用途纠正、抽屉机器人请求展开；私有事实指明实际物品，双方公开了解可选择的原生操作库。高层NN选择skill_id，真实VLA执行；库内操作的实际成功仍需验证，不能将原始任务／保持两选项的局限当广义HRC结论。

本轮原生推理抽屉的完整结果已加入报告：曾放下奶酪，之后再次取出，终态仍持物；不能算完成。返回＋搬物和抽屉底面支撑测量已按版本修复。跨活动加入／纠正及测试初态六条参考的预定设置见 [跨活动资格协议](GROUNDED_CONTRIBUTION_PROTOCOL_20261008.md) 与 [测试初态参考协议](TEST_INITIALIZATION_REFERENCE_PROTOCOL_20261008.md)。未结束的条件列待回收，不计发布数量。

本轮六条测试初态参考与三条工具人条件均已终态，无待回收运行。完整工具＋理想测量协调的点心条件出现并维持神经共同活动物理链；严格工具话语26次失败、完整饮品10次不支持的动作及错误柜顶完成声明仍保留。伙伴有效性与自然意图到可执行贡献的接口仍待改善，不能将动作语法、缺少合理放置目标或未持物造成的错误归为具身模型的HRC边界。

[自然人贡献／沟通与真实目标协议](HUMAN_DECISION_PROTOCOL_20261008.md)已固定。新饮品纠正及抽屉暂离返回条件均已结束，完整输入、控制、支持面与视频核查通过，已加入结果和数据。结束声明不标记成功；柜顶目标可按保存的碰撞几何和实际姿态独立重建。
