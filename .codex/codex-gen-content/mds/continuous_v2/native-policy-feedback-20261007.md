# 2026-10-07：实际执行反馈、协调关系与物理完成

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent（inline）
- Origin Mode: run
- Verification Status: UNVERIFIED（完整研究效度）；具体模型/控制/视频/物理重建按产物核查
- Version Label: native_dynamic_feedback

上一轮属于progress，本轮也推进了真实代码与实验；完整研究goal继续active。

## 完成的核心改动

去掉人输入恒定`placing_bowl`标签，机器人反馈来自实际EE速度、物体高度变化。
人的反馈含执行意图、运行阶段、身体/指尖目标与距离、推物实际剩余距离。
Qwen自己生成多步plan、目标与等待条件，程序只执行当次动作，不自动路由其plan。
模型memory_note与实际执行观测分别保存，避免“已返回”的文字覆盖半途停止的测量。

首两条发现模型把物体名plate_1当成目标区域，并误读机器人分工。
执行器将无效push转换为observe，却没有反馈具体拒绝理由。
在这两条完整结束后，补上公开动作参数范围、双方分工和明确的命令拒绝反馈。
不替模型选合法替代动作；允许有效但不推进原分工的请求。
前后接口不同，六条件不能当作单一固定配置比较。

新增两种实际协调关系：prepare_receptacle（先准备盘子再合法放置）、
shared_workspace（人移动cookies到附近，机器人操作邻近的碗/盘子）。
前者有公开前置条件，后者只要求双方分别工作，未证明布局必然迫使空间冲突。
基础技能仍以取放/推物为主，不能称全面多样化技能集。

## 已完成六条实际运行

都为task2/init0/seed41；两种合成人格倾向；20Hz、最多20秒；episode记忆。
human Torch seed=41+1000*task_id+init_id，robot服务采样状态未按条件重置。
全部逐条件控制/视频、人物、公开执行反馈核查通过，运行期源文件无变更。

| 条件 | 原始robot | human | 原始共同 |
|---|---:|---:|---:|
| moving_receptacle cooperative | 1 | 0 | 0 |
| moving_receptacle assertive | 1 | 0 | 0 |
| prepare_receptacle cooperative | 0 | 1 | 0 |
| prepare_receptacle assertive | 0 | 1 | 0 |
| shared_workspace cooperative | 1 | 1 | 1 |
| shared_workspace assertive | 0 | 1 | 0 |

前两条20次原始push均因无效目标参数转为observe；不是纯粹选择等待。
后四条人的接触推物全部达成目标，但不由此声称人格或接口因果提升。
prepare cooperative最大碗抬升约17cm；几何关系在前置满足前跳变7次，
这是观测关系跳变而不是7次完整放置。assertive没有这类跳变，也没有合法贡献。
共享cooperative 8.5秒原始几何成功、17π调用、9人决定，真实cookies接触推动。

## 关键假阳性与物理判据修正

共享cooperative末帧仍有碗/夹爪接触，夹爪开度约7.7mm，不能算已释放放置。
旧score不改写；`placement_verification.json`保存末帧接触诊断，旧数据缺连续几何
判定，不能事后证明持续释放/稳定成功。运动与显示资格通过并不是物理完成证明。

原生入口当前默认released_stable，只支持明确的单一On任务，不默默回退几何成功。
要求原生On关系、真实接收盘接触、无夹爪接触且实际开度≥40mm、物体与接收盘
速度均<0.08m/s连续0.2秒。`placement_evidence.jsonl`保存每个控制步测量，独立verifier重建。
它只改变评估和终止条件，不替模型开夹爪，不改变模型动作。新的真实伙伴运行
在`native_released_collaboration`，最终结论以该目录summary与独立placement_verification为准。
该真实运行20秒结束：human完成、robot未完成、共同未完成，40次π推理、20次人决定。
夹爪曾有49个释放观测，但没有形成原生On关系与接收盘接触的稳定放置，stable duration最大0。
末帧仍有夹爪接触。独立控制、人物、公开反馈与物理判据重建均通过；不能说物理任务已经成功。

## 第二种机器人架构

直连中国ModelScope `zixiaoBios/openvla-7b-finetuned-libero-spatial`，16文件约15.1GB，
逐文件SHA256核验，无环境代理；未核对上游权重哈希身份。
模型保存在共享models，仓库models/openvla_libero_spatial软链接访问。
官方OpenVLA代码固定c8f03f48af692657d3060c19588038c7220e9af9，位于项目数据盘external。
Transformer4.40.1、timm0.9.10、tokenizers0.19.1、accelerate0.33.0、psutil7.0.0
隔离overlay来自清华PyPI，不改现有模型环境。
首次载入缺Accelerate已补齐；严格载入无缺失/意外/形状不匹配。
真实原生Sim 11秒、220次动作/推理，原始任务未完成；控制与视频链路通过。
只消费外部相机与语言，兼容腕部/末端字段未使用。SDPA推理、未匹配官方默认中心裁剪，
仅接入诊断，不作OpenVLA能力或HRC排名。当前没有两种算法的有效HRC比较。

## 核查、报告与未完成项

最新报告`experiments/native_dynamic_feedback/index.html`保存真实Sim视频与同步人决定。
最终报告共8段真实Sim视频，包含严格物理判据片段；生成式模型的失败与原始几何假阳性都保留。
当前非归档回归146通过、1项JAX依赖跳过；归档旧测试导入问题仍未处理，不属于当前通过范围。
关键提交c297af7、082541a、cbe79e5、06b9f4c。

仍需完整手/身体接触动力学、多个先进机器人算法的匹配评测、更多技能和环境、
生成式开放意图/角色协商、持续世界、人格效度与统计协议。
不能把六条原始几何数据、一个接入的第二架构、人物外观或score修正当成成熟Benchmark完成。
