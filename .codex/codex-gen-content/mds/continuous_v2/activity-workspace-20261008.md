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
