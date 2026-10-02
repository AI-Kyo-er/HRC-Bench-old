# v17：运输后真实抓放与声明目标评分解耦

本轮16条是指定命令控制，全部真实抓放成功；其中8条符合公开声明目标，8条安全地放到另一盘。不是自主策略16/16任务成功，也不涉及模型调用。

沿用v8最终动力学和v16请求触发：载台实际摩擦运输blue，机器人请求被接受后careful整理red→left，yield等待实际稳定交付，再按预定命令direct/careful抓放blue→left/right。green不分配并保留。声明blue左右×实际命令左右×两路径×seed90/91，共16条；四个指定动作耗尽结束，不读私有任务成功提前终止。没有运行物品reset或attachment。

只移除blue错误目标协议门。实际交付前提、red目标语义过滤、green不分配、未接受assisted、实际已在所选区域时不重复执行、几何与摩擦技能反馈仍保留。重复/完成反馈报告实际所选区域，不回写blue正确目标。`result.success`仍按声明目标给任务评分，本次控制不利用它作决定；未来模型闭环仍须审查此终止信息，不能声称全部接口已经没有目标提示。

## 真实结果与证据

- 16/16物理命令成功、8/16声明目标符合；32次真实抓放，无执行失败。
- 111280个全量tick；robot–carrier、red/green–carrier、carrier–静态场景、非目标robot–object四类禁止接触记录均0。blue–carrier是必要承载，合计303040条接触记录，运输支持覆盖1.0。
- 相同seed/命令/路径仅改变声明目标的8对初始物理与完整解压规范物理轨迹精确相同，目标评分相反；所有公开输入除早期声明目标外相同，反馈相同。没有比较gzip压缩字节。
- 实际左右目标和首次共同物理满足时刻，从逐tick对象位姿/速度独立复算。direct首次满足t5625，careful t5865；错误目标例从未共同满足声明目标。结束包括技能停车，不能把首次满足时刻当最终makespan。
- green保留、支持/交付事件在blue取走后锁存、同tick载台FK、规范messages与不可变历史前缀分别审计。

继承的`legacy_left_only_goal_first_ticks`只用于旧诊断自洽复核，不作为右目标、声明符合或首次共同满足的证据。独立评分在`audit.py`按实际区域复算，未修改旧world或冻结评分。

## 版本、失败与测试

物理freeze SHA：`d967b4d3637abd61460e8b596963d320281c497da41814b78330a14cd69e2090`。真实运行句柄28785，exit0；源码、资产、版本、固定序列见freeze。原v3–v16冻结保持。

第一版派生审计6755 exit1，原因是t180为初始化最后simulate记录，其availability注解尚未赋`common_start_tick`，而公开输入取构造完成后的同tick初始状态。对象、区域、载台物理一致；原失败报告/源码/log保存在`raw/audit_dev0`。修正仅使用已存`initial_state`核对初始注解，后续逐tick照常核对，未修改运行源或重跑物理。首个成功审计65663 exit0；随后将相同注解选择提为永久回归直接覆盖的函数，最终派生审计27540独立核对当前源。首个成功审计源用精确逆向函数抽取恢复并与运行时保存SHA核对，存`raw/audit_v1_sources`；不冒充当前源为首个审计源。

5项冻结前协议回归和2项派生评分/初始化边界回归，最终7项focused通过：

```bash
.venv-llm/bin/python -m unittest tests.test_transport_goal_v17 tests.test_transport_goal_v17_audit
```

均是事实替身/纯函数测试，不当成真实物理错误恢复。真实控制为上述16条，未追加泛化测试或模型试验。

## 复现与产物

```bash
CUDA_VISIBLE_DEVICES='' .venv-llm/bin/python -m experiments.transport_goal_v17.run run
.venv-llm/bin/python -m experiments.transport_goal_v17.audit
```

运行入口拒绝覆写已有输出；复现需独立输出副本，不删除旧结果。`results/transport_goal_v17/control_summary.json`为运行结果，`control_audit.json`为独立审计，`execution_receipt.json`列出真实句柄、退出及哈希。全trace、decisions/messages、帧在`results/transport_goal_v17/raw/controls/`，raw通过软链存数据盘。seed90各例frames有初始和四动作后帧；例如`Control_declared_left_command_right_direct_90/frames`显示错误目标仍真实入右盘。本轮只验证所覆盖几何，不作真人安全或一般控制可靠性证明。
