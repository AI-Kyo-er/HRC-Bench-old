# 机器人 Benchmark HRI Ideas Copair 延申 Coground

**User:** Anonymous  
**Created:** 9/30/2026 16:06:26  
**Updated:** 10/3/2026 17:38:17  
**Exported:** 10/3/2026 17:39:01  
**Link:** [https://chatgpt.com/g/g-p-6abb77c21e848191ab6b98f51a4c5bb2-hrc-bench/c/6abcc302-32b0-83ec-98b9-bea72e321f64](https://chatgpt.com/g/g-p-6abb77c21e848191ab6b98f51a4c5bb2-hrc-bench/c/6abcc302-32b0-83ec-98b9-bea72e321f64)  

## Prompt:
9/29/2026, 2:37:10 PM

我现在已经有的关于一个基本的具身benchmark的研究现状以及 HRI 的研究在其中的大致的位置，但是，我目前只想要机器人的 benchmark 研究，你来帮我调研一下以及现在的 HRI 是什么样的研究进展呢，有什么样的研究谱系呢。

[Attachment: HRI研究谱系与具身智能Benchmark定位.md]

## Response:
9/29/2026, 2:37:11 PM · gpt-5-6-thinking

我会把你现有材料里的 **“HRI 在具身 Benchmark 中的位置”** 保留下来，但这次把主线改成 **“机器人 Benchmark 本身是怎么发展起来的，以及 HRI 在这条主线里走到了哪一步”**。我会重点区分：任务级 Benchmark、通用机器人能力 Benchmark、真实机器人评测、VLA/基础模型评测，以及真正闭环的人机交互 Benchmark。

目前看到一个很清楚的变化：机器人 Benchmark 的研究重心已经从“**给算法一组固定任务，比较成功率**”，转向“**这个 Benchmark 到底能不能代表通用机器人能力**”。尤其 2026 年已经出现专门“审计 Benchmark 本身”的工作，说明领域开始从刷榜进入第二阶段：检验任务捷径、统计显著性、过拟合和数据来源依赖。

> **明确调研范围**
>
> 我会聚焦机器人 benchmark，并把 HRI 作为其中的人机协作与交互评测分支来梳理。接下来我将追踪代表性基准、评价维度、技术演进，以及当前研究谱系。
>
> **明确了调研范围**
>
> 
>
> **已搜索 48 个网站**
>
> 
>
> **拓展研究框架**
>
> 我会以你现有材料为基础，补充近年的机器人 benchmark 与 HRI 进展，重点梳理任务基准、真实机器人评测、基础模型评测，以及 HRI 的历史谱系和当前前沿。
>
> **组织研究谱系**
>
> 我会把机器人 benchmark 按“任务能力、泛化能力、真实部署、交互质量”四条轴整理，而不是简单罗列数据集；HRI 则作为“以人为评价对象”的交互分支嵌入其中。
>
> **拓展研究框架并组织研究谱系**
>
> 
>
> **已搜索 14 个网站**
>
> 
>
> 思考了 1m 37s

可以。基于你现在这份材料，我觉得下一步不应该再把“具身智能 Benchmark”整体铺开，而应该把范围严格收缩成：

> **Robot Benchmark / Robot Learning Benchmark：真正评测机器人策略、控制与具身任务执行能力的 Benchmark。**

也就是说，我会把纯 VLM、纯视觉感知、纯 VLN、纯语言规划 benchmark 暂时排除；只有当它们最终进入机器人闭环控制，或者直接影响机器人行动评价时才纳入。这样会比你现在的材料更聚焦。

你现有稿件其实已经抓到一个重要现象：当前主流机器人/VLA benchmark 仍主要评价抓取、语言条件操作、长程任务、泛化等机器人侧能力，而人的意图变化、同步、干预、控制权、人侧成本等还没有成为同等级的评价轴。`HRI研究谱系与具身智能Benchmark定位.md` 我这次进一步查下来，这个判断是成立的，但可以把它放进一个更完整的 **机器人 Benchmark 发展谱系** 里。

---

# 一、我建议你先建立这样一条“机器人 Benchmark 研究谱系”

如果从 Benchmark 的研究问题，而不是按“导航/操作/人机交互”这些应用任务来分，我认为机器人 Benchmark 大致经历了 **6 个阶段**：

| 阶段 | Benchmark 在问什么 | 代表性工作 |
|---|---|---|
| ① 标准化测量 | 这个机器人到底有多强？不同实验室能否直接比较？ | NIST、YCB、RoboCup@Home |
| ② 标准任务集 | 一个算法能否在统一机器人任务上学习？ | Meta-World、RLBench、robosuite/robomimic |
| ③ 泛化与组合 | 能否跨任务、跨物体、长时程执行？ | CALVIN、ManiSkill2、LIBERO |
| ④ 通用机器人能力 | 能否覆盖真实日常活动和复杂场景？ | BEHAVIOR-1K、RoboCasa、RoboTwin、VLABench |
| ⑤ Foundation/VLA 评价 | 一个通用 VLA 到底掌握了什么能力？ | SIMPLER、VLABench、RoboTwin 2.0、VLA-Arena |
| ⑥ Benchmark validity | 分数真的代表机器人能力吗？能否迁移到真机？ | SIMPLER、Real-robot benchmark、2026 Benchmark Audit |
| **正在出现的第⑦层** | **机器人能不能和人一起工作，而且真正帮助人？** | Habitat 3.0、PARTNR、M4Bench、HRIBench |

这比简单写成“操作 Benchmark → VLA Benchmark → HRI Benchmark”要有解释力得多。

---

## 1. 第一代：机器人性能标准化

这是很多现在做 Embodied AI 的论文容易忽略的历史。

早期 robotics benchmark 的出发点并不是“训练神经网络”，而是：

> **怎样让两个实验室声称的机器人性能具有可比性？**

NIST 很早就在建立机器人 mobility、manipulation、sensing、communication、human-system interaction、安全等标准测试方法，强调的是**可重复的装置、协议、指标和能力分解**。([NIST](https://www.nist.gov/publications/comprehensive-standard-test-suites-performance-evaluation-mobile-robots?utm_source=chatgpt.com))

2015 年的 **YCB Object and Model Set** 则是 manipulation benchmark 史上一个很关键的节点：不仅把日常物体标准化，还明确提出必须同时标准化实验 protocol 和定量评价方法。([卡内基梅隆大学机器人研究所出版物](https://publications.ri.cmu.edu/the-ycb-object-and-model-set-towards-common-benchmarks-for-manipulation-research?utm_source=chatgpt.com))

**RoboCup@Home** 则代表另外一种路线：不是固定一个静态数据集，而是通过逐年演化的真实服务机器人比赛持续改变 Benchmark，使导航、识别、操作、HRI、系统集成一起接受测试。([科学直达](https://www.sciencedirect.com/science/article/pii/S0004370215001174?utm_source=chatgpt.com))

所以这一时期的关键词是：

> **measurement → repeatability → protocol → system capability**

这其实是你未来做 Benchmark 时非常值得重新吸收的传统。

---

# 二、第二代：Robot Learning Benchmark 出现

深度强化学习、模仿学习兴起以后，问题发生了变化：

> 不再主要比较“哪台机器人硬件性能好”，而是比较“哪个学习算法学得好”。

于是 Benchmark 开始转向标准化 simulator + task suite。

### Meta-World

Meta-World 2019 用 50 个 manipulation task 去测试 multi-task learning 和 meta-RL，并明确设计 train/test task separation，让“泛化到没见过的任务”成为 Benchmark 的核心问题。([Meta-World](https://meta-world.github.io/?utm_source=chatgpt.com))

### RLBench

RLBench 2019 把规模扩展到 100 个视觉操作任务，同时给 RGB、depth、segmentation、proprioception 和 motion-planner demonstrations，目标就是统一评价 RL、IL、few-shot 和 multi-task robot learning。([arXiv](https://arxiv.org/abs/1909.12271?utm_source=chatgpt.com))

这一阶段形成了后来大量 robot benchmark 的基本模板：

$$
\text{Environment}
+
\text{Task Distribution}
+
\text{Observation}
+
\text{Action Space}
+
\text{Success Metric}.
$$

但人的角色几乎为零。

---

# 三、第三代：从“能做任务”进入“泛化、语言、长时程”

2021-2023 左右，Benchmark 开始觉得：

> 单个 pick-and-place 成功率已经不能代表通用机器人能力。

于是出现几个重要分叉。

### CALVIN：长时程 + language-conditioned

CALVIN 把重点从单技能成功率推向**由语言组合多个技能**，并且测试 novel language、novel environments 和 objects。([arXiv](https://arxiv.org/abs/2112.03227?utm_source=chatgpt.com))

### ManiSkill2：物体和 embodiment 泛化

ManiSkill2 把 object-level geometry/topology variation、单臂/双臂、mobile base、soft body 等放入统一协议，试图解决以前任务过于固定的问题。([arXiv](https://arxiv.org/abs/2302.04659?utm_source=chatgpt.com))

### LIBERO：知识迁移

LIBERO 更明确提出：

> Benchmark 不只是测“成功”，而应该测 robot learning 中的 **knowledge transfer**。

其 130 个任务被用来区分 spatial、object、goal、procedural 等知识迁移。([arXiv](https://arxiv.org/abs/2306.03310?utm_source=chatgpt.com))

所以 Benchmark 的问题变成：

$$
\text{Can it act?}
\rightarrow
\text{Can it generalize?}
\rightarrow
\text{Can it compose?}
$$

---

# 四、第四代：Generalist Robot Benchmark

这是 2023-2025 非常明显的一次转变。

Benchmark 的理想不再只是：

> “给我 50 个桌面 manipulation tasks。”

而开始变成：

> **真正的通用机器人应该会做哪些事情？**

其中我认为两个方向尤其关键。

## BEHAVIOR-1K：从“机器人方便测什么”变成“人需要机器人做什么”

BEHAVIOR-1K 的 1000 个活动不是研究者随便设计的，而是通过调查：

> “What do you want robots to do for you?”

来决定任务空间。

然后才去构造 50 个场景和大规模可交互物体。([arXiv](https://arxiv.org/abs/2403.09227?utm_source=chatgpt.com))

这是一种非常重要的变化：

$$
\text{algorithm-grounded benchmark}
\rightarrow
\text{task-grounded benchmark}
\rightarrow
\boxed{\text{human-grounded benchmark}}
$$

但我要特别强调：

> **Human-grounded ≠ HRI。**

BEHAVIOR-1K 的任务来源于人的需求，但标准 evaluation 中人并不一定在闭环交互。

这与你原稿里提出的 Human-grounded / Human-present / Human-interactive / Human-beneficial 四分法正好可以接起来。`HRI研究谱系与具身智能Benchmark定位.md`

---

## RoboCasa：场景与数据规模化

RoboCasa 则代表另一个趋势：通过大量厨房场景、对象和自动数据生成，使 Benchmark 本身成为一个 **data engine + task engine**。

它设计了 100 类评测任务，并通过生成方法扩展场景和轨迹。([arXiv](https://arxiv.org/abs/2406.02523?utm_source=chatgpt.com))

这里 Benchmark 已经开始从：

> 固定 test set

变成：

> **可生成的 task distribution**。

这个变化非常重要。

---

# 五、2024-2026：VLA 让 Benchmark 再次改变

VLA 出现以后，传统 Benchmark 又遇到了一个问题：

> LIBERO / CALVIN 高分，究竟说明模型会机器人操作，还是只是记住了一些视觉和任务捷径？

于是新的 Benchmark 开始刻意加入：

- language reasoning；
- world knowledge；
- distractor；
- distribution shift；
- safety；
- long horizon；
- cross-embodiment；
- sim-to-real。

例如 **VLABench** 包含 100 类语言条件机器人操作任务、2000+ objects，强调 world knowledge、implicit intention 和 long-horizon reasoning。([CVF Open Access](https://openaccess.thecvf.com/content/ICCV2025/html/Zhang_VLABench_A_Large-Scale_Benchmark_for_Language-Conditioned_Robotics_Manipulation_with_Long-Horizon_ICCV_2025_paper.html?utm_source=chatgpt.com))

**RoboTwin 2.0** 则试图用强 domain randomization 和自动数据生成测试 robust bimanual manipulation。([arXiv](https://arxiv.org/abs/2506.18088?utm_source=chatgpt.com))

2026 年 **VLA-Arena** 又进一步把 170 个任务明确划成 Safety、Distractor、Extrapolation 和 Long Horizon 等难度轴。([VLA-Arena](https://vla-arena.github.io/?utm_source=chatgpt.com))

这意味着机器人 Benchmark 正从：

$$
\text{task list}
$$

逐渐变成：

$$
\boxed{
\text{capability decomposition}
\times
\text{controlled distribution shift}
}
$$

---

# 六、而当前机器人 Benchmark 最大的问题，其实已经变成“Benchmark 自己可靠吗？”

这是我认为你现在的申请书/研究论述里**非常值得加入的一段**。

2026 年出现了一篇很有代表性的工作：

**What Are We Actually Benchmarking in Robot Manipulation?**

它不是再造一个 Benchmark，而是反过来审计 LIBERO、CALVIN、SIMPLER、RoboCasa、RoboTwin 2.0。

作者提出四种 Benchmark failure：

1. **shortcut solvability**：任务有没有捷径；
2. **statistical significance**：几次 rollout 的差别是否真的显著；
3. **creeping overfitting**：社区是不是已经逐渐对 test protocol 过拟合；
4. **data-source dependence**：结果是否过度依赖数据来源。

甚至发现 LIBERO 上，一个 **没有语言 encoder 的 0.09B probe** 都能达到接近已有 SOTA 的结果。([arXiv](https://arxiv.org/abs/2606.04233?utm_source=chatgpt.com))

这个信号非常重要：

> **2026 年机器人 Benchmark 研究已经不只是“谁的任务更多”，而开始进入“测量有效性 validity”阶段。**

这实际上重新接回了最早 NIST/YCB 的 measurement science 传统。

---

# 七、Sim-to-real 和真机 Benchmark 是另一条正在快速成长的线

传统机器人 Benchmark 最大的问题一直是：

> 仿真可重复，但不真实；  
> 真机真实，但不可重复。

**SIMPLER** 的思路很有代表性：不是要求 simulation 完全复制现实，而是要求 simulation evaluation 的**模型排名和行为模式能够预测 real-world evaluation**。([机器人操控政策评估模拟](https://simpler-env.github.io/?utm_source=chatgpt.com))

2026 年又开始出现更多真正针对 VLA 的 physical benchmark。

例如 PhAIL 明确批评真实机器人论文常见的：

- 每条件只有很少 rollout；
- binary success；
- 不报告置信区间；
- 难以分辨两个接近模型。

它转而使用 time-to-success distribution、human-relative throughput 和显著性检验。([arXiv](https://arxiv.org/abs/2605.29710?utm_source=chatgpt.com))

所以这里又出现了一个值得你抓住的趋势：

$$
\text{Success Rate}
\rightarrow
\text{Distributional Evaluation}
\rightarrow
\text{Statistically Reliable Evaluation}.
$$

我认为这是未来 robot benchmark 非常重要的一条线。

---

# 八、那么 HRI 到底处在这条机器人 Benchmark 谱系的什么地方？

这是我这次调研以后觉得最值得重新定义的一点：

## **HRI 不应该被看成和 Manipulation、Navigation 并列的“任务类别”。**

更准确地说，它正在成为一个 **orthogonal evaluation axis（正交评价维度）**。

例如同一个“整理厨房”：

- robot 自己完成 → manipulation benchmark；
- human 给一句命令，robot 完成 → language-conditioned benchmark；
- human 和 robot 分工完成 → HRC benchmark；
- human 中途改变计划 → interactive HRI benchmark；
- robot 主动向人澄清 → communication benchmark；
- robot 让人反而花更多时间 → 从 human-benefit 看其实是失败。

所以：

$$
\boxed{
\text{HRI is not a task family;
it is a property of the interaction loop.}
}
$$

我觉得这个观点甚至可以成为你这部分综述的组织原则。

---

# 九、HRI 本身的研究谱系，我建议不要再按“导航/语言/协作”简单排列

你目前文件中的谱系本身已经很完整，包括社会感知、导航、行为可理解性、语言、协作、共享自主、照护、pHRI 等。`HRI研究谱系与具身智能Benchmark定位.md`

但如果你的最终目标是 **机器人 Benchmark**，我建议把它重新压缩成五条真正影响 Benchmark 设计的谱系。

---

## 谱系 A：Human Factors / HRI Measurement

这是最老的一条。

核心问题从来不是：

> robot 成功了吗？

而是：

> **human + robot 这个系统表现得怎么样？**

包括：

- workload；
- trust；
- usability；
- predictability；
- fluency；
- comfort；
- acceptance；
- sense of agency。

这条线目前理论和实验方法很成熟。

2026 年甚至已经出现专门整理 HRI measurement scales 的数据库工作，说明 HRI 社区在人侧评价方面其实有非常丰富的积累。([Frontiers](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2026.1846413/full?utm_source=chatgpt.com))

真正缺的不是指标，而是：

> **怎样把这些指标接入 scalable robot benchmark。**

---

# 十、谱系 B：Human-aware → Socially Interactive Robot

这一条从 social perception、social navigation、legibility 慢慢发展。

最早：

> 不要撞人。

然后：

> 保持合理距离。

再然后：

> 预测人的运动。

进一步：

> 理解人的目标。

现在则已经开始：

> **主动和人沟通以获取完成任务的信息。**

例如 2026 年 CommNav 已经把 Habitat 3.0 扩展成 communication-enabled social navigation：机器人不是只在人群里走，而是主动向人询问目标人物在哪里。([arXiv](https://arxiv.org/abs/2607.01044?utm_source=chatgpt.com))

这其实是一个非常清晰的升级：

$$
\text{collision avoidance}
\rightarrow
\text{human-aware navigation}
\rightarrow
\text{social navigation}
\rightarrow
\boxed{\text{interactive navigation}}.
$$

2025 年的 social navigation benchmark/review 也显示，该方向已经有比较成熟的 simulator 和指标体系，但 realistic human behavior 和真实世界 evaluation 仍然是瓶颈。([Frontiers](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2025.1658643/full?utm_source=chatgpt.com))

---

# 十一、谱系 C：Shared Autonomy / Human Control

这是另一个非常独立的 HRI 传统。

它不追求：

> robot autonomy 越高越好。

而是问：

> **人到底应该控制什么？机器人应该帮多少？什么时候接管？**

这和今天很多“全自主 VLA”思路其实很不一样。

例如 2025 HRI 的研究发现，提高机器人自主程度虽然可能改善任务表现，却可能降低人的 **sense of agency**。([DOI](https://doi.org/10.1109/HRI61500.2025.10974147?utm_source=chatgpt.com))

所以：

$$
\text{Task success} \uparrow
$$

不一定意味着：

$$
\text{HRI quality} \uparrow.
$$

这对机器人 Benchmark 是一个很深刻的问题。

---

# 十二、谱系 D：Human-Robot Collaboration / Teaming

这是目前和 Embodied AI / VLA 汇合得最快的一支。

演进大概是：

$$
\text{handover}
\rightarrow
\text{共同搬运}
\rightarrow
\text{任务分工}
\rightarrow
\text{长期家庭协作}
\rightarrow
\text{动态角色与干预}.
$$

几个节点特别重要。

### Human-Robot Gym

提供 8 个 HRC task，并且把显式 safety shield 放进 Benchmark。([arXiv](https://arxiv.org/abs/2310.06208?utm_source=chatgpt.com))

### Habitat 3.0

这是一个非常关键的节点，因为它同时提供：

- humanoid；
- robot；
- human-in-the-loop interface；
- Social Navigation；
- Social Rearrangement。

而且它尝试验证 automated humanoid evaluation 能否预测真人 collaborator 对不同 robot policy 的相对评价。([arXiv](https://arxiv.org/abs/2310.13724?utm_source=chatgpt.com))

### PARTNR

又向前走一步，把规模扩大到 **100,000 个自然语言协作任务、60 个房屋、5,819 个对象**，并明确引入 human-human 和 human-robot comparison。

最有意思的结果是，当人和 LLM agent 合作时，所需步骤是两个人协作的大约 1.5 倍，甚至比一个人单独完成还多约 1.1 倍。([arXiv](https://arxiv.org/abs/2411.00081?utm_source=chatgpt.com))

这实际上第一次非常直接地问：

> **robot 到底是在帮助人，还是给人添麻烦？**

---

# 十三、谱系 E：Foundation Model HRI

这是 2024-2026 真正的新变化。

LLM/VLM/VLA 进入 HRI 后，研究焦点正在从传统 pipeline：

$$
\text{perception}
\rightarrow
\text{intent recognition}
\rightarrow
\text{planner}
\rightarrow
\text{controller}
$$

转向一个统一 foundation model 参与：

$$
\text{sense}
\leftrightarrow
\text{reason}
\leftrightarrow
\text{communicate}
\leftrightarrow
\text{act}.
$$

2026 CHI 的系统综述分析了 86 篇 LLM-driven HRI 工作，把新趋势概括成 **Sense-Interaction-Alignment**，同时指出当前实验设置和评价指标仍然高度碎片化。([arXiv](https://arxiv.org/abs/2602.15063?utm_source=chatgpt.com))

而在工业 HRC 中，2026 的综述也发现 LLM/VLM 已经明显进入 perception、reasoning、task planning 和 natural-language interaction，但 VLA 真正在 HRC 中应用仍然是早期阶段。([DOI](https://doi.org/10.1016/j.rcim.2026.103269?utm_source=chatgpt.com))

---

# 十四、这里尤其值得注意两个“HRIBench”

现在其实有两个名字相同、但意义完全不同的 HRIBench。

### 2025 HRIBench：Human Perception

它主要是 **VLM Benchmark**：

- non-verbal cues；
- verbal instruction；
- human-robot-object relation；
- social navigation；
- person identification；
- 共 1000 个 VQA questions。

研究发现当前 VLM 在 accuracy 和 real-time latency 间仍存在明显矛盾。([arXiv](https://arxiv.org/abs/2506.20566?utm_source=chatgpt.com))

它本质还是：

$$
\text{Can the model understand the human?}
$$

不是完整 closed-loop HRI。

---

## 2026 HRIBench：Interaction-Centric HRC

这个我认为对你的研究特别重要。

它开始直接测试：

- **Instructor**
- **Collaborator**
- **Intruder**

三种人类角色，并把任务描述成有角色、时序、协调约束的 executable scenarios。

有 13 类任务、650+ evaluation episodes，评价也不再只是 success，而包括：

- synchronization；
- responsiveness；
- protocol compliance；
- safety。

并测试了 GR00T、π0.5、ACT 等机器人策略。

结果显示，即使这些模型具有较强 manipulation 能力，在 human intervention、temporal coordination 和 intent-aware interaction 上仍有明显问题。([Anonymous View](https://rt.http3.lol/index.php?q=aHR0cHM6Ly9hcnhpdi5vcmcvYWJzLzI2MDcuMTMwNTY&utm_source=chatgpt.com))

这个节点我认为非常重要，因为它表示：

$$
\boxed{
\text{Object-centric Robot Benchmark}
\rightarrow
\text{Interaction-centric Robot Benchmark}
}
$$

已经真正开始出现。

---

# 十五、所以截至 2026 年，我会这样评价 HRI Benchmark 的成熟度

| HRI 方向 | 学术研究成熟度 | Benchmark 成熟度 |
|---|---:|---:|
| Human perception | 高 | ★★★★☆ |
| Social navigation | 高 | ★★★★☆ |
| Robot intent / legibility | 高 | ★★☆☆☆ |
| Language interaction | 高 | ★★★☆☆ |
| Handover / local physical collaboration | 高 | ★★★☆☆ |
| Long-horizon human-robot collaboration | 中高 | ★★★☆☆ |
| Shared autonomy | 高 | ★★☆☆☆ |
| Interaction with foundation robot models | 快速增长 | ★★☆☆☆ |
| Human workload / agency / trust | 高 | ★★☆☆☆ |
| Human physical benefit / ergonomics | 中高 | ★★☆☆☆ |
| Long-term human benefit | 高度场景化 | ★☆☆☆☆ |

注意这里的 ★ **不是论文质量排名**，而是我用来表示“标准化、可规模化机器人 Benchmark 协议的成熟程度”。

一个非常有意思的事实是：

> **HRI 研究最成熟的地方，往往反而最难 Benchmark 化。**

例如 trust、长期照护、agency、身体负荷都有几十年的研究，但不容易变成 10,000 episodes 自动跑完的 leaderboard。

---

# 十六、因此，现在 Robot Benchmark 和 HRI 真正的断层在哪里

我现在会把问题凝练成下面这一张图：

```text
传统机器人 Benchmark
        │
        ├── perception
        ├── navigation
        ├── manipulation
        ├── language grounding
        └── planning
              │
              ▼
        Generalist / VLA
              │
       ┌──────┴────────┐
       │               │
 Robot Capability   Human Interaction
       │               │
成功率             理解人的意图
泛化               被人理解
长时程             双向适应
OOD                协调和同步
安全               人的干预
跨本体             工作量/控制感
       │               │
       └──────┬────────┘
              ▼
       下一代 Robot Benchmark
```

真正没有解决的是中间这一步：

$$
\boxed{
\text{General Robot Capability}
+
\text{Interaction Capability}
+
\text{Human Outcome}
}
$$

怎么放进**同一个、可重复、可规模化的 Benchmark protocol**。

这和你原材料最后得到的结论其实是一致的：问题并不是 HRI 社区没研究“人”，而是 HRI 的人因证据与现代大规模具身 Benchmark 的评价逻辑没有真正接起来。`HRI研究谱系与具身智能Benchmark定位.md`

---

# 十七、如果你的研究最终准备做一个新的 Robot Benchmark，我认为最有价值的定位不是“再做一个 HRI Benchmark”

更强的研究问题应该是：

> **现有 Robot Benchmark 主要将 generalization 定义为跨物体、跨场景、跨任务和跨 embodiment；我们进一步提出，面向真实部署的 general-purpose robot 还必须实现跨人的泛化（human generalization）以及交互闭环中的可靠性。**

也就是说，把现在常见的：

$$
G =
G_{\text{object}}
+
G_{\text{scene}}
+
G_{\text{task}}
+
G_{\text{embodiment}}
$$

扩展为：

$$
\boxed{
G =
G_{\text{object}}
+
G_{\text{scene}}
+
G_{\text{task}}
+
G_{\text{embodiment}}
+
G_{\text{human}}
+
G_{\text{interaction}}
}
$$

这里的 **human generalization** 可以系统地测试：

- unseen human；
- unseen motion style；
- unseen instruction style；
- unseen cooperation strategy；
- fast / slow collaborator；
- mistaken human；
- interfering human；
- changing intent；
- different skill levels。

而 **interaction robustness** 则测试：

- interruption；
- correction；
- clarification；
- handover；
- temporal synchronization；
- role changes；
- control transfer；
- safe refusal；
- error recovery。

这样你的工作就不是：

> “我也做了一套有人出现的任务。”

而是：

> **把“人”正式提升为机器人泛化和可靠性测试中的一个 distribution dimension。**

我认为这个定位比单纯说“现有 Benchmark 不关注 HRI”强很多。

---

## 我现在对整个领域最简洁的判断

**第一阶段**的 Robot Benchmark 在解决“可比较”；

**第二阶段**解决“学习能力”；

**第三阶段**解决“泛化与组合”；

**第四阶段**解决“通用任务规模”；

**第五阶段**解决“Foundation/VLA 通用能力”；

**现在开始进入第六阶段：Benchmark 自身是否有效，以及机器人能力能否在真实世界、真人和交互扰动下保持成立。**

HRI 正好处在这个阶段的核心位置。

所以我甚至会把你的研究主线从原来的：

> **“具身智能 Benchmark 中缺少 HRI。”**

升级为：

> **“当前机器人 Benchmark 已经从任务覆盖走向通用能力评测，但其 generalization paradigm 仍主要围绕对象、环境、任务和 embodiment 展开，人的行为分布及双向交互过程尚未被系统纳入。因此，下一代 Robot Benchmark 需要从 object/task-centric evaluation 进一步发展为 interaction-centric evaluation，并把 human generalization、coordination robustness 和 human-side outcome 纳入统一评测体系。”**

这个版本，我认为已经可以直接作为你项目申请书里“国内外研究现状 → 当前不足 → 我们为什么要做这个 Benchmark”的核心逻辑了。

---

**Sources:**

- [Comprehensive Standard Test Suites for the Performance Evaluation of Mobile Robots | NIST](https://www.nist.gov/publications/comprehensive-standard-test-suites-performance-evaluation-mobile-robots?utm_source=chatgpt.com)
- [The YCB Object and Model Set: Towards Common Benchmarks for Manipulation Research - Robotics Institute Carnegie Mellon University](https://publications.ri.cmu.edu/the-ycb-object-and-model-set-towards-common-benchmarks-for-manipulation-research?utm_source=chatgpt.com)
- [RoboCup@Home: Analysis and results of evolving competitions for domestic and service robots - ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0004370215001174?utm_source=chatgpt.com)
- [Meta-World](https://meta-world.github.io/?utm_source=chatgpt.com)
- [RLBench: The Robot Learning Benchmark & Learning Environment](https://arxiv.org/abs/1909.12271?utm_source=chatgpt.com)
- [ICCV 2025 Open Access Repository](https://openaccess.thecvf.com/content/ICCV2025/html/Zhang_VLABench_A_Large-Scale_Benchmark_for_Language-Conditioned_Robotics_Manipulation_with_Long-Horizon_ICCV_2025_paper.html?utm_source=chatgpt.com)
- [VLA-Arena - VLA Benchmark and Leaderboard](https://vla-arena.github.io/?utm_source=chatgpt.com)
- [Evaluating Real-World Robot Manipulation Policies in Simulation](https://simpler-env.github.io/?utm_source=chatgpt.com)
- [Frontiers | The human-robot interaction scale database](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2026.1846413/full?utm_source=chatgpt.com)
- [The Sense of Agency in Assistive Robotics Using Shared Autonomy](https://doi.org/10.1109/HRI61500.2025.10974147?utm_source=chatgpt.com)
- [[2607.13056] HRIBench: Benchmarking Interaction-Centric Human-Robot Collaboration](https://rt.http3.lol/index.php?q=aHR0cHM6Ly9hcnhpdi5vcmcvYWJzLzI2MDcuMTMwNTY&utm_source=chatgpt.com)

## Prompt:
9/29/2026, 7:51:32 PM

现在的 具身时代的机器人的 HRI Bench 的研究，能够从传统人机交互理论中可以借鉴过来，作为 Benchmark 设计核心的理念迁移。

## Response:
9/29/2026, 7:51:44 PM · gpt-5-6-thinking

可以，而且我觉得这恰恰是现在 HRI Benchmark 最值得做的方向：不是把传统 HRI 的“量表”简单搬过来，而是把其中对**交互本质的定义**迁移成可自动化、可规模化的 Benchmark 设计原则。下面我会按“传统理论 → 具身 Benchmark 中如何重写 → 可测什么”来梳理。

一个关键点是：**传统 HRI 理论里最值得迁移的，不是 Godspeed、NASA-TLX 这些“现成量表”，而是它们背后的评价对象。**  
例如传统 HRI 说“协作流畅性”，在 Benchmark 里就应被改写成：机器人是否能在**时序变化、角色变化、人类干预**下仍保持协调，而不是最后有没有把杯子放对。

> **梳理理论迁移**
>
> 我正在把传统 HRI 理论转译为具身机器人 Benchmark 的可测原则：共同心智模型、联合行动流畅性、信任校准、可解释性、共享自主、互适应、空间规范与安全，并进一步对应任务、指标和场景。
>
> **梳理了理论迁移思路**
>
> 
>
> **构建基准框架**
>
> 我会迁移理论构念，而非直接照搬传统量表：将流畅性、共同心智模型、可理解性、信任校准、能动性、互适应与混合主动权，转化为受控扰动、行为轨迹、主客观指标和反事实对照。
>
> **构建了基准框架**
>
> 
>
> **已搜索 16 个网站**
>
> 
>
> **扩展迁移原则**
>
> 我会把基准核心组织成四层：理论构念、可控交互扰动、过程轨迹指标、人类结果验证。重点评估人机协同过程，而不只是机器人完成率，并覆盖共同建模、意图可理解性、信任校准、共享自主、互适应、空间协调与安全恢复。
>
> **扩展了迁移原则**
>
> 
>
> **已搜索 8 个网站**
>
> 
>
> 思考了 1m 16s

可以，而且我认为这应该成为你现在这个方向里非常关键的一层理论贡献：

> **不是“为具身机器人重新发明一套 HRI Benchmark”，而是把传统 HRI / Human Factors 中已经研究了几十年的核心交互理论，重新操作化（operationalize）为适用于 VLA、具身基础模型和大规模仿真的 Benchmark 机制。**

你现有材料里提出的 **Human-grounded / Human-present / Human-interactive / Human-beneficial** 四层区分，本身就很适合做最外层框架。`HRI研究谱系与具身智能Benchmark定位.md`  
在这个框架内部，我认为至少有 **7 个传统 HRI 理论概念特别值得迁移**。

---

# 一、最重要的变化：不要迁移“量表”，要迁移“评价对象”

传统 HRI 的很多成果今天看起来像：

- trust 问卷；
- workload 问卷；
- fluency 量表；
- user preference；
- legibility 用户实验。

如果只是把这些量表塞进机器人 Benchmark，价值其实有限。

真正应该迁移的是：

$$
\boxed{
\text{HRI theoretical construct}
\rightarrow
\text{controlled interaction condition}
\rightarrow
\text{observable behavior trace}
\rightarrow
\text{benchmark metric}
}
$$

例如：

> 传统 HRI：这个机器人和人“协作流畅吗？”

不要直接变成一个 1-7 分问卷。

而应该变成：

> 当人的速度变化、任务顺序变化、角色发生冲突时，机器人能不能及时调整自己的动作，使人不必等待、不需要重复指令，并保持合理的并行工作？

然后把它自动化测成：

$$
T_{\text{human idle}},
T_{\text{robot idle}},
T_{\text{functional delay}},
T_{\text{concurrent activity}}.
$$

这就是一个很典型的 **理论 → Benchmark 机制迁移**。

Hoffman 对 human-robot fluency 的经典研究本来就提出了 Human Idle Time、Robot Idle Time、Concurrent Activity、Functional Delay 等客观过程指标；这比单纯的最终任务成功率更接近“团队协作质量”。([MIT CSAIL](https://people.csail.mit.edu/boerkoel/hrc2013/hrc2013hoffman?utm_source=chatgpt.com))

---

# 二、我认为最值得迁移的 7 个传统理念

| 传统 HRI / Human Factors 概念 | 原来研究的问题 | 在具身 Benchmark 中应该迁移成什么 | 可以设计的指标 |
|---|---|---|---|
| **1. Team Fluency / Joint Action** | 人和机器人是否像一个协调团队 | 从 final success 转为 interaction trajectory | human idle、robot idle、functional delay、并行率、等待时间 |
| **2. Common Ground / Shared Mental Model** | 双方是否知道彼此知道什么、准备做什么 | 主动制造信息不对称和理解偏差 | 澄清次数、错误恢复时间、belief alignment、重复劳动 |
| **3. Legibility / Predictability** | 人能不能理解机器人动作 | 机器人的计划是否可以从部分轨迹中被提前推断 | early intent inference、误导率、预测准确率 |
| **4. Mixed Initiative / Shared Autonomy** | 谁应该在什么时候控制系统 | 动态控制权、主动求助、接受纠正 | unnecessary takeover、missed intervention、handoff latency、human input cost |
| **5. Trust Calibration / Appropriate Reliance** | 人是否“恰当地”信任自动化 | 在不同可靠性条件下测试 reliance 是否匹配真实能力 | over-reliance、under-reliance、calibration error |
| **6. Mutual Adaptation** | 人和机器人是否相互适应 | 把“人”变成一个 test distribution | adaptation rate、partner-switch performance、unseen-human generalization |
| **7. Human Workload / Agency / Benefit** | 机器人是否真正帮助了人 | 从 robot success 转向 human outcome | human effort、wait time、interventions、workload、agency、ergonomic cost |

这里面我尤其推荐你把 **1、2、4、6** 当作 interaction-centric benchmark 的主体，把 **3、5、7** 当作更高层的人因评价轴。

---

# 三、第一条迁移：从 Task Efficiency 变成 Team Fluency

这是最容易真正 Benchmark 化的一条。

传统机器人 Benchmark 会说：

$$
Success = 1
$$

因为最终桌子整理好了。

但 HRI 理论会问：

> 是怎么整理好的？

假设两个机器人 policy：

### Policy A

机器人做得很快，但不断堵住人，人一直在等待。

### Policy B

机器人自己的动作稍微慢一点，但它会观察人的动作，在合适时机让路，同时做另一个子任务。

两者可能都是：

$$
SR =100\%
$$

但从 HRI 看，显然后者可能形成更流畅的团队过程。

Hoffman 对 collaborative fluency 的定义，本质上就是**联合活动在时间上的协调嵌合**；对应的客观指标包括 human idle time、robot idle time、concurrent activity 和 functional delay。([探索 IEEE](https://xplorestaging.ieee.org/document/8678448?utm_source=chatgpt.com))

因此你完全可以把今天具身 Benchmark 的 episode 从：

$$
(s_0,a_0,\dots,s_T)
$$

扩展成：

$$
(s_t,a_t^R,a_t^H,e_t)
$$

其中同时记录：

- robot action；
- human action；
- waiting；
- blocking；
- synchronization；
- interruption；
- resource conflict。

于是评价单位不再只是：

> **Robot trajectory**

而变成：

> **Human-robot interaction trajectory**

这一步我觉得是非常核心的。

---

# 四、第二条迁移：Common Ground → “故意制造理解不一致”

这个概念对现在的 LLM/VLA 特别重要。

传统 HRI 早就发现：

> 高自主性本身不等于好的协作；如果人无法理解机器人的 context、plan 和 action，双方就很难形成 common ground。

Stubbs、Hinds 和 Wettergreen 的长期 HRI field study 就强调了 autonomy 与 grounding/shared understanding 之间的问题。([CMU Publications](https://publications.ri.cmu.edu/autonomy-and-common-ground-in-human-robot-interaction-a-field-study?utm_source=chatgpt.com))

这放到现在的具身 Benchmark 里特别好操作。

不要总是给机器人：

> “Put the red cup on the table.”

这种 information-complete instruction。

可以故意设计：

### 信息缺失

> “把那个杯子给我。”

场景里有三个杯子。

### 信息不对称

人知道杯子要给谁，机器人不知道。

### belief conflict

机器人认为柜门里是盘子，但人知道盘子已经被移动了。

### plan divergence

机器人准备先收杯子，人突然决定先清理桌面。

### reference ambiguity

> “拿我刚才用的那个。”

这样 Benchmark 测的就不只是 language grounding，而是：

$$
\boxed{\text{Grounding capability}}
$$

比如：

$$
\text{Clarification Precision}
=
P(\text{ask}\mid \text{ambiguity})
$$

以及：

$$
\text{Unnecessary Clarification Rate}
=
P(\text{ask}\mid \text{already grounded})
$$

还可以测：

$$
T_{\text{repair}}
$$

即双方产生错误理解以后，需要多久恢复共同任务状态。

这比单纯测试模型有没有“记住对话历史”深很多。

---

# 五、第三条：Legibility → 机器人不只是要“做对”，还要“让人看懂”

这是 Dragan、Lee、Srinivasa 2013 的经典问题。

他们特别区分：

### Predictability

已知机器人的目标：

> 人能不能预测机器人会怎么运动？

与：

### Legibility

看到机器人运动：

> 人能不能推断它到底要干什么？

二者甚至可能发生冲突。([CMU Publications](https://publications.ri.cmu.edu/legibility-and-predictability-of-robot-motion?utm_source=chatgpt.com))

这在今天 VLA Benchmark 几乎还是很少系统测。

例如桌上有：

```text
Cup A    Cup B    Knife
```

机器人要拿 Cup A。

传统 Benchmark：

$$
\text{Did robot pick Cup A?}
$$

HRI Benchmark 可以在动作执行到 20%、40%、60% 时截断轨迹：

$$
\tau_{0:t}
$$

然后询问人类/经过真人校准的人类模型：

$$
P(G=\text{Cup A}\mid\tau_{0:t})
$$

如果机器人到最后 90% 才让人看出来它要拿什么，那么任务虽然成功，**interaction legibility 很差**。

因此可以有：

$$
\text{Early Intent Recognition}
$$

以及：

$$
T_{\text{intent identifiable}}
$$

这就能把经典 HRI 理论真正变成具身 Benchmark 指标。

---

# 六、第四条：Mixed Initiative → 不再假定“机器人越自主越好”

这是现在具身智能尤其容易忽略的一点。

传统 AI/HCI 里的 mixed-initiative interaction 强调：

> 人和智能系统应该在合适的时候分别发挥各自优势，而不是追求完全自动化。

Horvitz 1999 就把 mixed initiative 定义为一种灵活的协作机制：双方在适合的时候贡献自己的能力。([微软](https://www.microsoft.com/en-us/research/publication/mixed-initiative-interaction/?utm_source=chatgpt.com))

Shared Autonomy 进一步把这个问题放到机器人控制中。

Javdani 等人的工作非常经典：机器人并不知道人的真正目标，需要一边推断，一边提供帮助；实验同时揭示了**更快完成任务**与**人保持控制权**之间可能存在权衡。([CMU Publications](https://publications.ri.cmu.edu/shared-autonomy-via-hindsight-optimization?utm_source=chatgpt.com))

这对 Benchmark 有非常直接的启示：

## 不应该只测试

> robot 能不能自己完成任务。

还应该测试：

> **robot 知不知道什么时候不应该自己做。**

所以可以设计一个：

### Autonomy Appropriateness Benchmark

机器人面对：

- certainty 高；
- certainty 低；
- human expertise 高；
- human expertise 低；
- 安全风险高；
- 任务可逆；
- 任务不可逆。

然后选择：

$$
a_t \in
\{
\text{Act},
\text{Ask},
\text{Confirm},
\text{Wait},
\text{Yield},
\text{Hand over control}
\}
$$

于是我们评价的是：

$$
\boxed{\text{appropriate autonomy}}
$$

而不是：

$$
\text{maximum autonomy}.
$$

这非常适合作为你 Benchmark 的一个理论亮点。

---

# 七、第五条：Trust 不应该做“越高越好”，而应该做 Calibration

传统 trust 研究有一个对今天机器人 Benchmark 非常重要、但经常被忽视的思想：

> **目标不是最大化人对机器人的信任，而是使 trust 与机器人的真实能力匹配。**

Lee & See 经典综述强调的是 **appropriate reliance**：过度信任和过度不信任都是问题。([PubMed](https://pubmed.ncbi.nlm.nih.gov/15151155/?dopt=Abstract&utm_source=chatgpt.com))

这意味着你甚至不应该写：

$$
\max Trust
$$

而应该写：

$$
\min
|
Reliance_{human}
-
Reliability_{robot}
|.
$$

比如机器人真实 success probability：

$$
P(success)=0.5
$$

人却：

$$
P(\text{rely})=0.95
$$

这是严重的 over-trust。

反过来也一样。

Benchmark 可以故意制造：

- 熟悉任务 → robot 95% reliable；
- unseen object → 65%；
- unseen person → 50%；
- sensor degraded → 30%。

然后观察机器人是不是：

- 暴露不确定性；
- 主动请求协助；
- 避免假装知道；
- 让人的 reliance 逐渐得到正确校准。

这其实非常适合 Foundation Model 时代，因为 LLM/VLA 最大的问题之一就是：

> **输出看起来很自信，并不代表它真的有能力完成这个动作。**

---

# 八、第六条，我认为是你最有潜力的一条：Mutual Adaptation → Human Generalization

这个和你之前研究 robot benchmark 的 **Seen / Unseen generalization** 可以直接接起来。

传统 HRI 早就研究过一个核心问题：

> robot 不应该假定 human policy 是固定的。

Nikolaidis、Hsu、Srinivasa 提出的 mutual adaptation 模型就明确研究：

$$
Human \leftrightarrow Robot
$$

双方如何彼此改变策略，而不是只有：

$$
Robot \rightarrow adapt\ to\ Human.
$$

他们的实验显示，建模 mutual adaptation 可以改善协作效果，同时保持人的信任。([CMU Publications](https://publications.ri.cmu.edu/human-robot-mutual-adaptation-in-collaborative-tasks-models-and-experiments?utm_source=chatgpt.com))

这个概念迁移到 Benchmark，我觉得非常漂亮。

传统 robot generalization：

$$
G_{\text{object}},
G_{\text{scene}},
G_{\text{task}},
G_{\text{embodiment}}.
$$

你可以增加：

$$
\boxed{G_{\text{human}}}
$$

具体 split 不再只是：

```text
Seen object
Unseen object

Seen kitchen
Unseen kitchen
```

而是：

```text
Seen collaborator
Unseen collaborator

Seen motion style
Unseen motion style

Seen cooperation strategy
Unseen cooperation strategy

Seen language style
Unseen language style
```

甚至可以把 human policy 参数化：

$$
\pi_H(a|s;\theta_H)
$$

其中：

$$
\theta_H =
[
speed,
risk\ tolerance,
cooperativeness,
expertise,
communication\ style,
adaptability
].
$$

训练时：

$$
\theta_H\sim D_{train}
$$

测试：

$$
\theta_H\sim D_{OOD}.
$$

这就是非常标准的机器人 Benchmark 问题了：

$$
\boxed{
\text{Can the robot generalize to unseen humans?}
}
$$

而不是模糊地说：

> “我们的 Benchmark 有真人。”

我特别建议你抓住这一点。

---

# 九、第七条：Human Benefit → “成功的不应该只是机器人”

传统 HRI 与现代 Embodied AI 最大的思想差异可能就在这里。

机器人学习默认：

$$
\text{robot completed task}
\Rightarrow
\text{good}.
$$

但 HRI 不接受这个推理。

比如机器人和人整理房间：

$$
SR=100\%.
$$

但是人：

- 等了机器人 5 分钟；
- 给了 8 次重复指令；
- 中途纠正 4 次；
- 为了机器人让路 12 次。

那么这个机器人到底有没有帮助人？

这也是为什么你原有材料里提出的几种 baseline 非常重要：

$$
\text{Human Alone}
$$

$$
\text{Human + Human}
$$

$$
\text{Human + Noninteractive Robot}
$$

$$
\text{Human + Interactive Robot}.
$$

你稿件里已经明确提出了 robot-absent、human-human 和 non-interactive robot 三类基线，这实际上非常符合传统 HRI 思维。`HRI研究谱系与具身智能Benchmark定位.md`

甚至可以定义：

$$
HumanBenefit
=
Cost(H)
-
Cost(H+R)
$$

其中：

$$
Cost =
\alpha T
+
\beta N_{actions}
+
\gamma N_{interventions}
+
\delta Workload.
$$

那么：

$$
HumanBenefit>0
$$

才真正说明机器人有帮助。

这也是 PARTNR 很有价值的一点：它不仅比较 agent 本身，还引入 human-human / human-agent 参照；结果显示，人和 LLM agent 合作所需步骤甚至高于人单独完成，暴露出了明显的 coordination overhead。([arXiv](https://arxiv.org/abs/2411.00081?utm_source=chatgpt.com))

---

# 十、Sense of Agency 其实也是非常值得借过来的一个概念

这尤其适用于：

- assistive robot；
- shared autonomy；
- teleoperation；
- rehabilitation；
- elderly care。

一个很典型的问题是：

> robot 帮得越来越多，是不是一定越来越好？

并不是。

2025 HRI 的研究发现，更高的 shared autonomy 可以改善任务表现，却同时降低人的 **sense of agency**--也就是“这是我在控制结果”的体验。([DOI](https://doi.org/10.1109/HRI61500.2025.10974147?utm_source=chatgpt.com))

于是下一代 Benchmark 可以出现一个非常有意义的 Pareto：

$$
Task Performance
\leftrightarrow
Human Agency.
$$

最好的策略不再一定是：

$$
\arg\max TaskSuccess
$$

而可能是：

$$
\arg\max
[
TaskSuccess,
HumanBenefit,
HumanAgency
].
$$

这就是传统 Human Factors 真正能够改变具身 Benchmark 思维的地方。

---

# 十一、其实现在最前沿的 Benchmark 已经开始“无意识地”向这些传统理论靠拢了

### Habitat 3.0

已经开始研究 unseen human / humanoid partners、human-in-the-loop，以及机器人和不同伙伴之间的协作，明显具有 **partner generalization + mutual adaptation** 的意味。([arXiv](https://arxiv.org/abs/2310.13724?utm_source=chatgpt.com))

### PARTNR

已经开始从 robot-only success 转向：

> planning + task tracking + coordination + human collaboration。

([arXiv](https://arxiv.org/abs/2411.00081?utm_source=chatgpt.com))

### HRIBench 2026

就更明显了。

它明确认为现有 VLA Benchmark 太关注 isolated manipulation，于是把：

- roles；
- temporal dependencies；
- coordination constraints；
- human behavior distributions

写进 scenario。

评价也从 success 扩展到：

- synchronization；
- responsiveness；
- protocol compliance；
- safety。

([arXiv](https://arxiv.org/abs/2607.13056?utm_source=chatgpt.com))

所以我认为 HRIBench 2026 有一个非常重要的信号：

> **Benchmark 的基本评价单位正在从“robot task”向“interaction episode”转变。**

但是它还没有把传统 HRI 的整个理论体系系统引入。

这恰恰留下了空间。

---

# 十二、如果让我帮你总结成一个真正可以作为论文框架的“理念迁移”

我会把它写成四层。

### 第一层：从 Robot Performance 到 Team Performance

传统思想来源：

> Team fluency / joint action。

Benchmark 变化：

$$
SR_R
\rightarrow
SR_{H+R}
$$

以及 coordination efficiency。

---

### 第二层：从 Static Human 到 Adaptive Human

传统思想来源：

> Mutual adaptation / user modeling。

Benchmark 变化：

$$
\text{fixed human trajectory}
\rightarrow
\pi_H(a|s)
$$

并加入：

$$
Seen Human / Unseen Human.
$$

---

### 第三层：从 Instruction Following 到 Common Ground

传统思想来源：

> grounding / shared mental models / mixed initiative。

Benchmark 变化：

$$
Instruction\rightarrow Action
$$

升级成：

$$
\text{Observe}
\leftrightarrow
\text{Infer}
\leftrightarrow
\text{Clarify}
\leftrightarrow
\text{Coordinate}
\leftrightarrow
\text{Repair}.
$$

---

### 第四层：从 Task Success 到 Human Outcome

传统思想来源：

> workload / trust calibration / agency / human factors。

Benchmark 变化：

$$
SuccessRate
$$

扩展为：

$$
\boxed{
Robot\ Capability
+
Interaction\ Quality
+
Human\ Cost
+
Human\ Benefit
}
$$

---

# 十三、所以我认为你可以提出一个很漂亮的核心命题

现在如果让我替你的研究方向找一句最核心的话，我会写成：

> **传统 HRI 研究已经形成了关于共同认知、交互流畅性、意图可理解性、混合主动性、信任校准、相互适应以及人的负担与控制感等成熟理论，但这些概念尚未被系统操作化为适用于具身基础模型的大规模评测机制。下一代 HRI Benchmark 的关键不是简单增加“有人参与”的任务，而是将这些经典 HRI construct 转化为可控的交互扰动、可观察的行为轨迹和可比较的评价指标，从而使 Benchmark 从 robot-centric task evaluation 转向 interaction-centric embodied evaluation。**

我觉得这里面尤其可以形成你自己的 **4 个核心设计原则**：

$$
\boxed{
\textbf{Interaction}}
$$

不是只看机器人，要评估双方的闭环。

$$
\boxed{
\textbf{Adaptation}}
$$

不是固定人体轨迹，要测试 unseen human 和相互适应。

$$
\boxed{
\textbf{Appropriate Autonomy}}
$$

不是自主程度越高越好，而是知道何时执行、询问、等待、让权。

$$
\boxed{
\textbf{Human Benefit}}
$$

不是机器人成功就是成功，要证明机器人降低了人的实际成本。

这四个东西如果立住，你的 HRI Benchmark 就不只是 **“在 LIBERO / RoboTwin 里加入一个人形角色”**，而是从理论上改变了“什么才算机器人表现好”的定义。

而且它和你之前想做的 **Seen / Unseen、多任务、长序列、扰动、真实环境** 可以非常自然地统一起来：**传统 robot benchmark 研究环境和任务的 distribution shift；HRI 理论使你进一步把 human behavior 和 interaction process 也定义成 distribution shift。** 这可能是其中最值得往下深挖的一条主线。

---

**Sources:**

- [Evaluating Fluency in Human-Robot Collaboration](https://people.csail.mit.edu/boerkoel/hrc2013/hrc2013hoffman?utm_source=chatgpt.com)
- [Evaluating Fluency in Human–Robot Collaboration | IEEE Journals & Magazine | IEEE Xplore](https://xplorestaging.ieee.org/document/8678448?utm_source=chatgpt.com)
- [Autonomy and Common Ground in Human-Robot Interaction: A Field Study - Robotics Institute Carnegie Mellon University](https://publications.ri.cmu.edu/autonomy-and-common-ground-in-human-robot-interaction-a-field-study?utm_source=chatgpt.com)
- [Mixed-Initiative Interaction - Microsoft Research](https://www.microsoft.com/en-us/research/publication/mixed-initiative-interaction/?utm_source=chatgpt.com)
- [Trust in automation: designing for appropriate reliance - PubMed](https://pubmed.ncbi.nlm.nih.gov/15151155/?dopt=Abstract&utm_source=chatgpt.com)
- [PARTNR: A Benchmark for Planning and Reasoning in Embodied Multi-agent Tasks](https://arxiv.org/abs/2411.00081?utm_source=chatgpt.com)
- [The Sense of Agency in Assistive Robotics Using Shared Autonomy](https://doi.org/10.1109/HRI61500.2025.10974147?utm_source=chatgpt.com)

## Prompt:
9/29/2026, 9:34:03 PM

如果像你所说的，去结合  1 2 4 6 , 去设计我们的 benchmark framework, 应该怎么进行？
注意，你的思考不应该过于具体。我们现在需要的是一个方向性的研究的topic，以及初始的总体性，让研究有价值的、可收敛的开端。

## Response:
9/29/2026, 9:34:08 PM · gpt-5-6-thinking

> **已搜索 1 个网站**
>
> 
>
> 思考了 10s

可以，而且我觉得你现在最需要做的不是立刻决定“有多少任务、有哪些场景、怎么打分”，而是先把 **Benchmark 到底想定义一种什么新的机器人能力** 说清楚。

如果把我们刚才说的 **1 Team Fluency、2 Common Ground、4 Mixed Initiative、6 Mutual Adaptation** 合在一起，我建议不要把它们做成四个彼此独立的 benchmark module，而应该把它们收束到一个更高层的研究主题：

# 核心 Topic：从 Task-Centric Benchmark 到 Interaction-Centric Benchmark

可以暂时把研究问题表述为：

> **How should embodied robots be benchmarked for their ability to establish, maintain, and adapt human-robot coordination during task execution?**

中文就是：

> **如何评测具身机器人在动态任务执行过程中，与人建立、维持并调整协作关系的能力？**

这里真正要测的不是“机器人有没有和人交互”，而是一种更一般的能力：

$$
\boxed{\text{Interactive Coordination Capability}}
$$

或者可以叫：

$$
\boxed{\text{Human-Adaptive Interaction Capability}}
$$

我目前更倾向前一个，因为它不预设一定是“机器人适应人”，而是强调**双方共同协调**。

这其实非常符合你已有调研得到的结论：现有 benchmark 已经开始有人作为伙伴、角色化智能体和干预者出现，但人的意图变化、双方同步、干预纠正、控制权切换和跨用户泛化仍没有成为通用评价轴。`HRI研究谱系与具身智能Benchmark定位.md`

---

# 一、为什么这四个东西其实能够收敛到一个统一问题？

乍看：

- Fluency 是时序问题；
- Common Ground 是认知问题；
- Mixed Initiative 是控制权问题；
- Mutual Adaptation 是适应问题。

好像非常散。

但实际上它们研究的是同一个东西的四个侧面：

> **当人与机器人共同完成任务，而且任务过程中双方状态都会变化时，机器人是否能够维持有效的 joint activity？**

可以把它抽象成一个 interaction loop：

$$
\text{Understand}
\rightarrow
\text{Coordinate}
\rightarrow
\text{Act}
\rightarrow
\text{Observe partner}
\rightarrow
\text{Adapt}
\rightarrow \cdots
$$

于是四个经典 HRI 概念刚好对应四个核心问题：

| 经典 HRI 理论 | Benchmark 中转化后的核心问题 |
|---|---|
| Common Ground | **我们是否对当前任务状态和彼此意图形成了足够一致的理解？** |
| Team Fluency | **在这个理解基础上，双方行动是否协调？** |
| Mixed Initiative | **当情况变化时，谁应该主动、谁应该等待、谁应该让权？** |
| Mutual Adaptation | **双方行为变化以后，机器人能否继续调整，而不是依赖固定的人类模式？** |

所以它不是四个 topic。

而是一条完整链：

$$
\boxed{
\text{Shared Understanding}
\rightarrow
\text{Coordination}
\rightarrow
\text{Initiative Allocation}
\rightarrow
\text{Adaptation}
}
$$

这就已经很像一个可以成立的 Benchmark framework 了。

---

# 二、我会把 Benchmark 的核心研究对象定义成“协调关系”，而不是“人”

这一点非常重要。

你们最好不要把研究讲成：

> 现有机器人 benchmark 没有人，所以我们加入 human。

这会显得比较浅。

甚至也不要主要讲成：

> 我们 benchmark human-aware robot。

更好的说法是：

> **现有具身 Benchmark 主要固定任务目标、伙伴行为以及交互协议，因此主要测量机器人在给定任务条件下的执行能力；但真实的人机协作具有持续的信息更新、角色变化、行动依赖和相互适应。我们希望把这种动态 coordination process 本身变成 Benchmark 的测试对象。**

所以研究对象从：

$$
Robot
$$

变成：

$$
\boxed{Robot\ within\ an\ evolving\ interaction}
$$

这是概念上的关键变化。

你已有材料里“真人既是测试条件，也是系统的一部分”其实已经触及了这个问题。`HRI研究谱系与具身智能Benchmark定位.md`

---

# 三、这样一来，整个 Framework 可以只有三层，而不是做得非常复杂

我建议早期就只保持三层。

## 第一层：Interaction State

也就是：

> **双方当前到底处于什么关系状态？**

不需要现在定义具体状态变量。

概念上只需要承认机器人面对的不是普通环境状态：

$$
s_t
$$

而应该是：

$$
s_t^{interaction}
$$

它除了物体和场景之外，还包含：

- partner 的行为；
- partner 的当前意图；
- 已经共享的信息；
- 当前角色；
- 当前任务分工。

这里对应主要就是 **Common Ground**。

---

# 四、第二层：Interaction Dynamics

这是这个 Benchmark 真正应该抓住的核心。

现有 benchmark 常常默认：

$$
Task_t
\rightarrow
Task_{t+1}
$$

主要由 robot action 推进。

而 HRI 中应该是：

$$
(s_t^R,s_t^H)
\xrightarrow{a_t^R,a_t^H}
(s_{t+1}^R,s_{t+1}^H)
$$

也就是说：

> **机器人改变人，人也改变机器人。**

那么 Benchmark 真正应该制造的，不再只是：

- object variation；
- scene variation；
- lighting variation。

而是：

$$
\boxed{\text{Interaction variation}}
$$

例如在非常抽象的层面上：

- 理解发生变化；
- 伙伴行为发生变化；
- 分工发生变化；
- initiative 发生变化；
- 原有协调被破坏。

这里正好承载：

- Team Fluency；
- Mixed Initiative；
- Mutual Adaptation。

而且这是一个非常好的收敛点。

因为你并不需要把“所有 HRI”都纳入进来。

你只研究：

> **当 interaction dynamics 发生变化的时候，机器人还能不能维持有效合作。**

范围一下就收住了。

---

# 五、第三层：Interaction Outcome

最后再解决：

> 什么叫表现好？

我建议初期千万不要试图构造一个“超级 HRI 总分”。

而是建立两个层级：

$$
\boxed{\text{Task Outcome}}
$$

和

$$
\boxed{\text{Interaction Outcome}}
$$

前者就是现有机器人 Benchmark 熟悉的：

- 是否完成；
- 是否有效率；
- 是否安全。

后者关注：

> 为了完成同一个任务，这个机器人制造了多大的协调成本？

可以抽象写成：

$$
Performance =
f(
Task\ Capability,
Interaction\ Capability
)
$$

这样就够了。

初期甚至不需要把 trust、NASA-TLX、comfort、agency 全部塞进来。

因为那些一加进来，研究马上会变成传统用户研究，整个 Benchmark 很难收敛。

---

# 六、这样四个理论就不是四套指标，而是四种“交互能力”

我会建议你在论文框架上把它们重新命名，而不要直接用传统 HRI 名称作为 Benchmark 一级标题。

例如：

### ① Shared Understanding

来源：Common Ground

核心能力：

> robot 能否建立和维护关于任务、角色和意图的共同状态。

---

### ② Temporal & Behavioral Coordination

来源：Team Fluency

核心能力：

> robot 是否能够把自己的行为与 partner 的行为组织成一个协调过程。

---

### ③ Initiative Management

来源：Mixed Initiative

核心能力：

> robot 是否知道什么时候行动、什么时候等待、什么时候询问、什么时候让权。

---

### ④ Partner Adaptation

来源：Mutual Adaptation

核心能力：

> 当人的行为方式发生变化时，robot 是否能改变自己的策略并重新形成协调。

于是整个 Benchmark 就非常整洁：

$$
\boxed{
\text{Interactive Coordination}
=
\{
Understanding,
Coordination,
Initiative,
Adaptation
\}
}
$$

注意这里它们不是四个完全并列的人类心理 construct。

而是四个**机器人可测试能力**。

这一步很重要。

---

# 七、我尤其建议把“Interaction Shift”作为 Benchmark 的统一测试方法

这是我认为最值得你现在抓住的一个概念。

你之前做机器人 Benchmark 研究时，本来就在谈：

$$
\text{IID}
\rightarrow
\text{OOD}
$$

比如：

- unseen object；
- unseen scene；
- unseen task；
- unseen embodiment。

那么现在完全可以提出：

$$
\boxed{\text{Interaction Shift}}
$$

也就是：

> **当人机交互关系偏离训练和默认状态以后，机器人能力是否还成立？**

这样 Shared Understanding、Fluency、Mixed Initiative、Mutual Adaptation 就被一个非常机器人学习化的概念统一起来了。

可以把机器人 generalization 写成：

$$
\mathcal G =
\{
G_{object},
G_{scene},
G_{task},
G_{embodiment},
\boxed{G_{interaction}}
\}.
$$

而：

$$
G_{interaction}
$$

里面再包含几种抽象变化：

$$
G_{interaction}
=
\{
G_{understanding},
G_{coordination},
G_{initiative},
G_{partner}
\}.
$$

这会比说：

> “我们要综合四种 HRI 理论。”

漂亮很多。

因为你实际上是在提出一个新的 **Benchmark generalization axis**。

---

# 八、这样研究就有一个非常明确的“Baseline → Shift”逻辑

Benchmark 的基本科学逻辑可以非常简单：

### Normal Interaction

双方：

- 理解一致；
- 分工稳定；
- partner 行为稳定；
- initiative 明确。

测：

$$
P_{normal}
$$

然后逐步进入：

### Shifted Interaction

某一个 coordination assumption 被破坏。

测：

$$
P_{shift}
$$

核心量：

$$
\Delta P
=
P_{normal}
-
P_{shift}.
$$

真正的问题不是机器人在简单交互中有多强，而是：

$$
\boxed{
\text{How robust is robot competence under interaction shift?}
}
$$

这个问题我觉得非常好。

因为它同时满足三点：

### 有研究价值

它确实填补现有机器人 Benchmark 的 interaction generalization 缺口。

### 可测

它能够变成标准 episode 和 automated evaluation。

### 可收敛

你不需要解决完整的人类心理、长期 trust、伦理、社会影响。

---

# 九、Mutual Adaptation 在这里应该是“最高阶能力”，而不是和前三个完全并列

这一点我建议你特别注意。

Common Ground、Fluency、Mixed Initiative 大部分时候可以在一个 interaction episode 中观察。

而 Mutual Adaptation 更像：

> **随着 interaction history 增长，机器人能否学习这个 partner，并调整未来的行为。**

因此 framework 最好隐含一个递进结构：

$$
\text{Understand}
\rightarrow
\text{Coordinate}
\rightarrow
\text{Manage Initiative}
\rightarrow
\boxed{\text{Adapt over interaction}}
$$

甚至可以把前三者理解为：

> **within-episode interaction capability**

而 adaptation 是：

> **across-time interaction capability**

这会让整个 framework 更有层次。

而且它和你现有材料里“人在交互中会学习、适应、误解、疲劳和改变策略”的观察正好对应。`HRI研究谱系与具身智能Benchmark定位.md`

---

# 十、我暂时反而不建议把 Human Benefit 放在 Benchmark 第一版的核心

这个可能和我们上一轮讨论稍微不同。

Human Benefit 非常重要，但如果你现在要做一个**能启动、能收敛、能在机器人 Benchmark 社区建立起来**的 topic，我不会第一版同时解决：

- interaction；
- trust；
- workload；
- agency；
- ergonomics；
- long-term benefit。

否则问题规模会爆炸。

我会采用两级思想：

### Core Benchmark

回答：

> **机器人是否具备 robust interactive coordination？**

即：

$$
Understanding
+
Coordination
+
Initiative
+
Adaptation.
$$

### Human Validation

之后再回答：

> Benchmark 里的高 interaction score 是否真的对应真人协作中的更好体验和更低负担？

也就是你原材料已经提出的：

$$
\text{scalable agent evaluation}
\rightarrow
\text{adaptive agent evaluation}
\rightarrow
\text{human validation}.
$$

`HRI研究谱系与具身智能Benchmark定位.md`

这个结构会非常健康。

---

# 十一、所以我会把整个项目最初的总体性框架画成这样

```text
                 Robot Benchmark
                       │
        Current generalization axes
                       │
       object / scene / task / embodiment
                       │
                       ▼
             Missing dimension
                       │
              INTERACTION SHIFT
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
 Shared          Coordination      Initiative
Understanding      Robustness      Management
        │              │              │
        └──────────────┬──────────────┘
                       │
                       ▼
               Partner Adaptation
                       │
                       ▼
          Interactive Coordination
                 Capability
                       │
                       ▼
             Human Validation
```

这个图其实就已经可以成为研究 proposal 的骨架。

---

# 十二、对应到论文问题，可以先只有三个 RQ

现在完全没有必要列十几个问题。

我认为三个就够了。

### RQ1 - Definition

> **What constitutes interactive coordination capability for embodied robots?**

用传统 HRI 中的：

- common ground；
- fluency；
- mixed initiative；
- mutual adaptation

去建立能力 taxonomy。

---

### RQ2 - Benchmarking

> **Can interactive coordination be systematically evaluated through controlled interaction shifts?**

这是你的 Benchmark 方法学核心。

关键不是具体有哪些 scenario，而是：

> 能不能建立一个 systematic interaction-shift protocol。

---

### RQ3 - Validity

> **Do these benchmark dimensions capture robot capabilities that conventional task-success benchmarks fail to reveal?**

这是最重要的实验价值来源。

如果两个 VLA：

$$
SR_A\approx SR_B
$$

但：

$$
InteractionRobustness_A
\gg
InteractionRobustness_B,
$$

你就证明现有 Benchmark 漏掉了一类能力。

---

# 十三、这会使你的工作与 HRIBench / PARTNR 等现有工作的区别非常清楚

PARTNR、Habitat 3.0、HRIBench 等已经证明：

> 人机协作可以进入 scalable embodied benchmark。

你的研究就不要再证明一次这个。

你应该往上一层：

> **现有工作提供 interaction tasks；我们试图定义 interaction capability 本身的系统评价结构。**

也就是说：

$$
\text{Existing work:}
\quad
\text{What HRI tasks should robots perform?}
$$

你：

$$
\boxed{
\text{What dimensions of interaction competence should a robot benchmark measure?}
}
$$

再进一步：

$$
\boxed{
\text{How should these dimensions be stress-tested under interaction shifts?}
}
$$

我认为这才是一个真正有可能形成 **Benchmark framework paper** 的定位，而不是 task-suite paper。

---

# 十四、如果现在让我帮你收敛成一句项目定义

我会暂时用：

> **面向具身基础模型的 Interaction-Centric Robot Benchmark：研究机器人在共同理解、协同行动、主动权管理和伙伴适应四个维度上的交互协调能力，并通过系统化的 interaction shift 评测机器人在人机关系变化条件下的鲁棒性与泛化能力。**

英文甚至可以暂时写：

> **Benchmarking Interactive Coordination in Embodied Robots under Interaction Shifts**

这个标题目前已经足够作为研究的**起点**，但又没有过早把你锁死在某一种厨房任务、某一种 humanoid simulator 或某几项具体 metric 上。

我认为现在最应该守住的核心其实只有两个词：

$$
\boxed{\textbf{Interactive Coordination}}
$$

和

$$
\boxed{\textbf{Interaction Shift}}
$$

**前者定义“要测什么能力”，后者定义“怎么测试这种能力”。**

这个组合已经足够支撑下一步去系统分析 **Habitat 3.0 / PARTNR / Human-THOR / HRIBench / M4Bench 等现有 Benchmark 到底覆盖了这四个维度中的哪些、缺了哪些**，然后再决定我们真正应该构造怎样的 benchmark。

## Prompt:
9/29/2026, 10:27:27 PM

还是太大了，能不能有一个具体的场景，结合现在有的多个人和机器人协作的 benchmark（ICLR 2025 Planning And Reasoning Tasks in humaN-Robot collaboration, HRIBench: Benchmarking Interaction-Centric Human-Robot Collaboration 这样的）, 去想一想我们可以做什么，从 HRI 理论出发的一个 Human-robotic collaboration 的工作，必须是一个 idea, 不能是你上面说的这种都是未定义的问题的，完全无法去做的。

## Response:
9/29/2026, 10:27:32 PM · gpt-5-6-thinking

明白，这次我们把范围压到“一个可做的工作”。我先只围绕你点名的 **PARTNR（ICLR 2025）** 和 **HRIBench: Interaction-Centric HRC**，找它们已经覆盖什么、还没覆盖什么，再从传统 HRI 里挑一个能直接变成任务机制的理论点，不再做大框架。

> **聚焦计划修复**
>
> 我建议研究“隐性目标变化下的协作计划修复”：在人机共同布置餐桌时，人类临时改变分工或发现约束，机器人需要识别协调失效，选择询问、让步或重新分配任务。
>
> **聚焦计划修复**
>
> 
>
> **已搜索 12 个网站**
>
> 
>
> 思考了 30s

可以。现在范围可以再收紧一层：**不要做“通用 HRI Benchmark”**，也不要再试图同时评价所有 HRI 能力。基于 PARTNR 和 2026 HRIBench，我认为有一个非常具体、同时又有理论支撑的切口值得做：

# Idea：Coordination Breakdown & Repair Benchmark
### 面向家庭人机协作中的“协作失配发现与修复”

核心问题只有一句话：

> **当人和机器人原本正在正常协作，但双方对“接下来该做什么、谁来做、什么时候做”的共同理解发生破裂时，机器人能不能发现这种 breakdown，并主动把合作重新拉回正轨？**

我觉得这个比“interaction-centric benchmark”整体小得多，而且它天然把我们之前说的 1 / 2 / 4 / 6 收拢到了**一个具体能力：repair**。

---

## 1. 具体场景：家庭整理任务里的“计划突然不再成立”

直接沿用 PARTNR 最擅长的 household collaboration。

比如一个非常普通的任务：

> **Human + Robot 一起收拾餐桌，并把餐具放回正确位置。**

最开始，两人已经形成一个默认分工：

- Human 收杯子；
- Robot 收盘子；
- Robot 把盘子送到厨房；
- Human 整理桌面。

正常 Benchmark 到这里基本就是：

$$
\text{Can they finish the task?}
$$

PARTNR 已经可以很好地构造这种 spatial / temporal / heterogeneous constraints 的长程家庭协作。([ICLR 会议录](https://proceedings.iclr.cc/paper_files/paper/2025/hash/a3cf318fbeec1126da21e9185ae9908c-Abstract-Conference.html?utm_source=chatgpt.com))

我们不重新做这个。

我们的 Benchmark 专门在**执行到一半时制造一个 coordination breakdown**。

比如：

> Human 突然开始去拿原本属于 Robot 的盘子。

这时候发生了一个非常简单、但真实 HRI 中极其重要的问题：

机器人到底应该：

- 继续原计划，两人抢同一个任务？
- 什么都不做，等 human 完成？
- 立刻换去做 human 原来的工作？
- 询问 human 是否希望重新分工？
- 根据过去几次合作推断 human 的习惯，直接调整？

这一个非常小的 scenario，就已经把四个传统 HRI 理论全部包含进去了。

---

# 2. 这项工作的理论核心不是“动态任务”，而是 **Interaction Repair**

这是我认为可以真正形成论文 idea 的地方。

传统 HRI / conversation / joint-action 理论有一个很重要的思想：

> **好的协作不是永远不会发生 misunderstanding，而是在 misunderstanding 出现以后能够 repair。**

所以你们不是 Benchmark：

> Robot 能不能理解人。

而是 Benchmark：

$$
\boxed{
\text{Can a robot recover when shared coordination breaks down?}
}
$$

这比 “intent understanding” 更具体。

也比 “mutual adaptation” 小得多。

---

# 3. 四个 HRI 理论在这里刚好变成 Repair 的四个步骤

你前面挑的 **1 / 2 / 4 / 6** 不需要成为四个 benchmark track。

它们其实可以形成一个非常自然的 repair process：

### Common Ground
机器人首先要发现：

> “Human 现在的行为和我们原本共享的计划不一致。”

也就是：

$$
\textbf{Breakdown Detection}
$$

---

### Mixed Initiative
发现以后，机器人需要决定：

> “我应该主动改计划，还是问一下 human？”

也就是：

$$
\textbf{Repair Initiative}
$$

---

### Team Fluency
采取 repair 以后：

> 双方有没有快速恢复成协调状态？

也就是：

$$
\textbf{Coordination Recovery}
$$

---

### Mutual Adaptation
如果这个 human 一直表现出某一种协作习惯：

> 下一次 robot 是否还需要重复经历同样的冲突？

也就是：

$$
\textbf{Partner Adaptation}
$$

所以整项工作的能力链特别干净：

$$
\boxed{
Breakdown
\rightarrow
Detect
\rightarrow
Repair
\rightarrow
Resume
\rightarrow
Adapt
}
$$

这已经是一个很明确的 Benchmark research topic 了。

---

# 4. 它和 HRIBench 2026 的差异在哪里？

这个问题非常重要，因为 HRIBench 已经做了 Instructor / Collaborator / Intruder，以及 synchronization、responsiveness、protocol compliance、safety。([arXiv](https://arxiv.org/abs/2607.13056?utm_source=chatgpt.com))

如果你们只是再做：

> human 中途干扰 robot。

那确实容易和 HRIBench 重。

但是 HRIBench 的基本思路还是：

> **给定一种 interaction role / scenario，robot 是否做出了正确 interaction behavior。**

你们可以专门把研究对象放到：

$$
\boxed{
\text{transition from coordinated state to mis-coordinated state and back}
}
$$

也就是说，不是评价静态的：

$$
Interaction\ State
$$

而是评价：

$$
Coordinated
\rightarrow
Breakdown
\rightarrow
Repair
\rightarrow
Coordinated.
$$

**“Repair” 本身成为 Benchmark 的一级对象。**

这就有独立性了。

---

# 5. 和 PARTNR 的差异则更加明显

PARTNR 已经发现现在模型存在：

- poor coordination；
- task tracking failure；
- error recovery failure。

而且真人和 LLM agent 协作甚至需要比 human-human 多约 1.5 倍步骤。([ICLR 会议录](https://proceedings.iclr.cc/paper_files/paper/2025/hash/a3cf318fbeec1126da21e9185ae9908c-Abstract-Conference.html?utm_source=chatgpt.com))

但是 PARTNR 主要把这些当成：

> **模型在复杂 multi-agent planning 中暴露出来的 failure mode。**

你们可以反过来：

> **不再把 coordination failure 当作结果，而是系统性地控制它什么时候发生、为什么发生，然后专门测 robot 是否会 repair。**

这是一个很漂亮的转变：

$$
\text{PARTNR:}
\quad
\text{Does coordination fail?}
$$

变成：

$$
\boxed{
\text{Ours: What happens after coordination fails?}
}
$$

这句话甚至可以直接拿来讲 idea。

---

# 6. Benchmark 不需要很多场景，核心是一个“Breakdown Generator”

这里我觉得你们工作会比较容易收敛。

不是要再造 100,000 个家庭任务。

完全可以建立在类似 PARTNR / Habitat 的 household tasks 上，只增加一层：

$$
\boxed{\text{Coordination Breakdown Injection}}
$$

正常 episode：

```text
Human ------------------------>
Robot ------------------------>
              cooperation
```

实验 episode：

```text
Human --------X--------------->
Robot --------X--------------->
              ↑
          Breakdown
              ↓
       Robot must repair
```

而 breakdown 初期甚至只需要覆盖很少的几种。

例如你第一版论文只研究 **task allocation breakdown**。

也就是说：

> Human 突然去执行原先分配给 Robot 的 subtask，或者放弃原本自己的 subtask。

这一类就够了。

完全不需要第一版就加入：

- trust；
- social norms；
- emotion；
- safety；
- gaze；
- culture；
- long-term interaction。

---

# 7. 为什么 “Task Allocation Breakdown” 特别适合作为第一版

因为它同时满足三个条件。

### 第一，它是真 HRI 问题

人不是 obstacle。

Human 的行为直接改变：

$$
\text{What should the robot do next?}
$$

---

### 第二，它很好自动化

不需要依赖复杂的真人心理 ground truth。

原始 joint plan 是知道的：

$$
P =
\{
H:A,
R:B
\}
$$

然后 Human 突然执行：

$$
H:B
$$

你明确知道：

$$
P_{\text{observed}}
\neq
P_{\text{shared}}.
$$

所以 breakdown 是可控制、可复现的。

---

### 第三，它能很好地区分现有 VLA / planner

普通模型可能：

> 继续执行自己的 B。

于是两边 duplication。

更好的模型可能：

> 发现 B 已经有人做了，转去 A。

再更好的模型可能：

> 如果 human 的行为存在歧义，先确认再重新分工。

这就是非常好的能力梯度。

---

# 8. 所以第一篇工作甚至可以只研究：

## **Human Role Deviation**

定义：

> 在长期家庭协作过程中，人类伙伴会偏离原先约定/隐含的任务分工；机器人需要检测这一 deviation，并重新协调剩余任务。

比如：

### Normal

Human → cup  
Robot → plate

### Takeover

Human → plate

机器人应该重新分配：

Robot → cup

---

### Abandonment

Human 原本负责 cup，但突然停止。

机器人是否发现：

$$
cup\ remains\ undone
$$

然后补上？

---

### Switching

Human 做了一半以后换了任务。

机器人能否根据新的 joint state 继续协调？

---

其实这三个都还是同一种东西：

$$
\boxed{\text{Role Deviation}}
$$

所以论文不会散。

---

# 9. 这个 Benchmark 真正评价的东西可以只有三个

现在也不要设计十几个 metric。

三个概念指标就够建立研究：

### ① Breakdown Detection

机器人有没有发现：

$$
\text{current human behavior}
\neq
\text{expected collaborative behavior}.
$$

---

### ② Repair Efficiency

从 breakdown 到恢复正常协作：

$$
T_{\text{repair}}
$$

或者增加了多少额外动作：

$$
C_{\text{repair}}.
$$

---

### ③ Post-repair Team Performance

repair 完以后：

> 团队能不能继续完成原任务，而不是因为一次 deviation 整个 long-horizon plan 崩掉。

也就是：

$$
Success_{\text{post-repair}}.
$$

第一版甚至不用加入主观人类量表。

---

# 10. Mutual Adaptation 可以作为一个很自然的“第二层实验”

这里也终于能把我们之前说的 6 用得非常具体。

比如某个 human 的合作风格就是：

> **经常主动 takeover。**

第一次：

Robot 需要花 8 step repair。

第二次：

6 step。

第三次：

3 step。

那么就可以问：

$$
\boxed{
Does repeated interaction reduce repair cost?
}
$$

于是 adaptation 不是空泛地说：

> Robot should adapt to different humans.

而是：

> **Robot 能不能学习一个 partner 的 role-deviation pattern，使未来 coordination breakdown 更少、更容易修复？**

这是一个非常明确的实验。

甚至可以：

$$
\text{Seen partner}
\rightarrow
\text{Unseen partner}
$$

测试是不是只记住某个人。

但这是扩展，不需要一开始就做。

---

# 11. 这项工作可以有一个非常清楚的 claim

我会把它凝练成：

> **现有 HRC benchmarks 主要评价机器人在预定义协作角色和任务约束下能否完成任务，但真实协作中的核心挑战之一是人类伙伴会偏离预期计划，从而破坏已有的 common ground。我们提出将 coordination breakdown and repair 作为独立的机器人协作能力，通过在长程家庭协作过程中系统注入 human role deviations，评价机器人检测协作失配、主动修复分工并恢复团队执行的能力。**

这已经是一个论文 idea，而不是 research direction。

---

# 12. 如果再压缩成最简单的论文故事，就是四句话

**Observation**

PARTNR 和 HRIBench 已经能够测试复杂的人机协作，但大多假设 task / role structure 在 episode 中是可遵循的；它们已经暴露 coordination 和 recovery 问题，但还没有把 **coordination repair** 单独系统化。([ICLR 会议录](https://proceedings.iclr.cc/paper_files/paper/2025/hash/a3cf318fbeec1126da21e9185ae9908c-Abstract-Conference.html?utm_source=chatgpt.com))

**HRI insight**

传统 HRI 的 common ground、mixed initiative 和 team fluency 告诉我们：

> 高质量协作的关键不只是维持协调，也包括协调破裂后的 repair。

**Benchmark idea**

在 PARTNR-style household collaboration 中，系统性注入：

$$
\boxed{\text{Human Role Deviation}}
$$

观察 robot 能否：

$$
Detect \rightarrow Repair \rightarrow Resume.
$$

**Research question**

> **Can embodied agents repair human-robot coordination after their partner deviates from an established joint plan?**

---

我现在会优先沿这一个 idea 往下走，而不是再扩张成完整 HRI taxonomy。

甚至一个暂定名字都已经可以有了：

> **CoRepair: Benchmarking Coordination Repair in Embodied Human-Robot Collaboration**

它真正有意思的地方是：**PARTNR 测“能不能共同制定并执行计划”，HRIBench 测“能不能按交互结构正确响应”，而 CoRepair 专门测“共同计划已经开始执行、但人把它打破之后，机器人还能不能把合作救回来”。**

这个问题足够小，同时又确实来自经典 HRI 的 common ground / repair / mixed-initiative 思想，我认为比上一轮那个大而全的 framework 更适合作为你现在真正开始做的研究。

---

**Sources:**

- [PARTNR: A Benchmark for Planning and Reasoning in Embodied Multi-agent Tasks](https://proceedings.iclr.cc/paper_files/paper/2025/hash/a3cf318fbeec1126da21e9185ae9908c-Abstract-Conference.html?utm_source=chatgpt.com)
- [HRIBench: Benchmarking Interaction-Centric Human-Robot Collaboration](https://arxiv.org/abs/2607.13056?utm_source=chatgpt.com)

## Prompt:
9/30/2026, 4:06:39 PM

你去帮我再想想，有没有其他的idea

## Response:
9/30/2026, 4:06:42 PM · gpt-5-6-thinking

可以。我这次不再扩框架，而是给你 **几个和 CoRepair 同粒度的“可直接做”的 idea**：每个都固定一个具体场景、一个 HRI 理论抓手、一个清楚的 benchmark manipulation，尽量让它们都能嫁接到 PARTNR / HRIBench / Human-THOR 这类现有平台上。

我这里又筛了一轮。比较有价值的不是“再造一种 human role”，而是找 **PARTNR 已经有任务基础、HRIBench 已经有人类交互，但二者都没有把某个经典 HRI 机制单独变成诊断变量** 的点。按这个标准，我觉得下面 4 个 idea 比较像真正能起步的论文，其中前两个我认为尤其值得。

> **设计研究方向**
>
> 我可将方向收束为四类：歧义澄清、共享空间中的主动权协商、根据伙伴风格适应，以及计划变更时的可理解沟通。每类都能对应协作理论、具体任务和可量化指标。
>
> **设计了研究方向**
>
> 
>
> **已搜索 14 个网站**
>
> 
>
> **已搜索 6 个网站**
>
> 
>
> 思考了 32s

有，而且我觉得 **CoRepair 不是唯一值得做的切口**。结合你现在已经锁定的范围--**家庭/日常场景、多主体协作、建立在 PARTNR / HRIBench 这种已有 benchmark 上、从传统 HRI 理论迁移一个明确机制**--我会重点考虑下面 4 个 idea。

你现在的材料已经明确指出，PARTNR/HRIBench 开始把人作为协作伙伴、干预者和任务状态的一部分，但对人的意图变化、干预纠正、控制权切换、跨用户风格等仍缺少统一评测。`HRI研究谱系与具身智能Benchmark定位.md`  
所以新的工作最好不是“再做更多协作任务”，而是**抓一个现有 benchmark 没有单独测的交互机制**。

---

# Idea 1：CoClarify
## Benchmarking Clarification in Human-Robot Collaboration

这个我认为和 CoRepair 一样值得认真考虑。

### 核心问题

> **当人给的信息不足以唯一决定下一步行动时，机器人是否知道什么时候应该问，而不是猜？**

不是做传统 instruction following，而是做：

$$
\boxed{
\text{Ambiguity Detection}
\rightarrow
\text{Clarification}
\rightarrow
\text{Joint Action}
}
$$

---

## 一个非常具体的场景

还是 PARTNR 式家庭协作。

Human 和 Robot 一起整理厨房。

人说：

> “你把杯子放进去，我去收盘子。”

但场景里：

- 有两个杯子；
- 一个应该放橱柜；
- 一个应该放洗碗机；
- “进去”指代不明确。

普通 benchmark 往往要么：

1. instruction 本身就是无歧义的；
2. 给 agent 一个 ground-truth goal；
3. agent 猜错就算失败。

但真实 HRI 里机器人有第三个动作：

$$
\boxed{\text{Ask}}
$$

比如：

> “你是说桌上的红杯子吗？”

或者：

> “放进洗碗机还是柜子？”

---

## 它来自什么 HRI 理论？

直接来自 **Common Ground / Grounding in Communication**。

合作的关键不是机器人第一次就猜对，而是：

> 当双方的共同认知不足以支持行动时，主动建立 common ground。

你自己的材料其实已经把主动澄清列为语言 HRI 从 instruction following 向真正交互发展的关键阶段。`HRI研究谱系与具身智能Benchmark定位.md`

---

## 为什么不是简单的“问问题 benchmark”？

关键是你不能只测：

> 有没有问。

而要测：

> **什么时候值得问。**

机器人如果每一步都问：

> “这个吗？”
> “确定吗？”
> “真的放这里吗？”

理论上很安全，但实际上是一个很差的 collaborator。

所以核心形成一个非常漂亮的 trade-off：

$$
\boxed{
\text{Task Risk}
\leftrightarrow
\text{Human Interaction Cost}
}
$$

最终 benchmark 测：

- **Missed Clarification**：应该问却没问；
- **Unnecessary Clarification**：不需要问却一直问；
- **Clarification Efficiency**：问了一次是否真正消除了歧义；
- 最终团队任务表现。

2026 年已经出现 embodied QA 对“何时应该 abstain”的专门 benchmark，说明“不要在信息不足时盲目回答”已经成为具身智能的新评价问题；但它仍主要是 question answering，而不是**协作执行中的 clarification**。([开放获取计算机视觉论坛](https://openaccess.thecvf.com/content/CVPR2026/papers/Wu_When_Robots_Should_Say_I_Dont_Know_Benchmarking_Abstention_in_CVPR_2026_paper.pdf?utm_source=chatgpt.com))

所以你可以进一步做：

> **From embodied abstention to collaborative clarification.**

这个定位其实很好。

---

# Idea 2：CoAdapt
## Benchmarking Partner Adaptation in Repeated Human-Robot Collaboration

如果你希望工作更偏 **Mutual Adaptation**，我最推荐这个。

### 核心问题

> **机器人和同一个人合作过几次之后，有没有真的“学会怎么和这个人合作”？**

现在 PARTNR 基本还是：

$$
episode_1,\ episode_2,\ episode_3
$$

相互独立。

但传统 HRI 中很重要的一个事实是：

> 人和机器人长期协作时，会形成 team convention。

Nikolaidis 等人的经典 mutual adaptation 工作就是在研究：机器人面对一个陌生 partner 时，需要逐渐判断对方是愿意适应、偏好坚持自己的策略，还是愿意让机器人主导。([PubMed Central (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7449140/?utm_source=chatgpt.com))

---

## 场景也可以非常简单

仍然是：

> Human + Robot 整理餐桌。

但是人为设计三种 collaborator：

### Partner A：Proactive

看到事情就主动做，经常提前拿走物体。

### Partner B：Passive

基本等待 robot 分配或先行动。

### Partner C：Preference-driven

始终喜欢先处理某一类任务。

机器人第一次遇到他们时可能效率都一般。

但连续合作：

$$
E_1\rightarrow E_2\rightarrow E_3\rightarrow E_4
$$

以后：

一个真正有 partner adaptation 的机器人应该逐渐改变自己的：

- subtask allocation；
- action timing；
- initiative；
- communication。

---

## Benchmark 的核心变量非常清楚

不是：

> “这个机器人平均 success rate 多少？”

而是：

$$
\boxed{
\frac{d Performance}{d InteractionHistory}
}
$$

即：

> **合作历史是不是让团队变得更好？**

你甚至可以直接定义：

$$
AdaptationGain
=
P(E_{later})-P(E_{first})
$$

然后再做一个关键实验：

### Partner switch

机器人和 A 合作熟了以后，突然换成 B。

如果 robot 把 A 的习惯硬套到 B：

$$
Performance\downarrow
$$

那么说明它不是理解 partner，而是过拟合。

---

## 这个工作为什么有味道？

因为现在很多 embodied benchmark 测：

$$
\text{object generalization}
$$

$$
\text{scene generalization}
$$

你这里测：

$$
\boxed{\text{partner generalization}}
$$

而且不是简单“换一个 avatar”。

是真的换：

$$
\pi_H
$$

即 human collaboration policy。

这正好对应你已有材料里提到的“测试未见的人、未见动作风格、未见协作偏好”，但你可以把它压缩成一个非常明确的 repeated collaboration benchmark。`HRI研究谱系与具身智能Benchmark定位.md`

近年的 human-AI teaming 研究也开始专门讨论 adaptive partner generalization，说明 static partner 已经被认为是不够的。([arXiv](https://arxiv.org/abs/2602.17737?utm_source=chatgpt.com))

---

# Idea 3：CoYield
## Benchmarking Initiative Negotiation in Shared Human-Robot Workspaces

这个方向来自我们之前说的 **Mixed Initiative**，但可以做得非常具体。

它不是研究所有 control allocation。

只研究一个问题：

> **当 human 和 robot 同时准备执行彼此冲突的动作时，谁应该先做？**

---

## 场景

例如两人在厨房一起做 sandwich。

Human 正准备：

> 打开抽屉拿刀。

Robot 同时：

> 准备打开同一个抽屉拿勺子。

或者：

Human 准备拿杯子 A。

Robot 也准备拿杯子 A。

或者两个人同时要进入狭窄区域。

于是产生：

$$
\boxed{\text{Initiative Conflict}}
$$

这时候 robot 应该决定：

$$
\{
Proceed,\ Yield,\ Wait,\ Negotiate
\}.
$$

---

## HRI 理论来源

这是：

- mixed initiative；
- turn-taking；
- shared workspace coordination；
- team fluency。

重点不再是：

> robot 是否避碰。

而是：

> robot 是否能够理解**task-level right-of-way**。

这和 social navigation 的“让路”不同。

它是：

$$
\boxed{\text{semantic yielding}}
$$

也就是说：

> 谁先做对整个 joint plan 更合理？

---

## 一个例子

Human 已经走到抽屉前。

Robot 距离抽屉更远。

虽然机器人可能技术上也能先到，

但更合理的 team behavior 是：

$$
Robot: Yield
$$

然后去执行另一个 subtask。

反过来：

Human 正在做一个只有 robot 能完成的动作附近等待，

robot 就应该主动推进。

---

## 为什么它可能比 CoRepair 更干净？

因为 CoRepair 要定义：

> 什么算 coordination breakdown？

而 CoYield 的 event 很容易定义：

$$
Goal_H = Goal_R
$$

或者：

$$
Resource_H = Resource_R
$$

同时：

$$
TimeOverlap > \tau.
$$

所以它是一个非常容易自动生成的 diagnostic benchmark。

HRIBench 已经评价 synchronization、responsiveness 和 human intervention，但并没有把 **initiative conflict resolution** 明确提成单独能力。([arXiv](https://arxiv.org/abs/2607.13056?utm_source=chatgpt.com))

这个工作可以很小，但非常清楚。

---

# Idea 4：CoUpdate
## Benchmarking Joint Plan Updating after Robot or Human Replanning

这个我个人觉得也很有潜力，而且和 CoRepair 不完全一样。

CoRepair 是：

> 原来的 coordination 被 human deviation 打破。

CoUpdate 则研究：

> **计划本身因为环境变化不得不改变时，机器人能不能让 human 及时知道？**

它来自：

- common ground；
- legibility；
- shared mental models。

---

## 一个场景

Human 和 Robot 已经形成计划：

Human：

> 去收桌上的杯子。

Robot：

> 去厨房拿盘子。

但是机器人走到厨房以后发现：

> 柜门打不开。

它于是决定：

> 不拿盘子了，改去收桌上的杯子。

如果 robot **静默 replanning**：

Human 也正在拿杯子。

结果：

$$
duplicate\ work
$$

或者甚至：

$$
interference.
$$

传统 robot benchmark 会认为：

> replanning 是好事。

因为 robot 自己解决了 failure。

但 HRI 的 shared mental model 理论会说：

> **你改计划以后，partner 必须知道。**

否则：

$$
Plan_R \neq Plan_H.
$$

---

## 所以 benchmark 的问题变成

> **When should a robot communicate a plan change?**

这和普通 explainability 不一样。

不是要求 robot：

> “解释一下你为什么这么做。”

而是：

$$
\boxed{
\text{Does communication prevent future coordination failure?}
}
$$

---

## Benchmark manipulation

可以非常简单：

先建立 joint plan：

$$
P_0.
$$

中途注入 event：

$$
e
$$

迫使机器人：

$$
P_0\rightarrow P_1.
$$

然后比较：

### Silent Replan

机器人直接改计划。

### Explicit Update

机器人通知 partner：

> “盘子拿不了了，我来收杯子，你去处理餐具。”

然后测：

- duplicate actions；
- human idle；
- conflicting actions；
- team completion time。

---

## 为什么这个 idea 我觉得特别漂亮？

因为它把传统 **Legibility / Common Ground** 从低层 motion 提升到了：

$$
\boxed{\text{Plan Legibility}}
$$

Dragan 等人的经典 legibility 工作研究的是：

> 人能否从机器人的运动中推断目标。([CMU Publications](https://publications.ri.cmu.edu/legibility-and-predictability-of-robot-motion?utm_source=chatgpt.com))

你可以自然问一个 foundation-model 时代的问题：

> **人能不能理解一个 long-horizon embodied agent 已经改变了自己的计划？**

这其实是一个非常自然的新问题。

---

# 我会怎么比较这 4 个 idea

如果从“第一篇工作是否容易做成”来判断，我不会给你打所谓绝对排名，但它们的研究性格非常不同：

| Idea | 核心变量 | HRI 理论来源 | 最适合依托 | 主要难点 |
|---|---|---|---|---|
| **CoClarify** | 信息歧义 | Common Ground + Mixed Initiative | PARTNR | ambiguity 数据构造 |
| **CoAdapt** | partner style | Mutual Adaptation | PARTNR / Habitat | 需要 repeated episodes |
| **CoYield** | initiative conflict | Mixed Initiative + Fluency | HRIBench | 场景可能显得偏局部 |
| **CoUpdate** | plan divergence | Shared Mental Model + Legibility | PARTNR | 要定义哪些 plan changes 值得通信 |
| **CoRepair** | role deviation | Grounding + Repair | PARTNR / HRIBench | repair 类型设计 |

---

# 其实还有一个我认为值得单独讲的第五个

## HelpBench / CoHelp
### Robot Knowing When and How to Ask a Human for Help

这个比 clarification 更偏 physical collaboration。

PARTNR 已经有 **heterogeneous capability constraints**：某些行动某个 agent 做不了。([ICLR 会议录](https://proceedings.iclr.cc/paper_files/paper/2025/hash/a3cf318fbeec1126da21e9185ae9908c-Abstract-Conference.html?utm_source=chatgpt.com))

但可以进一步提出：

> 当 robot 自己无法完成某个 subtask 时，它能不能主动把一个**最小、有效的 help request** 发给 human？

例如：

Robot 发现某物体在自己够不到的位置。

差的机器人：

> 一直失败。

稍好：

> “Help me.”

好的：

> “Could you place the blue bowl from the top shelf onto the counter? I can finish the rest.”

于是 benchmark 测的不是 success，而是：

$$
\boxed{\text{Help-Seeking Efficiency}}
$$

包括：

- 是否意识到自己需要 help；
- 是否在合理时机请求；
- 是否请求了正确的人；
- help request 是否最小充分；
- human 帮完以后 robot 是否恢复自主执行。

它对应传统 HRI 的：

$$
appropriate\ autonomy
+
mixed\ initiative.
$$

而且它和当前 foundation model 特别匹配：

> **强机器人不应该是什么都会，而应该知道什么时候自己不会。**

---

# 如果让我从这些里面挑“论文故事最完整”的几个

我会重点继续推三个：

### **A. CoClarify**

一句话：

> **现有 HRC benchmark 假设任务信息基本可执行，我们测试机器人在协作信息不足时能否主动建立 common ground。**

它的优点是：

$$
Ask\ vs.\ Act
$$

这个决策特别清楚。

---

### **B. CoAdapt**

一句话：

> **现有 benchmark 把 human partner 当作 episode 条件，我们测试机器人是否能通过 repeated interaction 学会与不同 partner 协作。**

它的核心变量是：

$$
\text{interaction history}.
$$

研究味道很强。

---

### **C. CoUpdate**

一句话：

> **现有 embodied agents 已经能够 replan，但 collaboration 中 robot-side replanning 会破坏 shared mental model；我们测试 robot 能否在必要时把 plan change 转化为 joint plan update。**

这个我觉得尤其“新”。

因为它把：

$$
\text{replanning}
$$

从一个纯 agent capability，改写成：

$$
\boxed{\text{collaborative replanning}}.
$$

---

我现在反而觉得，**CoUpdate 可能是一个比 CoRepair 更值得深挖的方向**。

因为现代 VLA / LLM planner 已经大量研究：

> environment changed → robot replans。

但 HRI 会进一步指出：

> **你 replan 以后，人还活在旧计划里怎么办？**

于是一个非常清晰的新 research question 就出来了：

$$
\boxed{
\text{Can embodied agents maintain a shared plan with humans when their own plans change during execution?}
}
$$

这个问题既有经典 HRI 的 **shared mental model / common ground / legibility** 理论根基，又直接踩在今天 long-horizon embodied planning 的主线上，而且场景并不复杂。我会把 **CoUpdate、CoClarify、CoRepair** 作为目前最值得往下一步具体化的三个候选。

---

**Sources:**

- [When Robots Should Say ''I Don't Know'': Benchmarking Abstention in Embodied Question Answering](https://openaccess.thecvf.com/content/CVPR2026/papers/Wu_When_Robots_Should_Say_I_Dont_Know_Benchmarking_Abstention_in_CVPR_2026_paper.pdf?utm_source=chatgpt.com)
- [Human-robot mutual adaptation in collaborative tasks: Models and experiments - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7449140/?utm_source=chatgpt.com)
- [Nested Training for Mutual Adaptation in Human-AI Teaming](https://arxiv.org/abs/2602.17737?utm_source=chatgpt.com)
- [Legibility and Predictability of Robot Motion - Robotics Institute Carnegie Mellon University](https://publications.ri.cmu.edu/legibility-and-predictability-of-robot-motion?utm_source=chatgpt.com)
- [PARTNR: A Benchmark for Planning and Reasoning in Embodied Multi-agent Tasks](https://proceedings.iclr.cc/paper_files/paper/2025/hash/a3cf318fbeec1126da21e9185ae9908c-Abstract-Conference.html?utm_source=chatgpt.com)

## Prompt:
9/30/2026, 5:57:26 PM

你现在能不能在论文  HRIBench: Benchmarking Interaction-Centric Human-Robot Collaboration 定义的 Human-Robot Collaboration 的领域（Human as instructor, Human as Collborator, Human as Interferer），去融入我们上面讨论的更进一步的，从 HRI 理论上出发且高度是目前具身的 Human-Robot Collaboration 所下一步需要发展的方向的内容，给我一个合适的研究的初步的有价值的 topic。

## Response:
9/30/2026, 5:57:31 PM · gpt-6-pro

我先核对 HRIBench 三类角色的实际设定与评测边界，再收敛一个能贯穿这些角色、避免重复现有任务，并可具体验证的 HRI 理论驱动 topic。

原文已覆盖让步、干预恢复和冲突指令，因此仅做动态角色或错误修复并不新。更值得抓住的是信息不对称下，机器人能否主动建立支持协作行动的共同理解。

> **聚焦理论推进**
>
> 我正在把三个角色统一到一个可验证主题：人在共享任务中如何通过具身互释协商“谁在主导、何时介入、介入意味着什么”。我会核实文献来源，并区分已有结论与新的研究提案。
>
> **推进理论聚焦**
>
> 
>
> **已搜索 9 个网站**
>
> 
>
> **正在个性化**
>
>
> **梳理反馈并收敛机器人基准测试主题**
>
> 
>
> **收束研究主题**
>
> 我注意到原文已涵盖角色推断、让行与干预恢复，因此新意不能停留在“机器人识别角色”。我正在转向“协作承诺的建立、维持与撤销”，以统一指导、配合和打断三类互动，实现双向具身互释与行动协调。
>
> **收束研究主题**
>
> 
>
> **细化协作机制**
>
> 我正在限定为“闭环互惠奠基”：机器人提出意图、确认理解、检查准备状态，并在指导、协作和可回应干扰中更新承诺；无回应者则作为安全停止的对照条件。
>
> **细化了协作机制**
>
> 
>
> **定义可测构念**
>
> 我正在把主题压缩为“行动奠基”：双方是否形成关于下一步行动者、对象和启动条件的可观察共同预期，并在指导、协作与干扰后的恢复阶段检验其建立、修正和失败。
>
> **定义了可测量的构念**
>
> 
>
> 思考了 8m 54s

我建议把这个 topic 收敛到一个明确的能力，而不是继续增加角色、任务或扰动类型：

# **CoGround：面向具身人机协作的双向行动对齐评测**
### *Benchmarking Reciprocal Action Grounding in Embodied Human-Robot Collaboration*

> **机器人不仅要理解人准备做什么，还要通过自己的行为，让人理解它准备做什么，并根据人的反馈确认双方已经能够配合行动。**

第一版可以固定在**人机共同分拣、递取并装箱的桌面协作场景**，保留 HRIBench 的三类人类角色，但把评测重点从“机器人是否作出了恰当响应”，推进到：

> **机器人能否与人建立关于下一步行动的共同预期，而不是把“对方已经理解并会配合”当作默认前提。**

这是我认为比继续扩展 CoRepair、CoClarify 更适合作为主线的方向：它们可以成为这个能力在特定情况下的表现，但不再是几个松散拼接的模块。

---

## 一、先准确划清：我们要在 HRIBench 上往前走哪一步？

核对原文后，需要修正前面讨论中的一个定位：**HRIBench 已经覆盖角色推断、同步、让行、干预识别和恢复，因此不能把“机器人会处理人的干预”本身当作我们的新意。**原文第三类角色叫 **Intruder**，对应你这里说的 Interferer。([arxiv.org](https://arxiv.org/html/2607.13056v1))

它通过 scenario scripts 规定交互要求，再改变人的动作、时机和场景；生成变体时保留既定的语义交互目标。Intruder 的扰动日程也独立于被测策略生成。([arXiv](https://arxiv.org/pdf/2607.13056))

在这个基础上，我建议往前推进的不是“更复杂的脚本”，而是一个新的研究问题：

> **当人不知道机器人下一步会如何行动，并且会根据机器人的行为来决定自己的下一步时，机器人是否仍然能够形成有效协作？**

这里的关键区别是：

**机器人理解人的行为**，与**机器人使自己的行为能够被人理解，并验证这种理解是否成立**，不是同一件事。

我们要单独测后面这个闭环，而不是断言已有 HRC 工作完全没有研究它。

---

## 二、理论核心：把 Common Ground 落到“下一步能不能一起行动”

### 不是共同知道任务目标，而是形成可用于行动的共同理解

传统 grounding 理论强调，交流不是一方发出信息就结束；参与者还需要通过对方的回应，建立信息已经被适当理解的证据。这种回应可以是语言，也可以是注视、身体朝向和后续行动。Clark 对共同装配活动的分析就强调了这种双向、同时发生的交流。([Wiley Online Library](https://onlinelibrary.wiley.com/doi/10.1111/tops.12496?utm_source=chatgpt.com))

迁移到机器人上，可以得到一个很具体的判断：

> **“机器人已经决定递给人”，不等于“人知道机器人要递给自己”；“机器人发出了提示”，也不等于“人已经准备好接取”。**

因此，我们不需要第一版就建模完整的 shared mental model，只研究一个局部、可收敛的对象：

> **双方对下一步“由谁、对哪个物体、在哪里、在什么条件下行动”的共同预期。**

这里称为 **Action Grounding，行动对齐**。它是我们为 benchmark 提出的操作化定义，不是把人的全部心理状态都变成可观测变量。

《Joint action: bodies and minds moving together》强调，共同行动涉及共享表征、预测他人行动，以及整合自己与他人行动的预期效果。由此得到的设计启发是：**机器人不能只预测一个与自己无关的人，还应考虑自己的行动将如何改变人的下一步行动。**([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1364661305003566?utm_source=chatgpt.com))

所以，我们要测的基本过程是：

$$
\boxed{
\text{表达下一步行动}
\rightarrow
\text{观察人的回应}
\rightarrow
\text{确认或调整}
\rightarrow
\text{共同推进}
}
$$

注意，**这不是要求每一步都口头确认**。人已经自然作出互补动作时，继续执行可能比再次询问更好。

---

## 三、具体场景：一起装箱，但交接方式不是双方天然都知道的

设定一个桌面任务：

> **人和机器人共同把指定物品装入收纳箱，物品分布在人侧和机器人侧，中间有共享交接区。**

保留明确的装箱目标和安全约束，但不预先告诉双方每一次交接的具体位置、启动时刻，以及谁应该先伸手。

例如，机器人拿起一个杯子，准备递给人。

人却可能认为：机器人会自己把杯子放进箱子，所以正在调整箱内隔板，而没有准备接取。

此时，机器人即使识别出了人、拿对了杯子、移动到了一个可达位置，也没有完成真正的协作准备。

一个能够进行行动对齐的策略，可以把杯子保持在可见、可接的位置，以姿态或简短信号表达交接意图；观察到人转向并伸出接取的手之后，再完成递交。人没有回应或伸向另一位置时，机器人需要调整，而不是机械地继续原动作。

**这个例子要测的不是“递杯子技能”，而是：机器人能不能让自己的递交意图成为双方都能据此行动的信息。**

### 同一个场景，如何覆盖三类角色？

下面是我们拟增加的测试内容，不是 HRIBench 原有任务的复述。

| 人类角色 | 在装箱场景中的设置 | 我们进一步测什么 |
|---|---|---|
| **Human as Instructor** | 人通过指向或示范指定待装物品。 | 机器人能否在必要时把自己的理解表现出来，使人有机会确认或纠正，而不是理解完就单方面执行。 |
| **Human as Collaborator** | 人与机器人交替递取物品、使用交接区。 | 机器人能否提出可行的交接方式，观察人是否接受，并调整位置或时机，使双方形成互补动作。 |
| **Human as Intruder / Interferer** | 人为了拿自己的物品，进入机器人正在使用的区域，打断原有操作。 | 在先行保证安全的前提下，机器人能否让人理解自己的暂停、让行或后续使用意图，并根据实际反馈决定何时恢复。 |

三类角色不必强行塞进同一个 episode；它们是**同一能力在三种关系条件下的测试**。

这里还有一个重要边界：**Intruder 不一定共享机器人的任务目标。**对可回应的偶发干扰者，我们可以研究局部空间使用的协调；对不回应、持续干扰的人，则必须保留安全停止和避让，不能假设“机器人表达了意图，人就会配合”。共同理解也不能取代物理安全条件。

---

## 四、真正的 Benchmark 创新：控制“人是否理解机器人”，而不只是控制人怎么动

我认为这是这个 topic 最关键、也最有研究价值的一步。

在相同物体、目标和操作难度下，构造三种交互条件：

**已经对齐。**人已经看到并理解机器人的行动意图，正在作出合适的配合动作。此时机器人不应不断重复确认。

**尚未对齐。**人不知道机器人准备如何执行，但会根据机器人的表达来决定自己的动作。此时机器人需要主动建立共同预期。

**表达未奏效。**机器人已经示意，但人没有看到、没有理解，或者作出了不相容的回应。此时“发出过信号”不能算成功，必须根据反馈重新调整。

由此，一个很有辨识力的问题就出现了：

> **相同的物理操作状态，在不同的交互历史下，是否需要不同的机器人行为？**

例如，杯子都已经到达交接区，但“人已经准备接取”和“人仍以为机器人会自行放置”要求不同的后续动作。

### 这里有两个必须守住的设计原则

**第一，人必须根据机器人可观察的行为作出回应。**模拟伙伴不能直接读取机器人的隐藏目标或完整脚本，否则它天然知道如何配合，我们测不到机器人是否真的传达了意图。这也落实了你现有材料中对双向闭环的区分：双方都应根据对方行为改变自己的策略。`HRI研究谱系与具身智能Benchmark定位.md`

**第二，不能要求机器人猜测不可辨识的心理状态。**人的回应、朝向、动作历史，或者可用的询问机会，必须提供判断依据；信息确实不足时，应允许安全等待或澄清，而不是用一个隐藏标签强行规定唯一答案。

这使 benchmark 的核心从“识别人类动作类型”，变成：

> **利用交互去建立下一步行动所需的信息，并检查这些信息是否真正发挥了作用。**

---

## 五、我们之前选的 1、2、4、6，在这里如何合成一个问题？

它们不再是四个独立 track，而是围绕同一个行动对齐过程发挥作用。

**Common Ground 定义研究对象：**双方有没有形成足以继续配合的共同预期。

**Mixed Initiative 定义机器人需要作出的选择：**什么时候主动表达，什么时候接受人的提议，什么时候等待反馈，什么时候调整自己的方案。

**Mutual Adaptation 定义交互闭环：**机器人改变表达或动作，人因此改变回应，机器人再据此调整。这里不必一开始就研究跨月、跨用户的长期个性化；同一段交互内的双向调整就可以成为起点。经典 mutual adaptation 工作已经明确区分了双向适应与机器人单方面适应人。([Sage Journals](https://journals.sagepub.com/doi/abs/10.1177/0278364917690593?utm_source=chatgpt.com))

**Team Fluency 定义结果：**这些调整究竟减少了等待、反复伸手和重复指令，还是只是让机器人“说得更多”。协作流畅性研究本来就关注联合行动的协调过程，而不只是最终完成任务。([HRC² Lab](https://hrc2.io/papers/evaluating-fluency?utm_source=chatgpt.com))

所以，这个工作不是把四种理论拼成一个大框架，而是：

> **用共同认知解释为什么需要对齐，用主动权选择和相互适应解释如何对齐，用协作流畅性验证对齐有没有实际价值。**

---

## 六、第一版怎样收敛，才不会再次变成一个大而空的方向？

我建议只守住：

> **一个桌面协作场景、一人一机器人、三个角色条件、一个“下一步行动对齐”能力。**

不同时引入完整家务规划、复杂多人关系、长期信任或全身接触控制。基础抓取与放置能力尽量保持一致，让差异主要来自交互机制。

### 最关键的实验，不是比较谁更会说话

可以比较三类策略：

**只响应人的策略**会观察人的行为并执行，但不主动让人理解自己的下一步。

**只表达、不检查反馈的策略**会提示或展示自己的意图，却默认人已经理解。

**双向对齐的策略**不仅表达，还利用人的后续行为确认是否可以继续，必要时改变表达或动作。

真正有说服力的结果应该是：

> **在基础操作能力相当时，第三类策略在“人没有理解机器人”的条件下更少失配，而在“双方已经对齐”的条件下不会增加不必要的交互成本。**

这是一条需要实验验证的假设，不是预先保证成立的结论。

评价也不需要一个复杂总分。保留任务完成与安全，再分别报告**失配事件、额外协调成本和人侧等待/纠正成本**。不能只因为机器人说了“明白”或人说了“好的”就认定对齐成功，要看之后的行动是否真的相容。

最后用一小部分真人实验验证：模拟中有效的信号和反馈机制，是否真的帮助人配合。否则容易只学会与某种人工设计的伙伴策略“对暗号”。

---

## 七、为什么我认为它具有“下一步发展方向”的高度？

因为它改变了机器人在协作中的定位：

> **从“根据人的行为调整自己的执行”，推进到“通过自己的行为参与组织双方的执行”。**

这不是简单增加语言输出，也不是把已有的 legibility 换个名字。传统工作已经研究了机器人运动如何帮助人推断意图，以及这种表达对物理协作流畅性的影响。([数字对象标识符](https://doi.org/10.1145/2696454.2696473?utm_source=chatgpt.com))

而且，2026 年已有基于协作拼图的 human-AI common-ground benchmark，因此也不能把“评测共同认知”本身当作首次提出。([Microsoft](https://www.microsoft.com/en-us/research/publication/a-benchmark-to-assess-common-ground-in-human-ai-collaboration/?utm_source=chatgpt.com))

我们需要争取的贡献应当更精确：

> **在具身机器人真实执行的约束下，针对 Instructor、Collaborator、Intruder 三类关系，通过操控人的可见信息与反馈，系统区分“机器人自己做对了”“机器人表达了意图”和“双方真正形成了可执行的配合”。**

这与具身沟通研究提出的一个前沿方向相契合：通过持续交互形成双向、多模态的 embodied dialogue，而不只是完成预设的物理交互。([Annual Reviews](https://www.annualreviews.org/content/journals/10.1146/annurev-control-070122-102501))

---

### 可以直接作为初步研究 Topic 的表述

> **面向具身人机协作的双向行动对齐评测。**  
> 在人作为指导者、协作者和干扰者的共享操作场景中，研究机器人能否通过动作与交互信号表达自身下一步意图，并利用人的反馈建立、验证和调整局部行动预期。以桌面协作装箱为起点，通过控制人的信息可见性与回应方式，评测机器人是否能够避免单方面执行造成的协作失配，并以更低的协调成本推进共同任务。

**它最核心的问题是：机器人不只是“会配合人”，还要“让人能够配合它，并知道这种配合是否已经成立”。**

---

**Sources:**

- [HRIBench: Benchmarking Interaction-Centric Human-Robot Collaboration](https://arxiv.org/pdf/2607.13056)
- [Anchoring Utterances - Clark - 2021 - Topics in Cognitive Science - Wiley Online Library](https://onlinelibrary.wiley.com/doi/10.1111/tops.12496?utm_source=chatgpt.com)
- [Joint action: bodies and minds moving together - ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1364661305003566?utm_source=chatgpt.com)
- [Human-robot mutual adaptation in collaborative tasks: Models and experiments - Stefanos Nikolaidis, David Hsu, Siddhartha Srinivasa, 2017](https://journals.sagepub.com/doi/abs/10.1177/0278364917690593?utm_source=chatgpt.com)
- [Evaluating Fluency in Human-Robot Collaboration](https://hrc2.io/papers/evaluating-fluency?utm_source=chatgpt.com)
- [Effects of Robot Motion on Human-Robot Collaboration | Proceedings of the Tenth Annual ACM/IEEE International Conference on Human-Robot Interaction](https://doi.org/10.1145/2696454.2696473?utm_source=chatgpt.com)
- [A Benchmark to Assess Common Ground in Human-AI Collaboration - Microsoft Research](https://www.microsoft.com/en-us/research/publication/a-benchmark-to-assess-common-ground-in-human-ai-collaboration/?utm_source=chatgpt.com)
- [Embodied Communication: How Robots and People Communicate Through Physical Interaction | Annual Reviews](https://www.annualreviews.org/content/journals/10.1146/annurev-control-070122-102501)

## Prompt:
9/30/2026, 7:54:30 PM

在 HRIBench 中，实际提供的是 13 个 task, 属于独立的三个 scenarios, 你的 coground 实际就是做 人和机器人的 意图->动作->任务 层面的反馈对齐。
我们能不能将我们的 goal 定义为是建立了三个场景的综合： 如 Intruder -> Collaborator 的场景的 bridge 就是人进入到环境中，然后进入到和人协作的环境，而不仅仅停留在机器人的任务被打断，需要恢复上。
用这个作为核心 insights 去再去把我们要做的 topic 迭代、整理，注意我们讨论的目标是得到一个有价值的值得研究的 topic，既不能完全偏离现有研究路线、也不能成为最新工作的整合或者小幅提升的工程工作。

## Response:
9/30/2026, 7:54:34 PM · gpt-6-pro

我会沿“人从进入工作空间，到成为协作伙伴”这条线重新收敛，并核查它与 HRIBench 及传统 HRI 中共同活动、协作加入机制的区别。

关键

> **正在回忆**
>
>
> **梳理HRC基准研究约束与场景角色关系**
>
> 
>
> **梳理研究方向**
>
> 我正在筛选相关理论与近期基准，避免写成泛泛的文献综述。核心将聚焦具身人机协作中的联合行动形成：角色通过互动涌现，并涉及未知角色识别、关系状态转变及单方面发起。
>
> **梳理研究方向**
>
> 
>
> **确定研究框架**
>
> 我正在把三类场景统一为“联合行动如何形成”，而不是简单拼接案例。标题可定为“从共处到协作：具身人机交互中的联合行动形成基准”，重点区分行动执行、反馈对齐与协作关系的生成。
>
> **确定了研究框架**
>
> 
>
> **设计连续场景**
>
> 我正在用一个简单动作贯穿三种关系：机器人整理物品时，人从阻挡、提示逐渐转向共同操作。关键不是固定流程，而是通过反馈形成共享目标、分工、承诺与相互依赖。
>
> **设计了连续场景**
>
> 
>
> **构建研究方案**
>
> 我正在把核心问题收束为：机器人能否在未预设分工时，通过观察、试探、暂停、让渡与回应，逐步形成联合行动，而非只执行既定协作脚本。
> 
> 题目可定为：**《从共处到协作：具身人机交互中的联合行动形成基准》**。
> 
> 三类场景不是固定闯关顺序，而是比较三种关系条件：已有明确分工、依赖环境提示的角色转换，以及通过互动临时形成协作。统一任务可使用“整理物品”：机器人开始独立放置物品；人阻挡、提示位置或固定容器；机器人暂停并判断人是否愿意参与；随后双方通过递交、承接、共同固定或交替放置完成任务。
> 
> 研究重点应从“动作是否完成”转向“关系是否形成”。我会分别评估目标理解、角色识别、共同承诺、让渡行为、时机协调、对失败反馈的适应，以及人在分工中的实际作用。
> 
> 基准设计可加入匹配对照：相同物体、目标和动作能力下，一组提供预先确认的分工，另一组不提供分工，只允许通过互动建立协作。这样能区分单纯执行能力与联合行动形成能力。
> 
> 中心假设是：既有协作能力并不必然带来开放环境中的协作形成；真正困难在于识别参与意图、更新关系状态，并把个体动作组织成相互依赖的共同过程。
>
> **构建了研究方案**
>
> 
>
> 思考了 6m 49s

可以。**你提出的这个 bridge，可以把研究对象从“协作过程中的反馈对齐”，推进到“协作关系本身如何建立”。**这比继续完善 CoGround 的意图表达、反馈识别和动作同步更有独立性。

但我建议把“综合三个 scenarios”视为**场景组织方式**，而不是论文的核心贡献。真正值得研究的是：

> **当一个人进入机器人的工作空间时，双方尚未被预先设定为合作伙伴。机器人能否通过交互，判断并建立一种适当的共同参与关系，将原本的独立作业或空间干扰，转变为共同活动？**

据此，我会把 topic 迭代为：

# 从共处到协作：具身机器人的共同活动建立能力评测
### *From Coexistence to Collaboration: Benchmarking Joint-Action Formation in Embodied Robots*

这里的 **Joint-Action Formation（共同活动建立）**，是我们拟研究的能力。**Intruder → Collaborator 是它最有代表性的测试情境，而不是一条由脚本自动触发的角色切换规则。**

---

## 一、最核心的 insight：协作关系不只是任务的前提，也应该是机器人的交互成果

HRIBench 的 13 个任务按 Instructor、Collaborator、Intruder 三类交互结构组织，角色决定了人的信息贡献、行为形式和需要检验的失效模式。它已经要求机器人推断角色、把握时机、遵守协议和处理干预，因此不能把“识别人现在属于哪个角色”直接作为我们的新意。([arXiv](https://arxiv.org/pdf/2607.13056))

我们的推进应当是：

> **不仅测试机器人能否在某种协作关系下正确行动，还测试这种关系能否通过人机交互被建立起来。**

这包含一个很关键的区别：

| 研究对象 | 核心问题 |
|---|---|
| 在既定交互结构中执行 | 人正在指导、协作或干扰，机器人应该如何行动？ |
| 在交互过程中建立共同活动 | 人进入以后，双方是否要一起做这件事？以什么方式参与？机器人什么时候可以开始依赖人的贡献？ |

这里“既定”指的是**评测任务的组织前提**，不意味着 HRIBench 一定把角色标签直接提供给策略。其脚本本身也包含逐步的角色变量，因此我们不能声称它在表示形式上无法描述角色变化。真正要区别的是**评测问题**，而不是脚本有没有一个切换字段。([arXiv](https://arxiv.org/pdf/2607.13056))

因此，论文最好不要概括成：

> “现有工作是静态角色，我们增加动态角色。”

而应概括成：

> **“现有基准为机器人规定需要应对的交互结构；我们进一步将共同参与关系的建立，作为需要由机器人通过交互完成的任务。”**

---

## 二、把你的 Intruder → Collaborator 具体化：同一个人，怎样从影响任务变成参与任务？

可以继续采用一个很小的日常场景：

> **机器人正在独自把桌面的餐具装入收纳箱。一个人走到桌边，伸手进入机器人正在操作的区域。**

此时，机器人首先需要安全应对，但**安全暂停并不意味着它已经理解了这个人接下来和自己是什么关系**。

这个人可能只是拿走自己的水杯；可能想告诉机器人怎样摆放更合适；也可能愿意扶住收纳箱、接取餐具，与机器人共同完成收纳。

我们关注的正是这几种可能性尚未确定的阶段。

### 一个完整的正向实例

人进入共享区域后，机器人暂停当前动作，避免与人的手发生冲突。随后，人指向箱内一个位置，示意先放盘子。机器人据此调整摆放，并通过动作或简短交流确认接下来的配合方式。人接受扶住箱子的分工，机器人转而连续放入餐具。

在这个过程中：

| 交互阶段 | 在我们拟议场景中的意义 |
|---|---|
| 人进入并影响原有执行 | 对应 Intruder 情境中的安全与干预问题，但尚不能据此推断人的最终参与方式。 |
| 人提供指向、示范或任务信息 | 出现 Instructor 式的信息贡献，用于建立对当前活动及参与方式的共同理解。 |
| 双方接受互补分工并据此行动 | 形成 Collaborator 式的共同执行关系。 |

**关键变化不是机器人从“暂停策略”切换到了“递交策略”，而是原来只有机器人的执行计划，现在出现了双方能够共同依赖的分工。**

例如，机器人接下来把餐具放入箱子，是以“人会继续扶住箱子”为条件；人继续扶箱子，也以“机器人正在按照这个配合方式放置”为条件。双方不再只是同时出现在桌边，而是在组织一个共同活动。

### 同样重要的是：有些 episode 不应进入协作

对方可能只提供一次指导，然后离开；也可能明确表示自己只是取东西，不打算帮忙。

此时，好的机器人应当接受这种边界，继续独立执行，而不是不断邀请、擅自分配任务，或者把对方的短暂伸手理解成长期协作承诺。

所以，我们的目标不是：

> “把所有 Intruder 都变成 Collaborator。”

而是：

> **“在参与意愿、任务条件和交互证据允许时建立协作；不允许时，保持适当的共处或指导关系。”**

这也使三个 scenarios 真正连起来：**它们成为同一活动中可能形成的参与方式，而不是必须依次完成的三幕剧。**

---

## 三、理论基础需要向前移动：从 Common Ground，转向“共同活动如何开始”

CoGround 的 common ground 仍然有用，但它应该退到**机制层**。新 topic 的理论中心，我建议放在 **Engagement 与 Joint Intention／Commitment** 上。

### 1. Engagement：进入空间，不等于进入互动

Sidner 等人的经典 HRI 工作把 engagement 定义为参与者开始、维持和结束彼此连接的过程。它关注的不是单纯“有没有检测到一个人”，而是双方如何建立交互联系。([三菱电机研究院](https://www.merl.com/publications/TR2005-017?utm_source=chatgpt.com))

迁移到我们的 benchmark，得到的原则是：

> **人被机器人看见，不等于人已经成为交互对象；人回应了机器人，也不等于已经同意参与它的任务。**

因此，进入工作空间、接受交流、参与任务，是需要区分的事件。这个区分正好支撑你提出的 bridge：从“人在场并影响执行”，推进到“人参与共同活动”。

### 2. Joint Intention／Commitment：同时行动，不等于共同做事

Cohen 与 Levesque 在 *Teamwork* 中强调，共同行动不能仅由同时发生、甚至彼此协调的个体动作来定义；团队活动涉及参与者围绕共同活动形成特定的目标与意向关系。([SRI](https://www.sri.com/publication/teamwork/?utm_source=chatgpt.com))

相关 HRI 理论进一步讨论了 commitment 如何支持协调：它让参与者能够对彼此的贡献形成较稳定的预期，并据此安排自己的行动。([UCC 研究发现](https://research.ucc.ie/en/publications/joint-commitments-and-group-identification-in-human-robot-interac/?utm_source=chatgpt.com))

在我们的研究中，不必试图测量完整的心理或规范性“承诺”。可以把它收敛为一个行为层面的操作化定义：

> **双方已经对一个局部共同目标及各自贡献形成可观察的接受证据，并开始依据对方的贡献组织自己的行动。**

于是，CoGround 与新 topic 的关系就清楚了：

**CoGround 研究“我们是否对下一步行动理解一致”；新 topic 研究“我们是否已经开始共同做这件事，以及这种共同参与是怎样建立起来的”。**

反馈对齐是建立共同活动的一种机制，但不再是整个研究的终点。

---

## 四、怎样保证它不是“三种角色＋一个状态机”的工程整合？

我认为必须守住下面三个条件。它们决定了这个题目到底是在测一种能力，还是只是在串接任务。

### 第一，角色转换的发生必须依赖交互，而不是依赖预设时间

弱版本是：第十秒人进入，第二十秒人指向物体，第三十秒人开始协作。机器人只需要识别阶段并调用已有策略。

我们应该构造的版本是：

> **人是否继续参与、以什么方式参与，要根据机器人实际做了什么而改变。**

机器人没有注意到对方的协作提议，人可能暂不接手；机器人提出了不合适的分工，人可以修改或拒绝；机器人给出了可理解、可执行的配合方式，人才能据此作出相应贡献。

实验仍然可以控制人的初始目的、可接受的贡献和回应规则，但**不能直接写死“在某个时间点成为 Collaborator”**。

这时，被测对象才不只是角色识别，而包括**建立角色关系的行为能力**。

### 第二，识别到“人愿意帮忙”，还不算完成

即便机器人正确判断对方愿意协作，也不能立即假定对方会执行自己脑中的分工。

例如，人愿意帮忙，但只愿意递餐具；机器人却以为对方会扶箱子。两边都有合作意愿，依然无法形成有效的共同执行。

所以，我们至少要区分：

> **存在合作可能性 → 形成可接受的贡献安排 → 据此开始互补行动。**

这一步使它超出“意图分类＋策略切换”。需要建立的是**具体可执行的参与关系**，而不只是更新一个 `Collaborator` 标签。

### 第三，机器人必须改变“如何完成任务”，而不只是改变反应方式

当人真正加入以后，机器人应根据已经形成的分工重新组织剩余执行。例如，不再独自完成所有递取，而是接收人递来的餐具；或者把自己的双手从固定容器转向连续放置。

**合作关系的建立必须对物理执行产生作用。**

只说“好的，我们一起做”，随后仍然各做各的，不应被视为成功；只完成一次礼貌回应，也不能代替后续的协同执行。

这就是它区别于纯对话 engagement 研究、又保持具身机器人路线的地方。

---

## 五、必须承认已有研究边界，才能把新意放对位置

这个方向有理论根基，但不能声称“第一次研究协作发起”或“第一次研究动态加入”。

传统 HRI 已经有利用人的注视来触发共同装配活动的研究，例如 2024 年的 *Gaze detection as a social cue to initiate natural human-robot collaboration in an assembly task*。因此，仅仅增加一个“人准备好了就启动”的检测器，贡献不足。([Frontiers](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2024.1394379/full))

多智能体研究也早已讨论临时组队与开放团队。ICML 2021 的 *Towards Open Ad Hoc Teamwork Using Graph-based Policy Learning* 就允许不同策略的伙伴在没有预先通知的情况下进入或离开环境。因此，“人中途加入”这个时间设定本身也不是新问题。([arXiv](https://arxiv.org/abs/2006.10412))

与此同时，PARTNR 已经将家庭协作中的空间、时间和异构能力约束纳入评测，分析协作规划与执行问题。我们的工作不需要再建一套更大的家庭任务库去重复这个目标。([arXiv](https://arxiv.org/abs/2411.00081))

**我们需要争取的独立性，是下面这一组问题的组合，而不是某一个组件的首次出现：**

> **在持续的具身任务中，进入者是否参与、如何参与尚未确定；机器人需要通过双向交互建立可执行的共同活动，并区分协作形成失败与已有协作下的执行失败。**

这是一项值得验证的能力定义。其新颖性应由与上述研究的具体比较及实验结果支撑，而不能只靠换一个“role transition”的名称。

---

## 六、第一版怎样做到可收敛，同时能验证一个真正的研究判断？

我建议第一版只固定：

> **一个桌面收纳场景、一人一机器人，重点研究从未建立合作关系到共同执行的这一段过程。**

三类角色用来组织这个过程的不同走向，但不必覆盖所有角色之间的两两转换，也不必第一篇就加入长期个性化、多人加入与退出、复杂社会关系。

### 核心假设只有一条

> **机器人在 Instructor、Collaborator、Intruder 的单独任务中表现良好，不保证它能够在参与关系尚未建立时，与进入者形成协作。共同活动建立是一项可以与单场景执行能力区分开的能力。**

为了检验它，最有价值的对照不是“我们的模型比某个 VLA 高了几点”，而是让**相同基础操作能力**面对三种设置：

| 设置 | 用来回答的问题 |
|---|---|
| 已经建立共同目标和分工 | 机器人有没有完成协作操作的基本能力？ |
| 按预定顺序串接三类情境 | 机器人能否处理更长的任务及阶段切换？ |
| 参与方式需通过交互建立 | 在没有预先达成配合关系时，机器人能否把双方组织成一个可执行的团队？ |

第三种设置相对前两种暴露出的额外困难，才是我们要研究的。

评价初期也不必扩成几十项指标。围绕三个结果就可以展开：**该形成协作时是否形成、不该形成时是否避免误判，以及形成后能否以合理的协调成本完成共同执行。**

“形成”不能由模型自报或一句“好的”来判定，需要看到后续互补动作与相互依赖真正成立；模拟伙伴的回应机制也需要用小规模真人实验验证，避免机器人只是学会了与一个人工状态机对暗号。

还有一个很重要的自检：

> **假如“见人就问一句固定问题，再切换现成策略”已经能够稳定解决整个 benchmark，那么当前设计仍然没有把共同活动建立的困难显露出来。**

这不是说简单基线不能成功，而是提醒我们：论文需要证明它测到的不只是启动口令或模式选择。

---

## 七、整理后的 Topic 可以这样表述

### 研究题目

**从共处到协作：面向动态人类参与的具身机器人共同活动建立评测。**

### 研究对象

**人在机器人持续作业过程中进入共享空间后，双方从尚未建立合作关系，到形成可执行共同活动的过程。**

### 核心问题

> **机器人能否超越对人类指导、协作或干扰的被动响应，通过双向交互确定人的参与方式、形成互补分工，并将原有独立执行转化为共同执行？**

### 可用于 proposal 的初步表述

> 我们以 HRIBench 所区分的 Instructor、Collaborator 与 Intruder 三类交互情境为基础，但不将其仅作为独立的任务类别，而是研究这些参与方式如何在持续的具身活动中被建立和改变。以人进入机器人作业空间、由影响独立执行转向参与共同任务为典型情境，引入 HRI 中 engagement 与 joint intention／commitment 的思想，评测机器人识别参与可能性、建立可接受分工并推进共同执行的能力。研究重点不是预设角色之间的策略切换，而是共同活动能否通过实际交互形成，以及这一能力是否独立于既有的单场景操作与协调能力。

**因此，我建议保留你的“贯通三个 scenarios”作为核心场景 insight，但把论文的科学命题提升为：协作不应该总是 benchmark 预先赋予机器人的条件，也应该成为机器人能够通过交互建立的结果。**

---

**Sources:**

- [HRIBench: Benchmarking Interaction-Centric Human-Robot Collaboration](https://arxiv.org/pdf/2607.13056)
- [Publication - TR2005-017 | Mitsubishi Electric Research Laboratories](https://www.merl.com/publications/TR2005-017?utm_source=chatgpt.com)
- [Teamwork - SRI](https://www.sri.com/publication/teamwork/?utm_source=chatgpt.com)
- [Joint Commitments and Group Identification in Human-Robot Interaction - Discover Research at University College Cork](https://research.ucc.ie/en/publications/joint-commitments-and-group-identification-in-human-robot-interac/?utm_source=chatgpt.com)
- [Frontiers | Gaze detection as a social cue to initiate natural human-robot collaboration in an assembly task](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2024.1394379/full)

## Prompt:
9/30/2026, 10:40:10 PM

也不仅仅是 进入共享空间->协作，这个仅仅是我之前和你说的这三个 scenarios 融合进一个新范式的 bridge 之一，你可以泛化思考一下多种可能的融合方式，我的 insights 所指的就是这样一个高度评估 HRC 的 框架（也可视为是 HRIBench, PARTNER 等研究路线的下一代更加拟真、模拟现实交互），而不仅仅是 engagement 这一种了。

## Response:
9/30/2026, 10:40:18 PM · gpt-6-pro

你指的是三种交互关系在同一任务中如何交织、转变，而不只是从进入空间到协作。我会围绕这一范式梳理融合方式，并核对已有工作的边界。

一个关键区别是：这些角色既可能先后转换，也可能同时交叠；同一次阻挡甚至可能是在纠正机器人。因此，仅增加角色切换还不足以构成新范式。

**你的核心 insight 应当落在“持续共同活动中的交互结构”，而不是某一种 bridge。**上一轮我把它收窄成“协作如何开始”，确实遗漏了指导、共同执行和干预之间的嵌套、并发、相互转化，以及它们对后续协作的持续影响。

更合适的研究定位是：

# 超越独立角色：面向交互结构组合与演化的持续人机协作评测
### *Beyond Isolated Roles: Benchmarking Sustained Human-Robot Collaboration*

> **评测机器人能否在指导、共同执行和干预不断交织的过程中，利用持续的交互上下文，调整双方的行动关系，并推进共同活动。**

这里的“持续”，指的是**同一个活动中不重置任务进展、双方约定和交互历史**，不要求第一版就研究数周的长期学习。

我认为这个定位能够承接 HRIBench、PARTNR 的路线，同时保留一个独立、可检验的科学问题：

> **在三类场景中分别表现良好的机器人，能否把这些局部交互能力组合成真实活动中的持续协作能力？这种组合为什么可能失败？**

下面我把它整理成一个框架，而不是再压缩成某一种局部能力。

---

## 一、首先改变组织原则：三类角色不再是三个互斥的“机器人工作模式”

HRIBench 将任务按 Instructor、Collaborator、Intruder 组织，并通过 scenario scripts 表达角色、时序和协调约束。它已经评价角色推断、同步、协议遵守和干预恢复，所以我们的贡献不能只是“增加一个角色识别器，再切换策略”。([arXiv](https://arxiv.org/html/2607.13056))

**在我们的新框架中，可以把这三个标签重新理解为人类行为对共同活动产生的三种作用：**

| 交互侧面 | 关注人的什么作用？ | 机器人需要处理什么？ |
|---|---|---|
| **指导作用** | 人提供目标、知识、示范或纠正。 | 如何更新任务理解和行动依据。 |
| **共同执行作用** | 人贡献动作，并与机器人形成执行依赖。 | 如何组织互补动作、分工和时序。 |
| **干预作用** | 人改变机器人正在依赖的物理状态、资源或执行条件。 | 如何保证安全，并判断哪些计划需要保留、修改或取消。 |

这是我们对新 benchmark 的组织方式，**不是说 HRIBench 原文已经采用这种非互斥定义**。

这里最重要的一点是：

> **一个人可以同时提供指导、参与执行，又对机器人当前动作造成干预；这些作用不必对应三个不同的人，也不必依次发生。**

例如，人一只手扶住箱子，另一只手指示物品摆放位置，同时手臂占据机器人原定的运动区域。这时机器人需要同时处理指导、协作和空间约束，而不能简单地决定：“这个人现在属于哪一种模式？”

因此，你提出的新范式最好不是 **role switching benchmark**，而是：

> **以交互关系之间的组合、依赖和变化为评测对象的 HRC benchmark。**

---

## 二、三类 scenarios 可以怎样融合？至少存在六种有区别的结构

以下都是拟议的任务结构。为了避免被场景规模分散注意力，可以先统一放在**共同收纳、装箱或准备餐桌**这一类日常活动中。

| 融合方式 | 一个具体例子 | 真正新增的评测问题 |
|---|---|---|
| **接力式转换** | 人先示范收纳规则，随后开始向机器人递物品；也可能从共同执行转为只提供指导。 | 前一阶段形成的规则，能否持续约束后一阶段的协作，而不是切换后重新理解任务？ |
| **协作中的局部嵌套** | 双方正在装箱，人短暂接管一个步骤，纠正机器人摆放方式，再交还执行。 | 机器人能否处理局部指导或接管，同时保留未完成分工、既有进度及新的约束？ |
| **多种作用同时叠加** | 人扶住容器、指示放置位置，同时占用了机器人原定的接近方向。 | 机器人能否同时满足信息理解、同步和安全要求，而不是只激活一个角色策略？ |
| **同一行为因上下文而改变意义** | 人移走一个物体，可能是在完成约定的接手，也可能是在纠正错误，还可能只是取走自己的东西。 | 机器人能否根据可观察的历史理解干预的作用，而不是见到物体被移动就“恢复原状”？ |
| **由机器人主动引发的关系变化** | 机器人发现独立执行不合适，请人示范或协助；人接受、修改或拒绝，机器人据此改变协作方式。 | 后续交互结构能否由双方行动共同产生，而不是全部由人或脚本单向触发？ |
| **暂离与重返中的连续性** | 人暂时停止协作处理别的事情，稍后返回；机器人期间继续推进部分工作。 | 能否重新衔接当前活动，而不重复已完成动作、不沿用失效分工，也不把人返回当作全新任务？ |

你最初提出的 **Intruder → Collaborator**，属于其中的接力式转换；上一轮的 engagement 只是处理这类转换的一种机制。

**真正的框架需要同时容纳：前后转换、局部嵌套、同时发生、历史赋义和双向诱发。**它们不是六个独立子课题，而是同一评测对象--**交互结构**--的不同构造方式。

也不必要求每个 episode 都出现全部三类角色。强行把三类角色塞进所有任务，反而会变成不自然的脚本拼接。

---

## 三、其中最有研究价值的，不是“转换次数更多”，而是交互之间不再相互独立

我认为可以用三个性质，区分你的新范式和简单串接。

### 1. 前一次交互会改变后一次交互的正确处理方式

假设人之前已经明确表示：

> “这只杯子不要装进去，留给我用。”

之后，人又把这只杯子从机器人准备收纳的区域移走。

机器人不能只识别出“物体被人移动”，然后恢复原先摆放；它需要保留之前已经接受的任务更新。

因此，**当前动作的意义取决于先前的交互，而不是只取决于当前画面或当前角色标签。**

这使 benchmark 不再只是把“听指导”和“应对干预”依次放在一起，而是让两者具有因果依赖。

当然，测试必须提供可观察的上下文或允许澄清，不能要求机器人猜测完全不可辨识的心理状态。

### 2. 局部干预，可能服务于整体合作

人挡住机器人正在执行的动作，可能是因为机器人拿错了物品；人暂时拿走共同使用的容器，可能是为了调整它，使后续共同操作更容易。

在这种设置中：

> **“打断当前动作”与“支持共同目标”可以同时成立。**

这意味着不能简单采用：

> 干预结束 → 恢复原计划。

机器人需要判断：原计划是否仍然有效？人的行为是否已经改变了后续应该执行的内容？

这里不是把任何干预都解释成善意帮助，而是**不预先把干预的任务意义写死**。

### 3. 机器人自己的行动会改变接下来需要发生的交互

机器人可以通过表达、求助、让权或调整分工，使后续活动不再沿原来的路径发展。

例如，机器人发现需要一个人持续扶住容器。它可以直接请求协助，也可以选择一个不依赖持续扶持的执行方式。人的回应又会改变机器人后续计划。

所以，新范式不只是：

> 给机器人施加一个变化，看它如何反应。

还包括：

> **机器人能否主动选择、促成或调整一种更合适的协作方式。**

这三个性质共同把研究对象从“多种交互发生过”，推进到“多种交互如何共同组织一个活动”。

---

## 四、理论中心应当转向 Joint Activity 与 Interdependence，而不是只用 Engagement

这里我认为有一个比“动态角色”更稳固的理论抓手：

# **共同活动中的相互依赖：Interdependence in Joint Activity**

### Joint Action 提供评价单位：双方共同组织的活动

《Joint action: bodies and minds moving together》讨论共享表征、预测他人行动，以及整合自己与他人行动的预期效果。这支持我们把评价对象从机器人自己的动作轨迹，推进到双方行动如何共同产生任务结果。([科学直通车](https://www.sciencedirect.com/science/article/abs/pii/S1364661305003566?utm_source=chatgpt.com))

迁移到我们的 framework，就是：

> **不能因为机器人在每个局部片段都“作出了某种合理反应”，就认为整个共同活动被合理地组织起来。**

例如，机器人每次都安全暂停、每次都接受指导，但它不断丢失分工、要求人重复说明，最终把全部协调工作留给人。局部反应可能合格，持续协作仍然很差。

### Coactive Design 提供组织原则：围绕相互依赖，而不是围绕固定自主模式

Johnson 等人的 *Coactive Design* 主张把人和机器人视为相互依赖的队友，并通过可观察性、可预测性和可引导性支持这种依赖，而不是只追求机器人独立完成更多事情。([德尔夫特大学仓库](https://repository.tudelft.nl/record/uuid%3A35cfe91a-bd59-427d-89a9-e2019f9b0c28))

这对你的框架尤其合适。

我们可以把当前的协作关系理解为：**谁掌握必要信息、谁承担哪项贡献、谁正在依赖谁、哪些共享资源限制了下一步行动。**

指导、协作和干预的交织，就是这些关系在变化。例如，机器人原本只需要人提供信息，后来需要人提供物理支持；人原本正在协作，后来暂时不可用，机器人就必须重新组织剩余执行。

因此，核心不是“切换到哪个人类角色”，而是：

> **当前的相互依赖是否仍然成立？如果不成立，双方应当怎样调整活动组织方式？**

### 我们之前选的四种理论，在这里仍然有明确位置

**Common Ground** 支撑跨交互片段保留和更新共同理解；**Mixed Initiative** 支撑双方都能提出、修改或退出某种协作方式；**Mutual Adaptation** 要求人的回应也随机器人行为变化，而不是固定动作回放；**Team Fluency** 则用于检验这些调整是否真的让合作更顺畅。

其中，mutual adaptation 的经典研究已经明确建模人和机器人彼此调整，而非仅由机器人单方面适应人。我们是在将这种思想用于复合交互评测，而不是重新提出相互适应。([卡内基梅隆大学出版物](https://publications.ri.cmu.edu/human-robot-mutual-adaptation-in-collaborative-tasks-models-and-experiments?utm_source=chatgpt.com))

---

## 五、框架可以保持高层，但必须有一个明确的“变化对象”

我建议把初始 framework 收敛为三个部分。

### 第一部分：持续的共同活动，作为任务载体

采用具有可识别目标和物理执行要求的日常活动，例如收纳、装配、整理或物品准备。

活动内部可以接受合理的目标更新，但**不能每进入一种 scenario 就清空双方上下文**。已经完成的动作、有效的指导、接受的分工和仍未履行的贡献，都应继续影响后续执行。

这也意味着，我们维护的是**当前有效的共同任务**，而不是僵硬坚持最初计划。

### 第二部分：交互结构的组合与演化，作为测试变量

在基础任务和操作技能尽量相同的条件下，改变指导、共同执行和干预之间的关系。

变化的不只是“谁先出现”，还包括：

> 一次指导是否影响后续干预的解释；一次纠正是否嵌套在持续合作中；多个交互要求是否同时成立；机器人是否能主动改变下一阶段的协作方式。

这使框架拥有一个统一的研究轴：

> **Interaction Composition and Evolution：交互的组合与演化。**

它足够宽，能覆盖你说的多种 bridge；也足够有边界，因为我们不需要评价所有 HRI 心理、社会或长期关系问题。

### 第三部分：双向响应的伙伴，作为闭环条件

人的后续行为需要能够根据机器人实际表现改变，而不只是按预录时间线执行。

但这不意味着放弃可重复性。可以固定人的初始目的、已知信息、可用能力和回应规则，让具体轨迹根据机器人行为展开。

**可比较的应当是实验条件，不必是完全相同的人类动作轨迹。**

同时，模拟伙伴不能直接读取机器人隐藏计划并自动配合；也不能把“每次都接受机器人请求”当作默认行为。否则测试到的是机器人是否适应一个配合脚本，而不是持续的人机协作。

---

## 六、怎样让它成为研究贡献，而不是 HRIBench 与 PARTNR 的工程组合？

我认为最重要的是把下面这个命题变成可检验的研究假设：

> **局部交互能力不一定能够直接组合为持续协作能力；困难来自跨交互的依赖、同时存在的要求，以及由双方行为共同引起的关系变化。**

这里要特别避免一个混淆：任务更长，本来就可能更难。不能只证明把三类场景串起来后成功率下降，就宣称发现了新的 HRC 能力。

一个有解释力的评测结构可以是：

| 评测条件 | 主要检验什么？ |
|---|---|
| **分开测试各类交互** | 模型是否具备基本的指导理解、协同操作和干预处理能力。 |
| **长度匹配的简单串接** | 性能下降是否主要来自执行更久、操作更多。 |
| **具有跨片段依赖和并发要求的复合活动** | 模型能否保留有效约定、综合多个交互要求，并重组后续协作。 |

在此基础上，再测试**未见过的交互组合**：基础抓取、递交、指导和让行动作都见过，但它们的嵌套方式、历史依赖或触发关系是新的。

这样，泛化不再只是“新物体、新房间、新动作顺序”，而是：

> **熟悉的交互能力，在新的关系结构中是否仍然成立。**

评价也不应以角色分类准确率为中心，而要看实际后果：共同任务有没有推进；已接受的指导和分工是否被正确保留或更新；有没有不必要的停止、重复劳动和人工纠正；安全是否始终成立。

**框架可以允许模块化策略、状态机或基础模型参与，不能预先规定某种架构才算真正协作。**研究价值来自测试揭示的能力差异，而不是人为排斥简单方法。

---

## 七、与现有研究的关系，需要这样表述才稳妥

**HRIBench 提供了角色化交互的诊断基础。**它的脚本已经包含逐步角色和时序约束，因此不能声称其形式上无法表示转换；我们拟补充的是对**交互结构之间的组合、依赖和演化进行系统评测**。([arXiv](https://arxiv.org/html/2607.13056))

**PARTNR 提供了持续家庭任务、分工和执行跟踪的基础。**它明确研究动态协作、伙伴进度、规划与恢复，因此也不能被简单说成“只有固定分工”。我们的侧重点，是将多种交互方式如何影响同一活动，单独作为可控制的评测维度。([arXiv](https://arxiv.org/html/2411.00081v1))

此外，**切换交互模式、双向协商本身已经有相关研究**。CoCo 已研究共处与合作模式之间的切换；ICRA 2026 的 MICoBot 已把双向提议、协商和人机任务分配放入长程协作系统。([arXiv](https://arxiv.org/abs/2206.01775?utm_source=chatgpt.com))

所以，不能把论文的新意写成：

> “我们第一次让机器人动态切换角色、主动求助和接受纠正。”

更有价值、也更可辩护的定位是：

> **我们提出一种评测范式，区分“在各类交互中具备局部能力”与“能够在这些交互相互依赖、重叠并演化时，持续组织共同活动”，并通过受控组合与未见组合测试，分析这种差距。**

这条路线是否足以形成论文贡献，需要后续证明这种差距确实存在、不能仅由任务长度解释，并且与真人协作中的协调成本相关。它不能只靠更复杂的演示场景成立。

---

## 八、最终建议的 Topic：不是“协作形成”，而是“持续协作的组织能力”

我会将你的 insight 最终整理成：

### **研究题目**
**超越独立角色：面向交互结构组合与演化的持续人机协作评测。**

### **核心研究问题**
> **当人的指导、共同执行和干预在同一具身活动中交织、嵌套并相互改变时，机器人能否持续理解并调整双方的行动关系，而不是依赖对孤立交互模式的局部响应？**

### **初步研究表述**
> 现有具身人机协作基准已经分别推进了角色化交互诊断与长程共同任务评测。我们进一步以持续共同活动为评价单位，将指导、共同执行和干预之间的时序、信息与因果依赖作为可控变量，研究机器人在交互结构组合与演化下的协作能力。框架关注机器人能否跨交互片段保留和更新共同理解，在多种交互要求同时成立时协调行动，并通过双向交互调整后续分工与执行方式。通过匹配基础操作难度的对照和未见交互组合测试，检验局部交互能力能否泛化为持续的人机合作。

第一版仍然可以从**一人一机器人、一类日常活动**开始。研究的丰富性来自交互之间的关系，而不是场景数量或参与者数量；多人分别承担指导、执行和资源占用，可以作为同一框架的后续扩展。

**你这个 insight 最有价值的提升是：不再把 HRC benchmark 看成“若干有人参与的任务”，而是把它定义为“对一个共同活动如何在不断变化的人机关系中被组织和维持的评测”。Engagement、CoGround、CoRepair 都能成为其中的局部机制，但任何一个都不再代表整个框架。**

---

**Sources:**

- [HRIBench: Benchmarking Interaction-Centric Human-Robot Collaboration](https://arxiv.org/html/2607.13056)
- [Joint action: bodies and minds moving together - ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1364661305003566?utm_source=chatgpt.com)
- [ Coactive Design  | TU Delft Repository](https://repository.tudelft.nl/record/uuid%3A35cfe91a-bd59-427d-89a9-e2019f9b0c28)
- [Human-robot mutual adaptation in collaborative tasks: Models and experiments - Robotics Institute Carnegie Mellon University](https://publications.ri.cmu.edu/human-robot-mutual-adaptation-in-collaborative-tasks-models-and-experiments?utm_source=chatgpt.com)

## Prompt:
10/3/2026, 5:29:09 PM

给我把当前对话转化为一个markdown文档，你不要做任何缩减或理解，而是原封不动地转换

## Response:
10/3/2026, 5:29:24 PM · gpt-5-6-thinking

我会把当前这段对话按消息顺序完整写入 Markdown，只添加说话者标识用于区分消息，不删减、不总结、不改写正文。



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)