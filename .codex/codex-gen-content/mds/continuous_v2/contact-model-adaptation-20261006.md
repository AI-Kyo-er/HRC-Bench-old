# 2026-10-06：实际模型适配、生成式记忆与真实视频收尾

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-06
- Verification Status: UNVERIFIED（完整研究效度；执行、产物与链路已核查）
- Version Label: contact_model_adaptation_v1

当前这批训练与六条评测均完成，训练和评测进程退出码为 0。
完整 Dynamic Human Policy HRC Benchmark 的 goal 仍 active，不能标记 complete。

## 实际训练

采用官方 OpenPI 的 init_train_state / train_step，从已有本地 π0.5-DROID 进行
400 步 LoRA 适配，batch size 2、seed20。仅更新 49,987,584 个 LoRA 参数，
保留原 DROID 归一化和动作标度，不改成几何教师驱动的评测机器人。

两批已有接触示范共17条运行、11条有效、729帧；仅选完整15步动作窗口，
候选 train472 / dev103。固定16个dev窗口、固定噪声上的 flow-matching loss
从1.673917降到0.030588。dev只有red/blue有效示范，green只有一条成功train示范；
这不是完整验证集、独立样本泛化或仿真成功率。

- 权重：`/data1/sieniwgroup/sieniw/models/HRC-Bench/pi05_droid_contact_lora_v1/400`
- 记录：`results/contact_training/pi05_lora_v1/`
- 入口：`scripts/train_contact_lora.py`、`scripts/run_contact_lora.sh`
- 实际启动前检查显存，训练单独使用GPU3，约32GB；服务单独使用GPU2，约20GB。
- 本轮没有下载模型或数据；离线训练只解析已有本地权重/缓存。

## 独立基本操作

`pi05_lora_atom_evaluation`：red/blue/green，各seed20、30秒、15Hz，每tick重新推理，
observing伙伴不接管。1350次真实模型推理、1350个原生关节动作；三项全未完成，
机器人接触抬起证据与合法贡献均为0。训练下降没有转化为可靠闭环操作。
视频底部仍沿用原生配置标签，但模型服务 metadata / checkpoint 明确为LoRA权重。
后续已把服务metadata读取移到后端创建前，使新视频显示实际策略名称。

## 生成式伙伴联合运行

`pi05_lora_qwen_memory_contact`：三任务seed20、最长60秒、15Hz、最多执行8步动作块，
cooperative Qwen3-14B。335次VLA推理、2644个原生关节动作、181次伙伴决定与181条
生成式经验，解析错误0。结果如下：

| 场景 | 活动 | 机器人合法贡献 | 人合法贡献 | 关键观察 |
|---|---|---|---|---|
| relay | 未完成 | 0 | 0 | 伙伴只围绕blue观察/接近/持握，未完成red前置贡献 |
| concurrent_overlay | 完成，56.2667秒 | 0 | 3 | 人完成red/green收纳及blue留用，不能计成机器人成功 |
| robot_induced_rebalance | 未完成 | 0 | 0 | 人操作red但缺blue前置；实际放置被阻止提交 |

三个episode运动核验通过，记录与视频无对象吸附或控制期坐标写入。
模型输入双相机像素哈希、五键输入边界、输出动作转换与物理请求均独立核查通过。
运行中src源码未改动，两个新批次 provenance 的 source_files_changed_during_run=[]。

Qwen现在读最近10次带时间的公开观察、4次决定、12条自身生成经验；完整内容
保存到human_memory.jsonl。它不是手工信任表，但记忆中的推断可能错误，且每个episode
重置。relay末期16条公开对话窗口已不含初始red分工，伙伴还把blue称为自己的任务。
未验证记忆效用、跨活动保留、真人规律或因果关系。

## 评分和输入修订

- 截止tick冻结成功、事件与贡献，视频尾部settling不能增加成绩或继续人类决策。
- 提前放置且缺前置条件的物体不能在前置后来完成后自动获得贡献；需要重新操作。
- 这批已执行的机器人初始输入去重丢失了附加的公开前置说明，不能用于衡量理解依赖。
  运行结束后进一步修订：只去重初始普通搬运句，任何附加说明和后续分工保留。
  回归测试已通过，尚未对该输入修订重跑本批模型；不要把未来源码等同于已执行版本。
- 基础英文操作指令与中文运行对话未做语言条件对照。

## 视频与报告

本接触阶段共33条视频，7组保存核验均verified：人体校准1、较早真实模型6、
反馈执行器3、初始示范15、反馈示范2、LoRA基本操作3、新联合运行3。
每条完整解码并核对FPS/帧数与时间轴；失败运行也保留原始视频。

统一入口：`experiments/dynamic_contact_20261006/index.html`，包含9条嵌入视频，
分别呈现操作校准、最新联合运行、模型训练与独立基本操作、实际示范。
浏览器核查记录在report_verification.json，原始结果来源在evidence.json。

有效回归测试109项通过；归档的legacy_llm_direction不运行。
关键训练/记忆/评分代码提交为2a38fbe；输入保留修订与最终报告另行提交。
用户提供的未跟踪COOPERA PDF不纳入提交。临时帧检查文件在收尾删除。

## 后续沿原始研究目标推进

优先解决可靠机器人基本操作，并持续给模型保留公开承诺、依赖与剩余贡献；
再开展不同生成式伙伴、跨活动记忆、开放目标、九类任务组合与多真实模型评测。
目前只有一种机器人模型及一种合成伙伴人格，不能用活动1/3或未校准cobalance总分
作能力排名。人体是六自由度接触手与IK显示骨架，仍不是完整人体动力学或真人。
推理同步暂停模拟时钟，异步人的持续行动与推理延迟影响尚未测试。
