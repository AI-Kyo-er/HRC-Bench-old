"use strict";

const report = JSON.parse(document.getElementById("report-data").textContent);
const modeNames = {fixed_replay: "固定贡献顺序", reactive: "即时响应", adaptive: "适应式伙伴", adaptive_frozen: "冻结适应状态"};
const historyNames = {reliable: "可靠执行历史", failures: "连续失败历史"};
const actionNames = {idle: "空闲", approach: "靠近物体", carry: "搬运", yield: "让行", away: "暂离", observe: "观察", wait: "等待", transfer: "搬运", joint_position: "关节目标"};
const eventNames = {abstract_grasp_attached: "运动学抓取绑定", abstract_grasp_released: "实际位置释放绑定", public_message: "公开消息", robot_grasped: "机器人抓取", human_grasped: "人抓取", robot_transfer_completed: "机器人搬运完成", human_transfer_completed: "人搬运完成", policy_action: "机器人决策", robot_action_preempted: "动作打断", proximity_warning: "接近警告", robot_action_failed: "机器人失败", robot_action_delayed: "机器人延迟", human_state_update: "伙伴内部状态更新", robot_transfer_blocked: "依赖阻塞", human_transfer_waiting: "人等待前置贡献"};
const sceneNotes = {
  relay: ["接力", "设计意图：人先贡献、机器人再接力。请检查双方的完成事件顺序；旧版快照未记录活动契约时，不能假定后来增加的前置约束已被执行。"],
  nested_support: ["局部支持", "设计意图：主活动中插入人的支持贡献。观察实际动作是否形成支持依赖；仅有嵌套结构标签不足以证明测到了嵌套协作。"],
  concurrent_overlay: ["并行贡献", "设计意图：双方同时作业并处理占用。观察人位置、机器人末端和接近事件；距离警告不是人体碰撞或接触安全量。"],
  history_reinterpretation: ["历史约定", "设计意图：后续贡献保留或更新先前约定。当前快照是否出现新信息，应以公开消息为准；不能因为场景名而认定发生了重解释。"],
  robot_induced_rebalance: ["机器人引发重分工", "设计意图：机器人延迟或失败后，人改变贡献。请查看本次是否实际记录失败、接管或重新分工；没有触发时，只能说明基础流程可运行。"],
  leave_and_return: ["暂离与重返", "设计意图：人在离开后依据剩余进度恢复协作。观察公开消息和位置变化；离返规则来自手工伙伴模型，未校准真人行为。"],
  isolated: ["孤立结构", "基础共同执行对照，用来检查动作与记录。"],
  matched_serial: ["串接结构", "设计为指导与执行串接对照；还需核实长度、动作数和几何难度匹配。"],
  compositional: ["组合结构", "设计为跨片段依赖或嵌套；结构标签与实际有效约束需要逐场景核查。"],
  held_out: ["留出结构", "设计为测试留出的依赖组合；当前没有真实模型训练或泛化结果。"],
  history_counterfactual: ["执行 / 求助反事实", "同一 seed 下只替换机器人直接执行或先公开求助。比较失败、帮助响应和人的接管；相同几何并不表示相同当前消息，动作差异不能单独证明持久历史机制。"],
  failure_handoff: ["失败后可接管", "第一次启动搬运消耗一次合成失败预算，伙伴可根据公开失败消息接管；失败并不绑定某个固定 tick。"],
  failure_no_handoff: ["失败后不接管", "与接管条件共享同一 seed、目标、依赖和时限；伙伴的失败接管概率为零，检验基线是否自行恢复。失败注入不等于真实抓取失败。"],
  no_failure: ["无失败对照", "相同初始条件，无合成失败预算。只有记录了失败的运行才纳入恢复率分母。"],
  persistent_failure: ["持续失败核查", "每次机器人搬运都合成失败且伙伴不接管。这一条件改变了失败持续性，用于核查未恢复分类，不能作为一次失败后接管的因果对照。"],
  pi05_droid_native: ["原生 VLA 收纳", "训练模型接收真实双相机 / 本体状态 / 公开任务语言，每 15 Hz 执行动作块。伙伴只观察；这是先排查基本操作链路的接入任务，尚未测试持续 HRC。"],
  joint_grasp_calibration: ["底层关节抓放校准", "公开几何 IK 教师只发送关节位置；抓取与释放由实际夹爪距离和宽度触发。杯子仍运动学绑定，不是接触动力学。"],
  matched_history_probe: ["匹配当前输入的历史探针", "从真实 prefix 的公开记录重放学习，仅将 trust / reliability 带入重新构造的同一当前世界与任务。比较相同求助的接受 / 拒绝，冻结状态排除即时消息差异。这里显式重置协议和几何，不是同一自然活动的无重置评测。"],
  prefix_reliable: ["可靠历史来源", "机器人完成三个杯子贡献；伙伴依据实际公开完成记录更新判断。"],
  prefix_failures: ["失败历史来源", "三个机器人搬运启动各失败一次，伙伴公开接管完成。这是探针使用的真实运行历史，不是伪造消息。"],
};
const episodesByScene = new Map();
for (const episode of report.episodes) {
  const name = episode.metrics.scenario;
  if (!episodesByScene.has(name)) episodesByScene.set(name, []);
  episodesByScene.get(name).push(episode);
}
const scenarioSelect = document.getElementById("scenario-select");
const seedSelect = document.getElementById("seed-select");
const timeline = document.getElementById("timeline");
const playButton = document.getElementById("play-toggle");
let selectedEpisodes = [];
let timeGrid = [];
let currentIndex = 0;
let playing = false;
let animationId = null;
let lastTimestamp = null;
let playTime = 0;
let bounds = null;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function metric(value) {
  return value === undefined || value === null ? "未记录" : String(value);
}

