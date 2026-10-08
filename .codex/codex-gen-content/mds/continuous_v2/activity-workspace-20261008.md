# 下一版共同活动功能区：实现与资格边界

本轮为progress，上一轮6931b1d发布统一活动首例。完整Goal保持active，formal0，候选72未冻结；三活动六真实情境、可信伙伴、完整持续重组及正式系统比较仍待验收。

## 已完成

新增activity_workspace.py：将操作准备(.16,.04)、交付(.28,.45)、饮品暂放(.02,.45)及四物品个人区分离。位置以真实水平桌面为参考；以碰撞盒测当前朝向下底部偏移及XY占用，逐对象计算放置中心。检查桌边、固定柜体／炉面／酒架、区间距及声明的人手工作区。位置或形状不合法时拒绝，不另选正确目标、不路由策略、不移动物体／机器人，不用任务score。

旧位置别名证据与新布局通过CPU读取已保存XML／首trace，geometry_frame_replay先独立匹配缓存位置再解算。qualify_activity_workspace.py收录三当前／旧案例及init2/4/5参考，共12初态全部qualified_initial_layout_geometry。新布局没有接入活跃runtime，未测移动占用、实际搬运路径、Robot可达性或VLA操作成功；不能当新场景完成证据。下一步接入时须按当前所选物品解算高度，不把某物品的中心高度用于所有物品。

5项新增测试覆盖源世界不改、不同物品高度、桌边／固定物件／区域重叠拒绝及旋转物品后高度随底部改变；全pytest336 passed/2 skipped（session12421 terminal）。qualification46164 terminal12/12；plot75186 terminal，已查看PNG。plot_activity_workspace.py从真实固定物件碰撞边界与新位置绘图，SVG/PNG及来源保存data1/results/task_layout_review_20261008，不是执行视频。仓库results/task_layout_review_20261008已软链；此前doc引用仅data1尚不可通过HTTP访问的问题已修正。

新contract报告底部明确展示下一版几何设计图，保持首例完整Sim视频为结果。实际浏览器12172 terminal：1video/14links、loaded_figures=1、375px/JS0、实际play/seek/Range206、字幕active、同步need及SVG加载通过；路径contract_report_workspace_design_final_20261008.json。无需重复已验证检查，除非新增完整case。Task设计说明已增加实际实现、复现与未验证边界。

## 正在运行，需继续核对同一任务

batch2102624/session22121 live；第一drink子2102625 terminal，已发布120s/7review。第二snack/change_use子2273410 live，最近采样到84模拟秒，24s左右开始有容器和盘子准备、用途改变后选bowl_on_plate；后面反复称准备完整。当前只是中途记录，不认证有食品或动态协作成功，须收完整120s及原audit/video和逐例结果。第三drawer尚未开始。π2095935/session46190仍需本批剩余实验，不能停止。当前另一用户wangjy2251800在GPU0/3，不能动；我们的Human2、π3。批次全部terminal后及时停止不再需要的自有GPU服务并nvidia确认释放。

活跃run_joint_activity、策略、执行器、观测和条件未改。新增几何模块／CPU资格脚本／设计图／报告不在现有模型源路径。所有大文件在data1，未生成smoke。先收齐三例再按同版统一任务、需要与布局验证，不继续做单一提示字段变体。底座及图都不替代原始idea的交互组合、历史依赖／并发、双向重组、匹配对照及未见组合要求。


## 三活动终态、下一版接入与待运行资格

上一轮2618ccf是progress：功能区与12初态几何。当前batch2102624/session22121已terminal exit0，snack2273410、drawer2304239均terminal；π2095935确认UID/cwd/argv及无连接后SIGTERM退出，46190 exit143，nvidia compute-apps为空、四卡约48492–48494MiB空闲。未停止其他用户。别再轮询这些terminal handle或重启旧batch。

三条都120s/60H/30coord/2400control/2401视频帧，NN token、控制及完整视频均verified。VLA drink40/snack16/drawer16，人拒绝4/1/3。21项assistant解释源锚点核对通过。snack用途40触发摆碗到盘，37.2旁移、40.95回来；没有食品填装，只有空碗盘，Robot仅28/32选碗柜顶而实际指接触酒瓶，Human32取瓶被拒。drawer实际24 pause取消未完成放盘请求4并仍持盘，44恢复清盘/请求、R48再次开抽屉至约.160m，H56存奶酪、68.95宏终；目标邻近/底面支撑/释放的初始存储结果成立。不能只用身体y不变否认真实操作参与暂停/恢复；身体离返另列。电话24/24.5与40/58.4说明缺额外过程支持，76人说门关闭实仍开，R还等已完成清盘。承认成果，不认证伙伴拟真或全六覆盖。

