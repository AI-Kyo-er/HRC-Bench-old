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