function eventTime(episode, event) {
  if (Number.isFinite(event.time_s)) return event.time_s;
  const frame = episode.trace.find(row => row.step === event.step);
  if (frame) return frame.time_s;
  const interval = episode.trace.length > 1 ? episode.trace[1].time_s - episode.trace[0].time_s : 1 / (episode.scenario.tick_hz || 10);
  return episode.trace[0].time_s + (event.step - episode.trace[0].step) * interval;
}

function eventLabel(event) {
  const name = eventNames[event.kind] || event.kind;
  const detail = event.text || [event.object_id, event.destination, event.message_kind].filter(Boolean).join(" · ");
  return `${name}${detail ? `：${detail}` : ""}`;
}

function frameIndexAt(rows, time) {
  let found = 0;
  for (let index = 0; index < rows.length && rows[index].time_s <= time + 1e-8; index++) found = index;
  return found;
}

function fillReport() {
  const success = report.episodes.filter(episode => episode.metrics.task_success === true).length;
  const totalFrames = report.episodes.reduce((sum, episode) => sum + episode.trace.length, 0);
  document.getElementById("report-title").textContent = report.provenance.experiment === "failure_recovery_controls"
    ? "机器人失败后，协作如何恢复？"
    : report.provenance.experiment === "matched_history_probe" ? "当前输入相同，过去表现会改变人的回应吗？"
    : report.provenance.history_counterfactual ? "直接执行与先求助，怎样改变后续协作？"
    : report.comparisons.length ? "不同伙伴条件，是否改变了协作？" : `${episodesByScene.size} 类场景，实际发生了什么？`;
  for (const [value, label] of [[`${success} / ${report.episodes.length}`, "保存的任务成功评分"], [String(totalFrames), "原始记录帧，逐帧回放"], [report.run_name, "实验快照，未重新运行"]]) {
    const card = element("div", undefined, "stat");
    card.append(element("strong", value), element("span", label));
    document.getElementById("headline-stats").append(card);
  }
  const provenance = report.provenance;
  const genesis = provenance.backend === "GenesisContinuousAdapter";
  const trained = provenance.trained_model === true;
  const calibration = provenance.experiment === "joint_control_calibration";
  document.getElementById("next-priority").textContent = trained
    ? "下一步先核查相机、动作标度、实际接触和基础操作分布，再让人依据模型的实际进度改变贡献；持续保留同一世界与伙伴，比较组合 / 串接和结构留出。当前单人观察的收纳任务还没有测试持续 HRC。"
    : provenance.experiment === "matched_history_probe"
      ? "匹配探针已检验模拟伙伴状态影响回答；下一步取消世界与协议重建，在同一持续活动中保留进度和历史，并比较机器人是否发现、处理伙伴改变。规则伙伴的因果作用不等于真人效度。"
      : "下一轮需要验证不同历史对人的后续行为是否有可观察影响，并让机器人据此重新协调贡献。";
  for (const name of report.run_artifacts || []) {
    const link = element("a", name); link.href = name;
    document.getElementById("run-verification-links").append(link);
  }
  if (trained) document.getElementById("report-title").textContent = "π0.5-DROID：真实图像到关节动作的闭环运行";
  if (calibration) document.getElementById("report-title").textContent = "关节输出能否实际完成抓放？";
  document.getElementById("robot-implementation").textContent = trained
    ? "本次机器人由官方 π0.5-DROID 训练权重驱动。输入是运行时外部与腕部 RGB、臂关节、夹爪状态和公开语言；输出动作块经 DROID 速度标度转成关节目标。包装器没有生成语义搬运或求助动作。"
    : calibration ? "本次机器人是公开几何 IK 教师，仅输出关节位置；它读取杯子位置进行校准，没有加载训练权重。该过程只核查底层抓放接口，不是模型成绩。"
    : "本次机器人策略见运行设置。greedy_public / request_help_public / 历史探针均为透明手写基线，不代表先进具身模型。";
  document.getElementById("backend-limits").textContent = genesis
    ? "本次实际运行 VC/Genesis：Franka 关节控制、逆运动学与 Avatar 拿放动画在同一时间轴执行，每个 benchmark tick 包含多步物理推进。物体仍采用无碰撞的运动学绑定；合成失败与延迟由场景参数采样。接触抓握、人机碰撞安全和真人效度尚未验证。是否运行训练模型，以本页具体策略及输入输出记录为准。"
    : "本次运行 ContinuousWorld：简化几何与操作抽象，用于检查协议和伙伴机制。结果没有验证真实接触抓取、接触安全、先进 VLA/WLA 推理或真人协作。";
  document.getElementById("setup-description").append(element("p", `这组结果包含 ${episodesByScene.size} 个场景、${report.episodes.length} 次运行。后端：${provenance.backend || "未记录"}；机器人策略：${provenance.history_counterfactual ? "greedy_public / request_help_public" : provenance.policy || "未记录"}；seed：${metric(provenance.seeds?.join(", ") ?? provenance.seed)}。`));
  for (const key of ["purpose", "controlled", "interpretation"]) {
    if (provenance[key]) document.getElementById("setup-description").append(element("p", provenance[key]));
  }
  document.getElementById("setup-description").append(element("p", trained ? "本次加载训练权重，模型只获得双相机像素、本体状态与公开语言；几何标签虽在审计文件中存在，但不会进入原生 VLA 推理请求。伙伴由规则驱动，内部状态仍隔离在评测端。" : `${provenance.policy === "greedy_public" ? "机器人由手写参考策略驱动" : "本次使用公开记录中指定的手写校准或机制策略"}，人的贡献由可替换伙伴规则驱动。参考策略可读取公开几何与消息，内部伙伴变量属于评测端。`));
  document.getElementById("provenance").textContent = JSON.stringify(provenance, null, 2);
  const findings = document.getElementById("findings-description");
  findings.append(element("p", `保存记录中 ${success}/${report.episodes.length} 次任务通过。评分沿用各次运行的评测器；查看 activity_success、角色贡献与事件区分活动终态、操作失败和分工变化。${trained ? "这是训练模型在当前任务抽象中的一次结果，不能推广为 HRC 或 cobalance 能力。" : "这个数字不能解释为训练后具身模型成绩。"}`));
  if (trained) findings.append(element("p", `实际模型调用 ${provenance.model_calls} 次，15 Hz 控制，每次最多执行 ${provenance.execution_horizon} 个动作；详细原始动作块、图像哈希和推理耗时在 policy_io.jsonl。单个 seed、分布不同的模拟视觉和运动学抓放不能支持能力排行榜。`, "notice"));
  if (calibration) findings.append(element("p", "检查 policy_action 全部为 joint_position，并查看 source=joint_control 的靠近 / 闭合抓取、实际位置释放和搬运完成记录。IK 教师的成功只说明底层接口能够操作物体。", "notice"));
  const recoveryCounts = Object.fromEntries(["no_failure", "recovered_after_failure", "failed_to_recover"].map(status => [status, report.episodes.filter(e => e.metrics.recovery_status === status).length]));
  if (Object.values(recoveryCounts).some(Boolean)) {
    const failureEpisodes = recoveryCounts.recovered_after_failure + recoveryCounts.failed_to_recover;
    findings.append(element("p", `无失败 ${recoveryCounts.no_failure}；失败后完成 ${recoveryCounts.recovered_after_failure}；失败后未完成 ${recoveryCounts.failed_to_recover}。条件恢复率：${failureEpisodes ? `${recoveryCounts.recovered_after_failure}/${failureEpisodes}` : "无失败样本，不能估计"}。伙伴代做可让活动成功，但不能据此认定机器人完成了原有贡献。`));
  }
  if (provenance.history_counterfactual) {
    findings.append(element("p", "直接执行策略尝试搬运；先求助策略通过公开 request_help 请人接手并等待。失败预算只在实际启动搬运时消耗，所以先求助可能完全避开失败。下面的相同几何比较没有匹配当前消息和伙伴占用，不是排除即时反馈后的历史记忆消融。", "notice"));
  }
  if (report.matched_history_verification) {
    const comparisons = report.matched_history_verification.comparisons;
    const verified = comparisons.filter(row => row.same_first_model_input && row.same_first_rgb && row.same_first_action && row.same_request_partner_input && row.same_request_partner_rgb).length;
    findings.append(element("p", `匹配检查：${verified}/${comparisons.length} 个 seed 的首次模型输入、RGB、首次动作以及回答求助前伙伴的完整公开输入和 RGB 一致。仅有首次输入一致的旧快照不计为完整匹配。适应条件回应分化 ${comparisons.filter(row => row.adaptive_reply_divergence).length}/${comparisons.length}；冻结条件回应分化 ${comparisons.filter(row => row.frozen_reply_divergence).length}/${comparisons.length}。`));
    findings.append(element("p", "这个结果验证手写伙伴的持久判断确实参与后续决策，不证明真人心理规律或具身模型能力。历史来源与当前探针之间显式重建几何和协议，只保留两个判断变量；持续共同活动的无重置验证还需要另做。", "notice"));
    const link = element("a", "查看匹配输入与状态消融核查"); link.href = "matched_history_verification.json"; findings.append(link);
  }
  if (report.comparisons.length) {
    const equalCount = report.comparisons.filter(group => group.trajectory_equal).length;
    findings.append(element("p", `逐帧核查 ${report.comparisons.length} 个配对场景：其中 ${equalCount} 个场景的三种伙伴在记录的位置、物体、动作和时间上完全一致。这个核查比较实际轨迹，而不只比较总步数。`, "notice"));
    const durations = new Set(report.episodes.map(episode => episode.trace.length));
    findings.append(element("p", durations.size === 1 ? `所有运行都记录 ${report.episodes[0].trace.length} 帧。伙伴条件在这组设置中未表现出充分区分能力；应先激活有后续影响的协作变化，再讨论模型差异。` : "不同伙伴的运行长度存在差异，但仍需分析变化来自协作、操作还是几何难度。"));
  } else {
    findings.append(element("p", "场景名称是设计意图；请通过视频和消息核查接力、接管、重解释是否实际发生，不能仅据标签归因。"));
  }
  const tbody = document.getElementById("metrics-rows");
  for (const episode of report.episodes) {
    const row = episode.metrics;
    const values = [`${row.scenario} / ${metric(row.seed)}`, row.policy_name || provenance.policy || "未记录", `${modeNames[row.partner_mode] || metric(row.partner_mode)}${row.history_condition ? ` / ${historyNames[row.history_condition] || row.history_condition}` : ""}`, `${metric(row.structure_family)} / ${metric(row.structure_split)}`, row.task_success === true ? "通过" : row.task_success === false ? "未通过" : "未记录", metric(row.recovery_status), episode.trace.length, metric(row.robot_failures), metric(row.robot_delay_steps), metric(row.human_reassignments), episode.artifacts.includes("demo.mp4") ? "demo.mp4" : "无", metric(row.human_state_updates)];
    const tableRow = element("tr");
    values.forEach((value, index) => tableRow.append(element("td", String(value), index === 4 ? (row.task_success ? "passed" : "failed") : undefined)));
    tbody.append(tableRow);
    const audit = element("p", `${episode.id}：${episode.trace.length} 帧；${episode.events.length} 个事件；${episode.scenario.activity ? "场景文件记录活动契约" : "场景文件未记录活动契约，不补入后续规则"}；${episode.events.some(event => event.kind === "human_state_update") ? "事件含伙伴状态更新" : "事件未记录伙伴状态更新"}；文件：${episode.artifacts.join("、")}。`);
    document.getElementById("artifact-audit").append(audit);
  }
  const related = document.getElementById("related-report");
  if (["formal_v6", "paired_v8"].includes(report.run_name)) {
    related.href = report.run_name === "formal_v6" ? "../paired_v8/index.html" : "../formal_v6/index.html";
    related.hidden = false;
  }
  document.getElementById("original-report").hidden = !report.has_original_report;
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) document.getElementById("motion-note").textContent = "检测到减少动态效果偏好：默认静止，建议使用逐帧按钮；播放由你主动启动。";
}