新增surface_human_executor将公开表面与当前所选物品中心分开；SurfaceDestinations只给物理宏读，原公开区域不改，原持物buffer和当前所选物品各解高度。真实盒几何测试+连续宏集成检查（几何函数在宏测试中模拟，非真实Sim），只写人持物、速度.2、Robot qpos不变。下一版workspace_contracts明确食品不是空容器、长期收纳与暂放、盘与奶酪；private背景不共享，原CONTRACTS不改。

HumanDecisionSchedule只分配NN调用：已送达私人信息、新Robot表达、实际资源/接触/支撑/操作变化及20s重新考虑，最小4s（由check interval配置）；重复话语/无运动满足不制造反复NN回合，pending新消息保留。理由own_execution_update不等Task完成。无意图/策略/正确动作路由，不读取Task成功。仍两次NN产生私人理解/贡献。scheduler测试禁未来信息/保持副作用边界，Full344/2skip。全部Meta实际Model输入由原审计重建，新增checks与公开对话的计数前缀重放/精确校验NN实际调用时间；新表面目标独立几何重建。旧drawer audit再次verified60H/16VLA。

统一--workspace-method已接入run_joint_activity及run_workspace_joint_activity入口：NeedCards、功能区、SurfaceActor、NN调用时机；source hashes包含四新模块。ref分支不启用NN scheduler，定制提供/收尾位置仅用于固定参照，wine在serving_ready提供而非客用暂放区，收尾清盘。Journal无append API问题已在运行前修为list+flush；未让错误进入GPU实验。wrapper --help需要output的旧限制未修改，直接base --help通过。核心编译和344 tests通过，新的完整Sim资格尚待启动。

contract报告已3视频/27links+1设计图，71276终态浏览器通过；main68videos、67完整开发episodes/18000blocks/158400实际7D、uniqueIDs/source边界通过（44711terminal）。main最终浏览器93416待收，之后不重复已通过项。报告区分初始存储正例与完整Goal；所有raw不改，无smoke。TASK源代码和PrivateAgenda两次预算与旧不同，不能作单因素改善因果。

下一资格条件已运行前固定experiments/workspace_reference_20261008：snack/drink/drawer init2 seed91/92/93、120s、初持、固定人、task_only原生VLA，Robot准备期参考hold和收尾Cartesian清场分开。不使用reference-vla-instruction免其覆盖参考准备调度，也不将完整活动长指令塞进200token限制。脚本run_workspace_reference_batch.sh固定GPU2，π按需GPU3；起前必须nvidia再查。全部终态video/audit/process核查后，才进入同一方法跨活动神经验证和两个系统正式比较。Goal全要求保持active，formal0/candidate72未冻结。

若内部分析出现海量重复或不存在的变量名，不按那些内容写代码。只信本工作树、真实进程和输出；短分析立即工具，避免空转和单字段变体。


下一版与整批提交aeda078。main最终93416已收：68videos/648links、play/seek/Range206/字幕/375px/JS0全部通过，不再poll；contract3videos/27links+1图通过。344/2skip已收80353。新参考已实际启动：π GPU3/session46355/PID2366870（不是已terminal的旧2095935），port8766听服务；batch GPU2/session13767/父2367442/第一子2367443，NN Human0，第一snack已推进32模拟秒且24秒选择接收。首receipt实际surface[.16,.04,.9]→bowl body[.16,.04,.9004115578211194]，读取时再核对精确原值，不以本行浮点文字替实际记录。实际新模块已进入运行，无模型源编辑。仍需收三条终态、完整视频及参考成功/失败，结束后及时停止不再需要的自有π并nvidia验证；不停止活跃新任务。旧batch/session22121与旧π46190均terminal，勿混。


## 新布局三参考已全部核查（2026-10-08）

