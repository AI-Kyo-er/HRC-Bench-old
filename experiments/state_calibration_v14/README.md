# 第十四轮：基础状态字段与Qwen3-VL纯文本参照

固定216次调用全部完成，未追加生成、改提示或运行物理。Qwen2.5-14B与Qwen3-VL-8B的24条基础状态控制联合正确均为14/24；新8B在原v13上动作协议推进37/64、联合状态1/64，在原v4上16单动作全对但12多物品full仅6正确，原工程门槛未通过。这套状态报告探针仍未充分校准，不能把结果当作结构机制证据。

## 模型、环境与输入

只读核查发现原用户模型位于`/data1/sieniwgroup/sieniw/models/Qwen/Qwen3-VL-8B-Instruct`，项目`models/Qwen3-VL-8B-Instruct`为软链。architecture为`Qwen3VLForConditionalGeneration`，4个分片共17,534,339,512字节；索引750个tensor与各分片header/数据末端一致。全部分片SHA与原HF local-dir metadata一致，再从官方固定revision只查询文件元数据，4个LFS SHA及大小全部核对一致：

`0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`

config/tokenizer/template/index也与同revision的本地下载记录对应，完整SHA在`model_receipt.json`。没有下载或改写权重。旧环境4.49实测不认识`qwen3_vl`，用户msswift的5.9可CPU导入，但未改或复用其训练环境。

