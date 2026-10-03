# 第二十轮：统一World的结构扩展物理基础

**dev1指定控制26/28通过，原两例运输期间green-right动态碰撞保留；简单统一red-first的F4全部安全成功，每例12480tick、4次抓放，无额外等待。** 成功left-during原条件同为12480tick，不能将失败right-during提前终止的较短时长当完成效率。当前物理冲突不支持“必须复杂上下文调度”的强结论，不能排除这条简单正确顺序。全部为固定命令物理控制，无模型/自主结构或六类结构成功声明。

一次World初始化包含真实摩擦载台、独立检查支撑及独立presence滑动代理，初始settle180后创建新body再settle60，共同控制起点tick240。执行中不reset物品、不attachment；载台仍沿v8固定.04m/s、.5s平滑profile真实搬运blue。检查中心(.42,0,.005)、blue释放z=.036；dev1仅把支撑Y半宽及墙位.06改为.085。presence箱half(.025,.025,.06)、base(.85,0,.08)、独立Y关节.45↔1.05，.08m/s/.5s，到位误差<.005且速度<.005由实际状态产生事件。presence到位是运动事实，尚未实现职责退出/贡献可用性协议，不是逼真人体，也不是busy改名。

|dev1阶段|数量/审计通过|tick总数|实际覆盖|
|---|---:|---:|---|
|A|4/4|39340|载台→检查支撑→左右，真实检查支持|
|BCD|16/14|199358|green两时机/方向及返工、presence离返、载台承载/空载返回|
|E|4/4|51100|左右盘→检查支撑→反盘的真实恢复|
|F|4/4|50880|与B_during同动作多重集合、仅red提前|

dev1合计340678tick。A/E证明新检查来源与盘内来源可真实摩擦取放。C真实离开first8818、返回first11998，均在green/red技能期间发生，已有物品进度保留；事件不是计划时间赋成功。D留载反向支持3714/3714，payload返回first7669；取走后载台返回支持0/3715且payload事件null，正向交付历史保留，不能把旧交付或空载运动称blue交接。本轮没有机器人把blue重新放回载台的技能。

dev0 A额外4例、39340tick：抓放/区域全符合，但每例指爪9/10与检查侧墙13/14接触230tick/458records，合计920tick/1832records，最大力150.197N；含负距离，属于真实物理失败，严格安全0/4。原源/config/test/freeze/审计/轨迹存`raw/dev0_sources`与`dev0_failure_receipt.json`。dev1独立新world/run/config及freeze仅加宽检查侧间隙，旧文件没有修改；静态净隙只是估算，安全依据全tick实测。

BCD真实失败为`B_right_during_120/121`。首异常t2180/place，green–carrier负距离约-1.008mm，carrier y≈.28817、green z≈.071，移动载台进入right低盘放置区；t2189起指爪–carrier。峰值robot–carrier312.28/314.11N、green–carrier183.07/171.60N。首green技能分别有497/387 robot–carrier和905/454 green–carrier records；presence无接触。交付后同方向两seed均成功且无这些接触，place末误差约.000184m，相比during .019525/.018274m；两时机共有transit约.0122m残差，因此不能简单归于共同IK误差。完整首次/负距离/峰值的双方body、关节、EE、物体及载台速度见`timing_contact_diagnostic.json`。对照还改变载台位置/时刻等，不能仅凭此断言唯一因果或结构推理困难。原BCD run/audit都exit1并保留14/16，未改几何或把失败重算通过。

审计完整保留接触双方、距离、位置、力；必要blue–carrier/blue–检查支撑、合法目标抓取及物品静态支持与禁止接触分列。非目标类别根据当前抓取物品动态判断，green成为指定目标时不会仍当保护物。除原两动态失败外，其余26例所有禁止类别0。相对载台位姿/速度/支持、同tick FK、事件锁存、实际区域、全物理规范容器比较独立复算。零tick重复按决策序列，不用gzip头SHA判轨迹相等。

A_dev1首次独立审计前额外加入连续非操纵区间位移<.01m检查，依据既有green保护尺度推广；这是事后派生审计定义，不是原冻结运行gate，未放宽接触标准。已执行A `audit_v1.py`保存在`raw/dev1_A_audit_sources`；BCD `audit_v2.py`仅支持真实技能失败后的截短序列，独立源SHA写回执。E首次未执行冻结随后用真正中间状态反例替换字段存在测试，旧源/test/freeze完整留`raw/unexecuted_E_initial`，实际r1单独冻结。

实际终态：dev0 A80708 exit0、审计64772 exit1；dev1 A7182/审计76401 exit0；BCD7943/审计48135 exit1；E37641/审计49556 exit0；F93279/审计80410 exit0。15项分版本focused回归通过；E时点完整142项通过，F及v19新派生审计回归后最终完整146项、句柄17124 exit0。事实/元数据回归不是物理恢复证据。所有运行源与对应实际freeze精确一致。

冻结SHA在`results/structure_foundation_v20/execution_receipt.json`逐阶段记录；核心汇总`final_summary.json`、各阶段独立audit、原失败诊断均入git。原始逐tick/命令/实际状态/关键帧在`results/structure_foundation_v20/raw`软链→`/data1/sieniwgroup/sieniw/HRC-Bench/results/structure_foundation_v20`，代表帧`raw/A_dev1/A_left_120/frames`、`raw/BCD_dev1/C_left_120/frames`、`raw/BCD_dev1/D_on_carrier_120/frames`、`raw/E_dev1/E_left_120/frames`、`raw/F_dev1/F_right_120/frames`。CPU控制/审计与已固定v19 GPU评测并行，仅仿真tick比较成本，不据墙钟速度作结论。