前轮aeda078/77205ab/950a259为progress。实际参考batch2367442/session13767现terminal exit0，三个子均terminal；π2366870因无活动需要SIGTERM退出，46355 exit143，nvidia compute-apps为空、四卡显存释放确认。不得重启原三条或继续poll旧handle。

workspace_snack/drink/drawer_reference三条均完整120s、input/video verified，人NN0；点心/抽屉reference_complete True、饮品False，后者Human14.35s宏完成并提供wine到(.16,.04)，208VLA调用仍未上架、瓶终还在提供处而碗盘被扰动。不能将此基本操作失败归动态Human/HRC。点心准备支撑10.2、macro14.35，Robot原生21.65后接收24，39.95起物理匹配、macro42.2，链成立；参考Cart清场接触1.15s不归π协调，不能安全认证。

新build_workspace_reference_report及index/status展示三完整视频与固定控制来源，首browser12565终态3videos/22links/375px/JS0/播放拖动/Range206/字幕通过。添加控制协议链接后报告84950待收；主入口71videos、loader70complete/18720blocks/165600actual7D、source/uniqueID通过（51082terminal）。正式0/未冻结split，原失败保留。

已预先定义单条workspace_drink_provision_control_20261008：同init2/seed92/120s/初持/同新方法/原生task_only，仅固定参考提供位置改现有wine_bottle_1_personal(-.20,-.02)，不能把差异当单样本因果证明，π随机噪声未逐调用配对。新CLI reference-drink-provision仅workspace固定饮品可用，neural/source错误模式直接argparse exit2验证、无临时目录生成。没有改NNHuman选位置。入口run_workspace_drink_provision_control.sh；尚未启动时需nvidia确认、按需重启π。代码Full344/2skip（87922terminal），compile/diff通过，无smoke。下一步收位置控制后，启动同版三活动生成式Human、实际scheduler调用和几何审计；未验证NN方法有效性，不以参考2/3替完整Goal。


ab85006已提交三参考报告与独立位置控制。π按新控制需要重启：GPU3/session15826/PID2377653，8766已listen；控制实际启动GPU2/session97129，需查其当前子PID，固定人/NN0，不把其动作当动态Policy。来源和配置启动前冻结。全部三原参考13767及旧π46355终态，勿混；前三视频均核验，其中2成功/1失败。新增报告control链接后需最终browser及主71视频验证，已知前browser3/22通过、help非法参数exit2验证未生成/tmp目录。新控制无重跑旧结果，仍需完整120s后audit/process/video，模型不再需要时及时停自有新服务并nvidia查释放。正式0，生成式方法效果仍待Sim验证。

## 提供位置控制终态与六情境开发批预定

前轮ed5287d之后控制workspace_drink_provision_control_20261008已terminal exit0：人NN0、200 VLA调用、2400控制、拒绝0，16.3秒放置宏完成，仍未上架；audit/process及2401帧20Hz完整视频核验通过。π2377653已SIGTERM、session15826 exit143；本轮nvidia再次确认四卡约48492–48494MiB空闲、compute-apps为空。不要继续poll旧控制和服务或重跑原条件。

build_workspace_reference_report现以独立控制角色增加第四视频，原conditions三条不变；browser49346 terminal4videos/29links、播放拖动/字幕/Range206/375px/JS0通过。主报告已72视频（含旧partial）；全量开发loader71完整episodes、18960blocks、168000actual actions、uniqueID/source边界通过，3282 exit0。正式样本仍0。

预定experiments/workspace_dynamic_20261008六条（init2、seed101–106、120s、同版workspace-method、生成式PrivateAgenda人、symbolic协调+真实π0.5）。覆盖六情境配置而非实际行为，不能记全部六覆盖；目前尚未启动，status verified0。run_workspace_dynamic_batch每条结束审计/process/video后更新HTML，不自动覆盖或重试。报告修正inspection.js路径生成顺序，pending browser用系统Python3.12已通过0videos/9links；缓存浏览器greenlet针对3.12，不要用Sim Python3.11。整套pytest使用schema-decoding PYTHONPATH和LIBERO_CONFIG_PATH后344 passed/2 skipped（30212terminal）；首次少环境变量2失败不属于代码回归，仍留工具记录。

下一步新检查GPU再启动π3及开发批2，记录新PID/handle并收实际NN输入、scheduler及六例行为；大文件均data1。不将两条饮品操作失败归HRC缺口，也不做更多单一位置微调。未冻结候选72、多系统正式评测与全Goal仍active。

