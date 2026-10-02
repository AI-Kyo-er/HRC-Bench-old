# 本地VL模型纯文本基础参照

本轮复用用户已有Qwen2.5-VL-7B-Instruct完整权重，建立不同架构/训练的独立纯文本基线，不把结果解释为模型规模的单因素因果效果。没有图像输入，本轮不评估视觉能力。官方模型说明见[Qwen模型卡](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)，本地实际API为transformers 4.49.0的`Qwen2_5_VLForConditionalGeneration`。

原始目录`/data1/sieniwgroup/sieniw/models/Qwen/Qwen2.5-VL-7B-Instruct`保持只读，通过项目`models/Qwen2.5-VL-7B-Instruct`软链接访问。五个分片共16,584,414,560字节；`.mv`仅标记可变`Revision:master`，没有可靠的不可变HF revision，所以记录`revision=null`，不编造来源提交，也没有声称与官方HF特定revision哈希一致。`results/local_vl_v4/local_weights_receipt.json`记录全部权重与配置SHA、实际目录、配置和纯文本API检查。

固定输入直接复制既有`model_scale_v4/cases/freeze.json`的40条records：16单动作、12多物品全历史、12公开历史归约辅助。原始messages、20候选、集合评分和generation参数逐字保持；system中的具体green/right输出示例也保留。辅助是额外公开进度帮助，单列结果。评分标签只用于判分，不进入模型。旧3B结果只作描述参照，不声称重新完整复现。

工程门槛预先固定为单动作16/16且全历史12/12，辅助成绩不能代替全历史门槛。这只是小集可用性检查，不是统计能力证明；未过则分类诊断，不自动扩展物理formal。

运行`prepare`先只读核验五个分片/配置SHA和40条文本tokenizer输入，再冻结新版本代码、原输入、权重回执。`evaluate`再次核验SHA，记录GPU预检（BF16权重字节+3GiB裕量），完整模型单卡BF16/SDPA，seed0、greedy、batch1、最多96新token，无量化/CPU卸载。继承原纯文本predict，输入只有`input_ids`和`attention_mask`，逐调用保存messages、原始输出、token/时间和错误分类。完整调用/日志在数据盘，项目`results/local_vl_v4/raw`软链接。

```bash
.venv-llm/bin/python -m experiments.local_vl_v4.run prepare
CUDA_VISIBLE_DEVICES=2 .venv-llm/bin/python -m experiments.local_vl_v4.run evaluate
.venv-llm/bin/python -m unittest discover -s tests
```

GPU编号是本轮启动前实查选出的卡，后续运行必须重新用`nvidia-smi`检查。冻结和结果目录拒绝覆盖。正式结果、峰值显存、错误类型见`results/local_vl_v4/basic_summary.json`和执行回执。

本轮真实40次调用结果：单动作16/16、全历史9/12、公开进度辅助10/12，JSON/候选解析错误0、截断0。固定门槛未通过，不启动物理pilot。3B旧参照依次为15/16、4/12、6/12，未在本轮同条件重跑，不据此作规模因果结论。VL完整参数8,292,166,656，峰值allocated 17,100,109,824字节（15.93GiB）；GPU2启动时free30,412MiB，程序结束后恢复到相同值，没有残留本轮GPU进程。

全历史三处失败均在green已完成组：两次重复green、两次目标错误（其中一次同时属于两类）；辅助两次错误均为目标错误。12全历史输出10次选green、2次选red；辅助输出8green、2red、2blue。单动作实际触发4次yield、2次assisted，拒绝组4次均careful，request_clear没有被选择。单步候选选择不等于持续物理执行的协调行为。`error_audit.json`给出五个失败调用的规范输出、可接受集合及只读公开历史归约，执行回执验证40条完整record与原冻结精确相等。

具体green/right示例及语言/方向表达仍可能影响选择，但本轮没有改提示检验VL上的因果影响，不能将样例当唯一失败原因或把9/12称基础已修好。原3B独立锚定诊断显示分布敏感但去例不提升，见`interface_anchor_v4`。本轮保持旧提示与门槛，以免看结果后改变验收。

预检回执中的`estimate_basis`继承原14B函数，其`official`文字不适用于本地未知revision缓存；本轮计算实际使用核验过的本地VL分片字节。这只是描述文字勘误，没有修改已冻结代码或结果，也不表示验证过官方HF权重SHA。