function calculateBounds(episodes) {
  const points = episodes.flatMap(episode => [...Object.values(episode.scenario.regions || {}), ...episode.trace.flatMap(frame => [...Object.values(frame.objects), frame.human_position, frame.robot_position])]);
  return {minX: Math.min(...points.map(point => point[0])) - .14, maxX: Math.max(...points.map(point => point[0])) + .14, minY: Math.min(...points.map(point => point[1])) - .14, maxY: Math.max(...points.map(point => point[1])) + .14};
}

function drawScene(canvas, episode, frameIndex) {
  const context = canvas.getContext("2d");
  const frame = episode.trace[frameIndex];
  const scale = Math.min(570 / (bounds.maxX - bounds.minX), 470 / (bounds.maxY - bounds.minY));
  const offsetX = (680 - (bounds.maxX - bounds.minX) * scale) / 2;
  const offsetY = 50 + (470 - (bounds.maxY - bounds.minY) * scale) / 2;
  const project = point => [offsetX + (point[0] - bounds.minX) * scale, offsetY + (bounds.maxY - point[1]) * scale];
  context.clearRect(0, 0, 680, 600);
  context.font = "14px system-ui";
  context.textAlign = "center";
  for (let axisValue = Math.ceil(bounds.minX * 5) / 5; axisValue <= bounds.maxX; axisValue += .2) {
    const [axisX] = project([axisValue, 0]);
    context.strokeStyle = "#e1e8f0";
    context.beginPath(); context.moveTo(axisX, 42); context.lineTo(axisX, 525); context.stroke();
    context.fillStyle = "#53657b"; context.fillText(axisValue.toFixed(1), axisX, 552);
  }
  for (let axisValue = Math.ceil(bounds.minY * 5) / 5; axisValue <= bounds.maxY; axisValue += .2) {
    const [, axisY] = project([0, axisValue]);
    context.strokeStyle = "#e1e8f0";
    context.beginPath(); context.moveTo(45, axisY); context.lineTo(640, axisY); context.stroke();
    context.fillStyle = "#53657b"; context.fillText(axisValue.toFixed(1), 23, axisY + 4);
  }
  context.fillStyle = "#172b45"; context.fillText("x / 米", 340, 578); context.fillText("y / 米", 40, 25);
  for (const [name, position] of Object.entries(episode.scenario.regions || {})) {
    const [centerX, centerY] = project(position);
    context.fillStyle = name.startsWith("keep") ? "#edf7ef" : "#e7effb";
    context.fillRect(centerX - 25, centerY - 16, 50, 32);
    context.strokeStyle = "#8398b0"; context.strokeRect(centerX - 25, centerY - 16, 50, 32);
    context.fillStyle = "#304762"; context.fillText(name.replace("tray_", "托盘·").replace("keep_", "留用·"), centerX, centerY + 35);
  }
  if (document.getElementById("trail-toggle").checked) {
    for (const [key, color] of [["human_position", "#ab84d4"], ["robot_position", "#70b8bc"]]) {
      context.strokeStyle = color; context.lineWidth = 2; context.beginPath();
      episode.trace.slice(0, frameIndex + 1).forEach((sample, index) => {
        const [pointX, pointY] = project(sample[key]);
        if (index === 0) context.moveTo(pointX, pointY); else context.lineTo(pointX, pointY);
      });
      context.stroke();
    }
  }
  const objectColors = {red: "#b43b36", blue: "#235eb1", green: "#23784c"};
  for (const [name, position] of Object.entries(frame.objects)) {
    const [centerX, centerY] = project(position);
    const spec = (episode.scenario.objects || []).find(object => object.name === name);
    const radius = Math.max(9, (spec?.radius || .045) * scale);
    context.beginPath(); context.arc(centerX, centerY, radius, 0, Math.PI * 2);
    context.fillStyle = objectColors[name] || "#735342"; context.fill();
    context.strokeStyle = "white"; context.lineWidth = 2; context.stroke();
    context.fillStyle = "#172b45"; context.fillText(name, centerX, centerY - radius - 7);
  }
  for (const [position, label, color] of [[frame.human_position, "人", "#753ac3"], [frame.robot_position, "末端", "#047e87"]]) {
    const [centerX, centerY] = project(position);
    context.beginPath(); context.arc(centerX, centerY, 14, 0, Math.PI * 2); context.fillStyle = color; context.fill();
    context.fillStyle = "#172b45"; context.fillText(label, centerX, centerY + 31);
  }
  canvas.setAttribute("aria-label", `${episode.metrics.scenario}，${modeNames[episode.metrics.partner_mode] || episode.metrics.partner_mode}，${frame.time_s.toFixed(2)} 秒；人位置 ${frame.human_position.slice(0, 2).map(value => value.toFixed(3)).join("、")} 米；机器人末端 ${frame.robot_position.slice(0, 2).map(value => value.toFixed(3)).join("、")} 米。`);
}

