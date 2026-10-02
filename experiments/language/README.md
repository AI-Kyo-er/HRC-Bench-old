# 本地语言模型决策诊断 v2.1

## 执行前冻结

本轮是自然语言共同活动的连续关键决策切片，不是物理HRC评测。三领域（装箱、餐桌、工具准备）是三个词汇场景，共用一个逻辑模板，不代表三个独立任务机制。每episode保留三物品的已接受约定、尚未接受建议和完成进度；关键决策按照任务顺序外部指定。伙伴只有在模型实际request或yield之后响应。

开发集12个实例覆盖retain/revoke/nested/reentry，正式集60个实例覆盖上述结构与nested_reentry组合留出。正式集目标反事实变体与伙伴accept/refuse独立交叉；初稿v2.0曾绑定这两个轴，尚未推理前已修正为v2.1并重新冻结。冻结文件见cases/freeze.json；Git冻结提交先于第一次开发集模型调用。开发集无nested_reentry。这里的留出只限于本项目开发提示流程，不表示模型预训练未见这些语义。

每episode分别执行full_history与oracle_summary，两者维护各自真实动作引起的轨迹。摘要由参考规则从可见事件生成，维护生效约定、待接受建议、已完成进度、伙伴可用性和公开请求响应；它不是模型免费可得的信息，是状态维护的oracle干预。模型观察接口只接受消息字符串，不接受case、条件标签、隐藏伙伴响应或标准答案。参考规则根据公开事件归约，不读取结构标签或未来响应。目标动作通过允许动作集合判分，solo与获授权的assisted均可有效，不限定唯一JSON字符串排序。

首个开发结果出现后不根据正式结果改提示、生成器或解析器。本轮不进行模型排名、显著性检验、真人成本推断或社会特异性推断。小模型用于流程校准；成功和失败都如实记录。结构差异与输入token数/决策机会一起记录，未严格匹配长度或信息密度时不得归因纯结构效应。若模型全选solo，则支撑响应机制虽然可运行，本轮不构成实际闭环能力证据。

## 本地模型与存储

模型：公开[Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct)，3.09B BF16，固定revision `aa8e72537993ba99e69dfaafa59ed015b17504d1`。按官方模型卡使用transformers chat template；推理GPU3，greedy，seed0，max_new_tokens96。包版本锁定在requirements.txt，实际依赖完整记录到结果。

大型文件全部放数据盘，项目链接使用：

- `.venv-llm` → `/data1/sieniwgroup/sieniw/HRC-Bench/venv-llm`
- `models/Qwen2.5-3B-Instruct` → `/data1/sieniwgroup/sieniw/HRC-Bench/models/Qwen2.5-3B-Instruct`
- UV/HF新下载缓存 → `/data1/sieniwgroup/sieniw/HRC-Bench/cache/`
- `results/language_v2/dev`与`formal` → 数据盘同名结果目录，保存所有prompt/response/解析错误与连续事件。
- 首轮`results/symbolic_v1/episodes.csv`亦已移数据盘并链接，SHA256不变。

```bash
python -m unittest discover -s tests -v
CUDA_VISIBLE_DEVICES=3 .venv-llm/bin/python -m experiments.language.run --split dev --output-dir results/language_v2/dev
CUDA_VISIBLE_DEVICES=3 .venv-llm/bin/python -m experiments.language.run --split formal --output-dir results/language_v2/formal
```

运行前重新检查nvidia-smi；预计3B BF16加短上下文KV与激活<12GB，实际峰值随结果记录。权重首次下载通过用户clashon后运行download模块，token=False，不读取或发送认证凭据。此处仅下载公开文件，没有上传私有数据或调用他人推理服务。

## 覆盖审查

环境外部指定下一物品，并由参考事件归约器维护完成记录与阻止重做。因此结果只检验指定步骤下的有效约定/分工响应，不能声称检验机器人自主维护进度、选择未完成子任务或恢复行动规划。完整事件轨迹保留进度，不等于模型实际使用了这些信息。

nested目前是第二物品前注入局部纠正的近似，没有子任务栈、暂停点或恢复执行；reentry是在伙伴离开/返回事件后接受指定物品分工，没有开放式伙伴进度推断。本轮没有并发物理占位、安全运动、伙伴主动反提议或真正具身行动。五个结构标签不能当作已覆盖原idea的六种交互融合结构，测试通过也不证明科学覆盖完整。

后续优先仿真闭环：把三物品/两容器活动接到物理场景与行动执行器，使观察由仿真当前状态产生，机器人实际动作与伙伴状态改变后续可行行动、进度和交互。当前自然语言观察接口可复用，外部指定步骤与文本判分器需替换。仿真选择应在本轮结果后依据正式文档、许可证和实际环境可运行性核验；本轮不额外安装仿真器，不以文本轨迹代替仿真证据。
