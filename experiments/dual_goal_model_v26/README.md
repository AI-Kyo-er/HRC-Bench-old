# 双目标持续活动的神经闭环比较（v26）

复用第25轮已独立验收的World/12菜单与公开事务，固定16局部闭环在前、64完整闭环在后；目前先准备代码、CPU冻结和独立非任务显存预检，正式任务必须待探针回收验收。先仿真、后真机。不回改第25轮源码/输入/成绩，不根据本轮部分输出挑条件或重新采样。

## 输入与完整条件

完整条件I×acceptreject×sameopposite×确认beforecheck/afterhandoff形成16组，每组直接/关系×fullhistory/publicledger四臂。第g组将四臂基础顺序[direct-full,direct-aid,relation-full,relation-aid]左移g%4；模型每决策d的种子260000+100floor(g/2)+d。局部按F×G四组左移h，每决策270000+100h+d。物理seed120，完整48/局部12预算，yield1920，指定事实等待6000。80行与顺序/静态源/初始ids在freeze.json固定，没有依据局部结果删完整条件。

局部前缀由参考在新World真实前送/red-left/检查台/检查服务/空返far，保留全历史、时钟和总成本；模型从同一World的真实局部边界继续，prefix不消耗模型d/自主预算，不算局部自主完成。静态初始/局部消息来源于第25轮实际记录，正式执行逐字核对；后续分叉由实际动作产生，不用旧参考后续状态替换。

system继承v25公开规则无变动。只在独立新观测的workspace.notes澄清“运输循环”指载台前送/返程，不是整个活动；载台扫掠right区的风险公开，已far稳定无active时可整理green。两种表达/视图共同使用相同澄清，exact old/new保存在freeze。完整历史不截断。

aid额外归约当前有效blue/green目标及green表达、公开提议绑定/pending关闭状态、已公开scope/检查进度、由当前物理区域判断的done/remaining和公开载台义务/当前motion。只读history、physical_placements、当前carrier与motion，不读case的配对q/F/预定回应、私有score或未来。直接臂不暴露q，关系目标计算帮助和显式当前答案是额外辅助，不宣称两臂计算需求相同。

## 解析与实际终止

官方Qwen3-14B revision40c069824f4251a91eefaf281ebe4c544efd3e18，4.57.1环境、原生thinking、BF16单卡SDPA；temperature .6/top_p .95/top_k20/min_p0，max8192。沿v19最后think边界及原JSON/候选parser，缺边界或错误最终格式返回None，ep.act(None)实际耗1决策/0tick并公开未知候选，不找reasoning中的答案、不fallback或重抽。只有生成成功才产生动作，原始ids/输出在物理执行前先存calls.json。

安全但错误目标仍可真实执行，合法慢动作和暂存不自动记错；旧合法位置因更新失效不追溯违规。declare_done随时实际终止、不补救；预算失败、解析错误、输入容量、真实技能失败、全tick接触安全和最终任务不满足分开。失败终止耗时不作为成功完成效率。完整history超24576保存容量失败，不能删历史。仿真在推理期间暂停，model墙钟独立记录，不是人机实时流畅度。

## 非任务容量预检

CPU冻结单个非任务system/user及普通hello文本填充，官方thinking模板输入精确24576tokens、seed2699000。同一Backend.generate路径，输出8192；仅探针min_new_tokens8192防EOS提前终止，正式options不带。显式logits_to_keep1，return_dict=False、scores/logits/hidden/attentions不保存。没有任务World/候选/正确动作，输出不作能力评分。

总输入输出预算32768低于原生40960，KV纸面BF16 batch1=5GiB；权重29,536,665,640bytes+KV+3GiB工作区规划36361MiB，3GiB不是保证。实时选择free≥45000MiB的单卡；实测peak_reserved加2048MiB必须不高于启动free，探针结束free也至少2048MiB才合格。最终输出token通常不再forward，32768是保守KV上界；不通过开启return_dict测缓存伪称与正式完全相同。记录allocated/reserved真实峰值/加载信息、长度/输出ids/墙钟及前后nvidia。

## 测试与独立审计来源

CPU首次11focused通过；增加明确未来acceptreject不可见与handoff生成/晚观察反例后13focused与完整228通过。后来新增独立audit的4项反例，首次17项包括导入旧TestCase被重复收集的13项；1error为测试summary缺record_id。原失败log/源保留，仅补替身字段并改module导入，新增4/4通过；最终全套232（95774）真实exit0。不把替身单测当新真实物理证据。

freeze62996089023f72de804f31bf2fc64662a3cbfb11f59ce6ed8b1d9af61d597b4e保持不变。audit.py与新增audit tests在CPUfreeze之后写入，单独SHA/副本归档，不伪称原freeze已包含；它们不改变执行/输入/在线评分。独立全tick审计重算接触/支撑/持续非目标/服务/循环与事件，逐步重建消息/token/种子/parse/公开aid/成本。早声明可以尚无after事务，零tick请求必须按序列核对最后cycle注解；任务失败不自动当审计错误，真实禁止接触仍保留失败。

```bash
.venv-qwen3-v14/bin/python -m unittest tests.test_dual_goal_model_v26 -v
.venv-qwen3-v14/bin/python -m experiments.dual_goal_model_v26.run freeze
# probe/run均需先实时显存检查并设单卡CUDA_VISIBLE_DEVICES；probe完成验收前不run。
.venv-qwen3-v14/bin/python -m experiments.dual_goal_model_v26.audit
```

raw全部在数据盘软链。准备阶段回执与后续正式结果分开；单模板单物理seed不构成结构留出，shared seed不保证输入/轨迹相同。直接目标的额外信息、确认时机的提前工作/新近程度、可自主返工与失败等解释边界随结果保留；不将结果当完整六结构或HRI特有机制。

## 已完成准备证据

CPU冻结16231/PID247069、最终全套95774/PID251544及非任务容量探针92554/PID247870均真实exit0。探针在GPU3启动free48492MiB；输入精确24576、输出8192，实测peak_reserved36694MiB，相对启动free余量11798MiB、探针结束free11326MiB，四项检查均真。allocated/reserved与生成时长、完整原始ids见`results/dual_goal_model_v26/capacity_probe_receipt.json`及raw/probe/call.json，加载记录另存。探针进程已退出，不能把该终态句柄当作正式任务活句柄。

`preparation_receipt.json`记录80初始输入冻结、13定向/228早期全套/4新增审计/232最终全套的分阶段结果，全部冻结依赖与probe执行源副本未变，新audit源与测试单独SHA。准备提交时尚无正式任务生成或能力成绩；后续实际run须重新检查单卡资源，并沿冻结80表，不复用探针输出作为任务回答。
