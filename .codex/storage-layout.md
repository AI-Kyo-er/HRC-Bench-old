# 数据盘目录约定

全局规则见 [/home/sieniw/.codex/AGENTS.md](/home/sieniw/.codex/AGENTS.md) 第9条。模型统一存放，项目专属文件按项目名称管理，仓库通过软链接访问。

| 内容 | 实际位置 | 仓库入口 |
|---|---|---|
| Qwen模型权重 | `/data1/sieniwgroup/sieniw/models/Qwen/<模型名称>/` | `models/<模型名称>` |
| 原始实验结果 | `/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/` | `results/legacy_llm_direction/` 下的 `raw` 等软链接 |
| v1 pilot结果 | `/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/pilot_v1/` | `results/pilot_v1` 软链接 |
| v2持续协作结果、报告与动画 | `/data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/` | `results/continuous_v2` 软链接 |
| 早期Python环境 | `/data1/sieniwgroup/sieniw/projects/HRC-Bench/venv-llm/` | `.venv-llm` |
| Qwen3 Python环境 | `/data1/sieniwgroup/sieniw/projects/HRC-Bench/venv-qwen3-v14/` | `.venv-qwen3-v14` |
| 项目资源及缓存 | `/data1/sieniwgroup/sieniw/projects/HRC-Bench/{assets,cache,pip-cache}/` | 程序需要时从对应路径访问 |

日常报告链接和结果操作使用 `/home` 下的仓库入口。新增实验结果目录时，先在数据盘
创建实际目录，再用 `ln -s` 在仓库中建立对应入口；运行命令通过入口输出数据。
`results/continuous_v2` 已纳入 Git，只保存软链接目标，不保存数据盘上的实验文件。

## 2026-10-03迁移

原 `/data1/sieniwgroup/sieniw/HRC-Bench/` 中的三个模型（Qwen2.5-3B-Instruct、Qwen2.5-14B-Instruct、Qwen3-14B）移至统一模型目录，其余项目专属内容移至 `projects/HRC-Bench/`。旧数据盘顶层目录已移除。

迁移采用同一文件系统内的重命名，没有复制或重新下载权重。更新了38个仓库软链接，以及Qwen3虚拟环境中7个含旧绝对路径的启动、激活及配置文件；早期环境的入口使用仓库路径，无需改写。

文件迁移前后核对了147787个条目的设备号、inode、类型、大小和修改时间；核对完成后才修复环境启动路径。详细路径映射见 [storage-migration.json](storage-migration.json)。

旧实验源代码、冻结文件、运行回执和报告中的绝对路径是历史记录，保留原文。查找其对应实体时，将旧路径中的 `HRC-Bench/models/<模型名称>` 映射至 `models/Qwen/<模型名称>`；其余 `HRC-Bench/` 映射至 `projects/HRC-Bench/`。复现旧提交时，须按此映射重建模型、环境及原始结果的软链接，并为重跑使用新的输出目录。