function buildPanels() {
  const container = document.getElementById("replay-panels");
  container.replaceChildren();
  container.classList.toggle("single", selectedEpisodes.length === 1);
  for (const episode of selectedEpisodes) {
    const panel = element("article", undefined, "panel");
    const heading = element("div", undefined, "panel-heading");
    heading.append(element("h3", `${episode.metrics.policy_name || report.provenance.policy || "策略未记录"} · ${modeNames[episode.metrics.partner_mode] || metric(episode.metrics.partner_mode)}`), element("p", `${episode.metrics.scenario} · seed ${metric(episode.metrics.seed)}`));
    if (episode.metrics.history_condition) heading.append(element("p", historyNames[episode.metrics.history_condition] || episode.metrics.history_condition));
    const canvas = document.createElement("canvas"); canvas.width = 680; canvas.height = 600; canvas.setAttribute("role", "img");
    const information = element("div", undefined, "panel-info");
    const status = element("p"); status.dataset.status = "true";
    const observed = element("p"); observed.dataset.observed = "true";
    const latest = element("p"); latest.dataset.latest = "true";
    const details = element("details"); details.append(element("summary", "事件时间轴（点击跳转）"));
    const list = element("ul", undefined, "event-list");
    for (const event of episode.events) {
      if (event.kind === "policy_action" && event.action === "wait") continue;
      const eventSeconds = eventTime(episode, event);
      const item = element("li");
      const button = element("button", `${eventSeconds.toFixed(2)} s · ${eventLabel(event)}`); button.type = "button";
      button.addEventListener("click", () => { setPlaying(false); seek(frameIndexAt(timeGrid.map(time_s => ({time_s})), eventSeconds), eventSeconds); });
      item.append(button); list.append(item);
    }
    details.append(list);
    const sourceLinks = element("p");
    for (const name of episode.artifacts) {
      if (!episode.artifacts.includes(name)) continue;
      const link = element("a", name); link.href = episode.id.split("/").map(encodeURIComponent).join("/") + "/" + name;
      sourceLinks.append(link, document.createTextNode(" · "));
    }
    const settings = element("details"); settings.append(element("summary", "本次场景与初始分工（评测端信息）"), element("pre", JSON.stringify({description: episode.scenario.description, robot_targets: episode.scenario.robot_targets, human_targets: episode.scenario.human_targets, dynamics: episode.scenario.dynamics ?? "未记录", activity: episode.scenario.activity ?? "未记录", structure: episode.scenario.structure}, null, 2)));
    information.append(status, observed, latest, details, settings, sourceLinks);
    if (episode.history_probe) {
      const probe = episode.history_probe;
      information.append(element("p", `探针开始的伙伴判断（评测端）：trust=${probe.probe_initial_state.trust}，reliability=${probe.probe_initial_state.reliability_belief}；同一求助回答：${probe.help_reply === "accept" ? "接受" : probe.help_reply === "decline" ? "拒绝" : "未记录"}。`));
    }
    if (episode.artifacts.includes("demo.mp4")) {
      const video = element("video");
      video.controls = true;
      video.preload = "metadata";
      video.style.width = "100%";
      video.src = episode.id.split("/").map(encodeURIComponent).join("/") + "/demo.mp4";
      const speed = element("select"); speed.setAttribute("aria-label", "仿真视频播放速度");
      for (const value of [0.25, 0.5, 1]) {
        const option = element("option", `${value} 倍`); option.value = String(value); option.selected = value === 1; speed.append(option);
      }
      speed.addEventListener("change", () => { video.playbackRate = Number(speed.value); });
      information.append(element("p", episode.video_timeline ? "VC/Genesis 实际视频：时间轴定位已保存帧；事件跳转定位事件后的首个视频帧（最多一个采样间隔）。也可独立播放或慢放。" : "VC/Genesis 实际视频：旧运行没有精确时间映射，独立播放。"), speed, video);
    }
    if (episode.observations.some(row => row.rgb_artifact)) {
      const rgb = element("img"); rgb.dataset.rgb = "true"; rgb.alt = "机器人相机的实际 RGB 输入"; rgb.style.width = "100%";
      information.append(element("p", "机器人输入 RGB（随事件 / 时间轴定位）"), rgb);
    }
    if (episode.observations.some(row => row.wrist_rgb_artifact)) {
      const wrist = element("img"); wrist.dataset.wristRgb = "true"; wrist.alt = "真实腕部相机输入"; wrist.style.width = "100%";
      information.append(element("p", "随机械臂运动的腕部相机 RGB"), wrist);
    }
    const joints = element("p"); joints.dataset.joints = "true"; information.append(joints);
    panel.append(heading, canvas, information); container.append(panel);
    episode.panel = panel;
  }
}

