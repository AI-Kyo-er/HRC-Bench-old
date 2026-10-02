# 第十九轮：新接口识别与真实自主持续闭环

固定官方Qwen/Qwen3-14B revision `40c069824f4251a91eefaf281ebe4c544efd3e18` thinking配置：BF16、SDPA、batch1、temperature0.6/top_p0.95/top_k20/min_p0、max_new_tokens8192。旧v17 thinking已通过旧40项工程门槛，不能代替本轮新六动作的自主能力证据。模型推理期间物理时钟暂停，推理墙钟与仿真共同活动时长分开。

先运行12项明确指令识别（六语义×正常/反序菜单），不执行所选动作；其真实观察来源为v18 seed100/none/ready/公开账本参考。请求和red取left例decision0，等待取left decision1（请求已接受、尚未交付），blue左右分别取对应例decision3（真实交付、尚未放盘），完成声明取left decision4。只追加预设explicit_next_instruction和反转候选。识别不是自主能力充分门槛，成绩不筛掉后续条件。

随后完整历史12条，再公开账本帮助12条自主闭环：初始blue左右×无更新/接受相反提议/拒绝相反提议×ready/busy，seed100、正常六候选、最多12决策。每回合独立World，无预执行red；后续输入来自当次实际动作、伙伴回应与物理状态。账本只归约同一公开历史与实际区域，是额外计算帮助基线，不提供下一动作、不筛菜单，不当模型自行记忆。合法但慢的等待/拒绝/重复计成本，不能一概算语义错。declare_done允许错误并立即实际终止，私有符合性只在终止后评分。

冻结SHA `2615312d805c9f20dee5b7bdf0229d3853255540a20462ae40a5e855c1691da1`：识别最长2641token，初始最长1964token，既有真实参考动态最长2968token。预冻输入上界8192+输出8192=16384，官方context40960；batch1 BF16 KV2.5GiB+29,536,665,640bytes权重+3GiB工作区估算要求33801MiB。超界保存基础设施失败，不截历史/补采样。解析按最后think结束边界，仅之后严格JSON候选；失败调用ep.act(None)，消耗一次决策、零物理tick，不替模型执行fallback。

新8项focused永久回归及完整129项tests通过，CPU冻结句柄81918、全套测试37212真实exit0。正式GPU2句柄98899/PID121752按冻结顺序运行；结果尚待真实终态与全量独立审计，当前不声称闭环完成率。大原始输出与逐tick轨迹在`results/sustained_model_v19/raw`数据盘软链。旧v18/v17所有运行源及冻结保持。