新环境在`/data1/sieniwgroup/sieniw/HRC-Bench/venv-qwen3-v14`，项目`.venv-qwen3-v14`为软链。新建Python3.12 venv并独立复制旧site-packages（非hardlink），仅新环境固定transformers4.57.1/tokenizers0.22.2/huggingface-hub0.36.0，复用torch2.6.0+cu124/accelerate1.4.0。CPU native class/config/FastTokenizer导入、实际文本模板保留system/user及pip check均通过。旧环境4.49的版本及探针文件SHA在前后核对未变；安装日志与环境receipt完整保留。[官方4.57.1文档支持native Qwen3-VL及SDPA](https://huggingface.co/docs/transformers/v4.57.1/model_doc/qwen3_vl)，[固定版本依赖允许torch>=2.2](https://raw.githubusercontent.com/huggingface/transformers/v4.57.1/setup.py)。

预算为24控制×两模型48次，另新8B原v13全部128条与原v4全部40条，共216。旧14B只做24新控制，不重跑旧128/40。新8B是不同架构/训练的独立纯文本参照，不是模型规模单因素对照；没有图像或pixel输入，也不评估视觉能力。

原v13的system/history没有发现协议真值矛盾：D4检查通过后仍须finish终止，D5明确终止并恢复outer。不过字段`guidance_active`未单独给出事件映射，英文`current_blue_destination`可能被理解为实际物理区域，而中文要求是“当前应执行目标”。这些是需要校准的接口解释，不能仅凭输出模式认定为根因或内部HRI机制。

## 24条基础字段控制

全部控制的system逐字沿用v13 state system，保留22正常候选；只有user公开事实变化。真值由公开自然语言或v11 ledger归约，既不读私有case也不将答案送给action。控制是公开事实合成的纯文本，未执行机器人/伙伴，不称真实轨迹。

| 组 | 固定交叉 | 公共输入逻辑 |
|---|---|---|
| direct8 | outer左右×活动/不活动×source/neutral区域 | 仅自然语言直接声明有效outer、活动状态与当前规范目标；无accepted_child类型辅助反推 |
| scope8 | outer左右×单次开始/明确结束×neutral/outer区域 | 开始记录accepted_child；结束记录检查、撤离、检查通过、child_finished和outer_resumed。结束且物品在outer的文本补实际投递反馈以自洽 |
| update8 | 初始outer左右×接受/拒绝相反提议×source/neutral区域 | 无child，单次外层目标提议与绑定回应。提议无“等检查结束后”的条件措辞 |

左右有效outer每组4/4；direct/scope活动真假各4/4，update全不活动，这是合法状态空间的设计限制，不能声称所有三字段全独立反平衡。当前规范目标由active与有效outer决定，物品所在区域不决定规范目标。scope结束/outer多一条投递反馈，区域对照因此含信息混杂，不是严格单因素实验；控制整体也不等长度。

主控冻结前逐条审核后修正update措辞，修订前review/输入/源文件保留在raw。初次永久测试捕获adapter把v4单动作自然语言user误当JSON的缺陷；只对state/v13解析JSON后修复，失败源与focused/full日志保留。以上发生在冻结及生成前，未按模型分数调整。

## 基础结果

| 模型 | direct联合 | scope联合 | update联合 | outer字段 | active字段 | current字段 | 联合 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5-14B | 8/8 | 6/8 | 0/8 | 24/24 | 24/24 | 14/24 | 14/24 |
| Qwen3-VL-8B | 6/8 | 7/8 | 1/8 | 24/24 | 24/24 | 14/24 | 14/24 |

两模型各10错全部仅current字段错误，均输出neutral；各自共18次current=neutral。包括物品位于source的错误，不能单凭neutral案例断言模型只是在复制物理区域。

每模型每组4组区域配对，联合评分随区域变化的组数：14B direct0、scope2、update0；8B direct2、scope1、update1。scope结束的区域配对附带投递反馈差异，已单列混杂。所有48条control的公开history、区域、truth、原response、字段评分在`control_and_direction_audit.json`；配对逐例在`paired_field_audit.json`，不只报总数。

## 新8B复用原v13全部128输入

原128条messages逐字保留：64action/64state，action并未获得state答案。状态解析严格JSON/schema/types/enums，键序单列合规不改变语义；拒绝duplicate/missing/extra keys、bool字符串等，不修复/重试。本轮216条均无parse错误或截断。

| 阶段 | 动作推进 | outer正确 | active正确 | current正确 | 联合状态正确 |
|---|---:|---:|---:|---:|---:|
| D4 | 32/32 | 32/32 | 1/32 | 32/32 | 1/32 |
| D5 | 5/32 | 21/32 | 32/32 | 0/32 | 0/32 |
| 全部 | 37/64 | 53/64 | 33/64 | 32/64 | 1/64 |

所有current输出仍为neutral，active输出false63次/true1次。D5动作错误为13次重复finish、9次重复已完成green、5次错误blue方向；没有将重复finish解释为目标记忆错误。五个错方向中4个during/rejected跟随未接受提议，1个before/accepted/initialright/seed61正常菜单跟随初始目标。D4全选择finish，未执行其他候选，不能声称所有操作能力已经验证。

| 独立状态字段×动作 | 状态对动作对 | 状态对动作错 | 状态错动作对 | 状态错动作错 |
|---|---:|---:|---:|---:|
| outer字段 | 35 | 18 | 2 | 9 |
| current字段 | 32 | 0 | 5 | 27 |
| 联合状态 | 1 | 0 | 36 | 27 |

`paired_field_audit.json`有D4/D5、timing、acceptance、menu与initial分组交叉表；`summary.json`还有完整交叉条件、旧v13逐query输出/score对照。正常/反序是离线菜单变体，两seed与模板不是独立结构样本，不作显著性推断。独立query不是模型内部知识测量，未执行动作的协议推进也不是物理成功或闭环完成率。

## 新8B复用原v4全部40输入

| 原冻结组 | 可接受推进 |
|---|---:|
| 单动作 | 16/16 |
| 多物品full_history | 6/12 |
| 多物品public_progress_aid | 10/12 |

full错误包括5次未获授权assisted、1次错误目标；aid两错都是未获授权assisted。单动作实际选择place/assisted/careful/yield各4次；没有新增候选或改旧提示。原预设single16/16且full12/12的工程门槛为false；aid不替代full，基础控制也不合并成新gate。原3B记录只是旧提示描述参照，本轮没有重跑3B。

## 冻结、运行与归档

freeze SHA256：`71cb6b75cd3b9a98b209f801c4b3dd18985573c413374f9026e49d2401d49fb5`。输入、全部运行源/评分与依赖/来源SHA在freeze；事后仅增加只读audit/receipt/文档，未改冻结或生成配置。每条calls保存原messages/output/token与评分；全部错误原query另在`raw/incorrect_calls.json`。

两模型均单GPU、BF16/SDPA、greedy seed0、batch1、max96，不量化/offload/多卡。14B控制最长1406tokens、估需31244MiB；8B最长2160tokens、估需19795MiB。两次启动前实时GPU2空闲48494MiB，顺序运行并释放前一模型：14B句柄94898/PID45166，24calls真实exit0；8B句柄67541/PID45899，192calls真实exit0。峰值allocated分别约28760/17267MiB；两个PID及自有GPU资源均已消失，无活句柄。原生成配置内采样参数的日志警告被保留，实际generate显式do_sample=False。

新环境nativeCPU API/pipcheck通过；最终focused10项、全套73项永久测试通过。首次失败日志保留，修复后的全套只重验一次。216输入来源、token、parse、评分与分组summary独立审计通过，旧env前后未改。测试属于输入/协议/解析检查，不当作物理或模型成功证据。

完整raw约7.6MB，数据盘软链；隔离venv约6.2GB，既有模型保持原路径。`execution_receipt.json`记录确切字节、模型环境/官方SHA核验来源、真实句柄终态、GPU前后与全部artifact SHA。

```bash
.venv-llm/bin/python -m unittest tests.test_state_calibration_v14
.venv-llm/bin/python -m unittest discover -s tests
.venv-llm/bin/python -m experiments.state_calibration_v14.dataset
.venv-llm/bin/python -m experiments.state_calibration_v14.run freeze
CUDA_VISIBLE_DEVICES=2 .venv-llm/bin/python -m experiments.state_calibration_v14.run evaluate --model qwen2_5_14b
CUDA_VISIBLE_DEVICES=2 .venv-qwen3-v14/bin/python -m experiments.state_calibration_v14.run evaluate --model qwen3_vl_8b
.venv-llm/bin/python -m experiments.state_calibration_v14.audit
.venv-llm/bin/python -m experiments.state_calibration_v14.receipt
```

freeze/evaluate拒绝覆盖已有冻结/输出；未来执行须重新检查GPU。到本轮归档为止，不追加同模板提示变体、模型调用或物理实验。