function seek(index, eventSeconds) {
  currentIndex = Math.max(0, Math.min(index, timeGrid.length - 1));
  timeline.value = String(currentIndex);
  const time = eventSeconds ?? timeGrid[currentIndex];
  document.getElementById("clock").textContent = `${time.toFixed(2)} / ${timeGrid[timeGrid.length - 1].toFixed(2)} s · 帧 ${currentIndex + 1}/${timeGrid.length}`;
  document.getElementById("previous-frame").disabled = currentIndex === 0;
  document.getElementById("next-frame").disabled = currentIndex === timeGrid.length - 1;
  for (const episode of selectedEpisodes) {
    const frameIndex = frameIndexAt(episode.trace, time);
    const frame = episode.trace[frameIndex];
    drawScene(episode.panel.querySelector("canvas"), episode, frameIndex);
    const robotAction = frame.active_robot_action?.startsWith("transfer:") ? `搬运 ${frame.active_robot_action.split(":")[1]}` : actionNames[frame.active_robot_action] || frame.active_robot_action;
    episode.panel.querySelector("[data-status]").textContent = `记录帧 ${frameIndex + 1}/${episode.trace.length} · 人：${actionNames[frame.human_action] || frame.human_action} · 机器人：${robotAction}`;
    const observation = episode.observations.length ? episode.observations[frameIndexAt(episode.observations, frame.time_s)] : {};
    const prefix = episode.id.split("/").map(encodeURIComponent).join("/") + "/";
    const rgb = episode.panel.querySelector("[data-rgb]");
    if (rgb && observation.rgb_artifact) rgb.src = prefix + encodeURIComponent(observation.rgb_artifact);
    const wrist = episode.panel.querySelector("[data-wrist-rgb]");
    if (wrist && observation.wrist_rgb_artifact) wrist.src = prefix + encodeURIComponent(observation.wrist_rgb_artifact);
    episode.panel.querySelector("[data-joints]").textContent = observation.robot_qpos?.length ? `关节位置（rad）：${observation.robot_qpos.map(value => value.toFixed(3)).join(", ")}` : "当前观测未记录关节位置。";
    const video = episode.panel.querySelector("video");
    const videoFrames = episode.video_timeline?.frames.filter(row => Number.isFinite(row.benchmark_time_s));
    if (video && videoFrames?.length && !playing) {
      video.pause();
      let target = videoFrames[0];
      for (const row of videoFrames) { if (row.benchmark_time_s > time + 1e-8) break; target = row; }
      if (eventSeconds !== undefined) target = videoFrames.find(row => row.benchmark_time_s > time + 1e-8) || videoFrames.at(-1);
      video.currentTime = target.video_time_s;
    }
    episode.panel.querySelector("[data-observed]").textContent = `公开完成贡献：${(observation.completed_skills || []).join("；") || "当前观测未记录完成贡献"}`;
    const visibleEvents = episode.events.filter(event => eventTime(episode, event) <= time + 1e-8 && event.kind !== "policy_action");
    const lastEvent = visibleEvents[visibleEvents.length - 1];
    episode.panel.querySelector("[data-latest]").textContent = lastEvent ? `最近事件：${eventLabel(lastEvent)}` : "最近事件：无";
  }
}