63b76de已提交协议／六条条件／报告生成及控制终态。新π服务GPU3/PID2440833/session8693，严格权重加载且8766监听；新batch GPU2/PID2441354/session49178，首子2441355（snack/change_use）已加载Qwen并保存scene/task/situation/workspace。21:04:44子仍Rl、GPU2活跃；尚未产出首条完整NN决策，不认证行为。不要把观察等待当terminal或重启。旧GPU全部释放后按需新启，不停止仍被该batch需要的π。

主入口browser21025 terminal72videos/682links，播放／拖动／字幕／375px／Range206等通过。README和整体DESIGN更新到新方法，明确参考四条终态、生成式开发配置未验收及原idea组合仍待做。发现run_joint_activity末尾单run HTML仍有旧“每2秒”静态文案；活跃源码不改，结束后需改为真实cadence，当前新批统一页与PROTOCOL已正确写4秒检查／20秒重考虑。

fce721d后首例0秒决策已实际产出：agenda375tokens、贡献1181tokens；source含table_surface_positions及几何执行语义，current_need明确食品入碗并供取用。Human选择relocate cream_cheese→cream_cheese__in__bowl，0秒公开“I will place the cream cheese into the bowl.”，3.95秒实际pick_approach/held None（已先buffer自己的碗，不是食品已装完）。初始schedule仅initial_observation，实际记录与NN对应。

首Robot0秒也选execute put cream cheese in bowl，并说同一句自己会装填；reason明确据Human的“I will”进行操作。这是早期重复贡献／自愿声明被理解成Robot指令的问题线索，不是完整失败结论。完整episode需核对并发执行、支撑和后续双方反馈，不改活跃模型或预设本例失败。Robot实际public_input顶层含time/robot_task/human_task/dialogue/state/history/current_goal/self_execution/available操作/observed_world，递归未发现私有context/background/agenda/memory字段；这只是本刻输入边界检查，不替代终态独立审计。

## 首例运行中0–20秒证据：事实误判与提前转贡献

本turn前轮74d766d是progress。本轮先re-poll49178且ps确认父2441354/子2441355/π2440833 live，无重启或改运行源码。已核对Human4秒输出：原请求0仍pick_approach、completed=[]、碗supported_items=[]，却生成“Cream cheese placed in bowl”并选搬碗；回执request1明确superseded_motion_request_id0。Robot4改hold并等搬碗。8秒重复搬碗回执continues_motion_request_id1，**不重启**该同目标运动，不应把每次重复选择都计无效劳动。20秒碗已释放/phaseidle，食品支持仍为空，Human宣称点心完成；Robot仍等搬碗。agenda4合法且未失效fallback，仍需确认食品入碗，贡献层先自报完成；agenda8也开始记食品入碗。输入含所需测量，不能归漏观测或低层拒绝。

保存35条原始记录快照于data1/results/workspace_online_review_20261008/snack_through_20s.json；results/workspace_online_review_20261008软链已建。每条原JSONL路径/非空索引/原记录文本SHA，保存后重读逐条匹配；活跃文件继续追加不影响前缀。它不是终态review/audit或正式成绩，未判断整例失败，也尚未到用途通知。OBSERVATION_NOTES.md解释前缀，统一新批页新增链接并把旧BATCH_REVIEW明确为此前结果；browser0videos/10links通过。活跃源码保持，source审计应无变化。批全部terminal后及时回收不需要的自有服务并nvidia核对；目前仍被本批需要。

c9ae078已提交0–20秒前缀审阅。后来已到43.95秒：Human40按39.5通知选择碗放盘，Robot40hold并等同一贡献。32/36无变化scheduleFalse，不能当生成wait。发现继承activity_private_context通知不全是生活事实：snack change_use明确建议plate作托盘/bowl放plate，drink部分也指定柜顶；**不能据此认证自主推导方案**。PROTOCOL/OBSERVATION_NOTES已纠正解释，原source/通知未改。另保存7条通知及40秒源记录，snack_change_cue_40s.json，重读哈希匹配通过；仍为running prefix而非终态。全部6本版收齐后统一审阅，正式条件需区分纯生活需要与外部具体建议，不能迭代单字段后宣称能力改善。
