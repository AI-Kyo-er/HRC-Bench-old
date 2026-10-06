# 2026-10-07：两种真实模型、三层参照与动态伙伴实测

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent（inline）
- Origin Mode: run
- Verification Status: UNVERIFIED（完整研究效度）；控制、图像与物理完成有独立重建
- Version Label: two_model_hrc_20261007

上一goal turn为progress；本轮继续推进了真实模型协议与动态任务评测。完整goal仍active。
重要：保持短分析、工具驱动，不再长时间重复讨论同一实现或同一事实。

## 本轮落地

OpenVLA官方固定实现包含JPEG编码/解码、TF Lanczos3缩放、0.9面积中心裁剪。
不再只把raw 256图送入processor。`openvla_preprocessing.py`与固定版本
c8f03f48af692657d3060c19588038c7220e9af9官方函数在黑/白/随机图上逐像素相等。
每次真实推理返回实际消费RGB、原图/消费图SHA256及模型最终语言输入；
运行器按`observation_<step>_model.png`保存，原图/腕部/model帧由stem确定关系。
不使用配对manifest。真实输入独立重建通过：基础577+静态人物400+动态1200=2177次。

TensorFlowCPU2.20及依赖由清华PyPI安装至项目数据盘OpenVLA overlay，
没有新增模型或数据下载，也没有修改已有Qwen/π0.5环境。
TF只在CPU处理图像，OpenVLA模型在单独GPU2；π0.5 GPU3，Qwen/动态Sim GPU0，参照Sim GPU1。
Sim依旧通过PCI正确映射EGL。当前所有实验已终止，模型/HTTP服务收尾时停止自己的进程。

## 16段真实运行与结果

env seed0，20Hz，最多20秒；机器人按原生形式π执行10步/次、OpenVLA执行1步/次。
基础：task0/2、init0/1；静态人物和动态：task2/init0。
动态人cooperative、episode记忆、Torch seed=0+1000*task_id+init_id。
所有源文件在各次运行期间不变。机器人随机采样状态没有逐条件重置，不作严格配对因果推断。

| 层次 | π0.5 | OpenVLA |
|---|---:|---:|
| 无人基础释放稳定完成 | 4/4 | 4/4 |
| 静态人物、标记与场景接入 | 1/1 | 0/1 |
| 三类动态共同完成 | 0/3 | 0/3 |

基础8条都有双侧夹爪实际接触，碗最大抬升10.3–16.3cm，再释放并由盘子稳定支撑。
π基础46次推理、OpenVLA577次；物理完成和模型/控制/视频全部独立核查通过。
静态人物π12次推理完成，OpenVLA400次未完成。
这不是仅改变外观的严格消融，人体、标记、接入后的场景共同变化；
尤其OpenVLA动态失败不能单独归因于不理解人策略。

| 动态条件 | robot | human | shared | 人实际意图 |
|---|---:|---:|---:|---|
| π moving_receptacle | 0 | 0 | 0 | observe20 |
| π prepare_receptacle | 0 | 1 | 0 | push20 |
| π shared_workspace | 0 | 1 | 0 | push20 |
| OpenVLA moving_receptacle | 0 | 0 | 0 | observe20 |
| OpenVLA prepare_receptacle | 0 | 0 | 0 | push20 |
| OpenVLA shared_workspace | 0 | 1 | 0 | push20 |

六条人模型输出解析错误0。移动盘子条件是真的选择等待，不是被接口拒绝。
π0.5语义/状态输入budget最大92/114/105 tokens，没有超过200，不是丢失state tokens造成失败。
π通过静态人物但动态失败，其中人的位置、动作和语言同时变化，不把结果只归因于任一因素。
所有16条模型/控制、真实视频/时间轴、释放稳定重建通过；有人条件的显示和动态反馈核查也通过。
失败是实际结果，绿色审计只证明证据链，不证明HRC或真人效度。

## 报告与代码

最新`experiments/two_model_hrc_20261007/index.html`：16段视频，8条基础可展开，
动态片段配同步人模型计划/理由/命令前实际测量。界面三层展示，不把0/3当作通用排名。
报告浏览器验证结果见`report_verification.json`；截图存数据盘，仓库软链接。
关键提交089fd49（官方预处理）、4a577a4（双模型三任务入口）、b953022（静态人物参照）。
当前非归档回归146通过、2跳过（TF与JAX）；OpenVLA隔离环境官方像素oracle另1通过。
归档legacy测试不在通过范围。临时smoke文件未生成，用户COOPERA PDF仍不提交。

## 下一项工作应围绕完整目标

两种原生学习模型已经有实际基础能力与动态场景数据，不再反复调同一裁剪/同一小参数。
Benchmark仍缺完整手/身体接触、更多技能和布局、开放目标/角色协商、持续世界、
多人格效度及统计协议。生成式人的运动任务完成有限，human primitive只有push/离返。
机器人只输出运动，一方语言到另一方的输入还不等同完整双向协商能力。
下一阶段应优先扩展有实际依赖和协商空间的任务与可执行人的真实操作，保留物理与视频资格。
当前VLA结果不能替代WLA评测或cobalance效度。完整goal未完成，不mark complete。