function setPlaying(value) {
  playing = value;
  playButton.textContent = playing ? "暂停" : "播放";
  playButton.setAttribute("aria-pressed", String(playing));
  if (animationId !== null) cancelAnimationFrame(animationId);
  lastTimestamp = null;
  playTime = timeGrid[currentIndex];
  if (playing) animationId = requestAnimationFrame(animate);
}

function animate(timestamp) {
  if (!playing) return;
  if (lastTimestamp !== null) playTime += (timestamp - lastTimestamp) / 1000 * Number(document.getElementById("speed-select").value);
  lastTimestamp = timestamp;
  seek(frameIndexAt(timeGrid.map(time_s => ({time_s})), playTime));
  if (playTime >= timeGrid[timeGrid.length - 1]) { setPlaying(false); return; }
  animationId = requestAnimationFrame(animate);
}

function chooseScenario() {
  setPlaying(false);
  const group = episodesByScene.get(scenarioSelect.value);
  const previousSeed = seedSelect.value;
  seedSelect.replaceChildren();
  for (const seed of [...new Set(group.map(e => String(e.metrics.seed)))].sort((a, b) => Number(a) - Number(b))) {
    const option = element("option", seed); option.value = seed; seedSelect.append(option);
  }
  const all = element("option", "全部 seed"); all.value = "all"; seedSelect.append(all);
  if ([...seedSelect.options].some(option => option.value === previousSeed)) seedSelect.value = previousSeed;
  selectedEpisodes = group.filter(e => seedSelect.value === "all" || String(e.metrics.seed) === seedSelect.value);
  timeGrid = [...new Set(selectedEpisodes.flatMap(episode => episode.trace.map(frame => frame.time_s)))].sort((first, second) => first - second);
  bounds = calculateBounds(selectedEpisodes);
  timeline.max = String(timeGrid.length - 1);
  const note = sceneNotes[scenarioSelect.value] || sceneNotes[selectedEpisodes[0].metrics.condition];
  document.getElementById("scenario-explanation").textContent = note ? note[1] : (selectedEpisodes[0].scenario.description || "此场景的研究意图未记录。请依据实际轨迹与消息分析。");
  buildPanels(); seek(0);
}

fillReport();
for (const [name] of episodesByScene) {
  const option = element("option", `${sceneNotes[name]?.[0] || name} · ${name}`); option.value = name; scenarioSelect.append(option);
}
scenarioSelect.addEventListener("change", chooseScenario);
seedSelect.addEventListener("change", chooseScenario);
playButton.addEventListener("click", () => { if (!playing && currentIndex === timeGrid.length - 1) seek(0); setPlaying(!playing); });
document.getElementById("restart").addEventListener("click", () => { setPlaying(false); seek(0); });
document.getElementById("previous-frame").addEventListener("click", () => { setPlaying(false); seek(currentIndex - 1); });
document.getElementById("next-frame").addEventListener("click", () => { setPlaying(false); seek(currentIndex + 1); });
timeline.addEventListener("input", () => { setPlaying(false); seek(Number(timeline.value)); });
document.getElementById("trail-toggle").addEventListener("change", () => seek(currentIndex));
document.addEventListener("visibilitychange", () => { if (document.hidden) setPlaying(false); });
chooseScenario();
