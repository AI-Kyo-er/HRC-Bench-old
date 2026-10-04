"use strict";

const report = JSON.parse(document.getElementById("report-data").textContent);
const modeNames = {fixed_replay: "固定贡献顺序", reactive: "即时响应", adaptive: "适应式伙伴"};
const actionNames = {idle: "空闲", approach: "靠近物体", carry: "搬运", yield: "让行", away: "暂离", observe: "观察", wait: "等待", transfer: "搬运", joint_position: "关节目标"};
const eventNames = {public_message: "公开消息", robot_grasped: "机器人抓取", human_grasped: "人抓取", robot_transfer_completed: "机器人搬运完成", human_transfer_completed: "人搬运完成", policy_action: "机器人决策", robot_action_preempted: "动作打断", proximity_warning: "接近警告", robot_action_failed: "机器人失败", robot_action_delayed: "机器人延迟", human_state_update: "伙伴内部状态更新", robot_transfer_blocked: "依赖阻塞", human_transfer_waiting: "人等待前置贡献"};
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
};
const episodesByScene = new Map();
for (const episode of report.episodes) {
  const name = episode.metrics.scenario;
  if (!episodesByScene.has(name)) episodesByScene.set(name, []);
  episodesByScene.get(name).push(episode);
}
const scenarioSelect = document.getElementById("scenario-select");
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
  document.getElementById("report-title").textContent = report.comparisons.length ? "三种伙伴条件，是否真的改变了协作？" : "六类参考场景，实际发生了什么？";
  for (const [value, label] of [[`${success} / ${report.episodes.length}`, "保存的任务成功评分"], [String(totalFrames), "原始记录帧，逐帧回放"], [report.run_name, "实验快照，未重新运行"]]) {
    const card = element("div", undefined, "stat");
    card.append(element("strong", value), element("span", label));
    document.getElementById("headline-stats").append(card);
  }
  const provenance = report.provenance;
  const genesis = provenance.backend === "GenesisContinuousAdapter";
  document.getElementById("backend-limits").textContent = genesis
    ? "本次实际运行 VC/Genesis：Franka 关节控制、逆运动学与 Avatar 拿放动画在同一时间轴执行，每个 benchmark tick 包含多步物理推进。物体仍采用无碰撞的运动学绑定；合成失败与延迟由场景参数采样。尚未验证接触抓握、人机碰撞安全、训练后的 VLA/WLA 或真人效度。"
    : "本次运行 ContinuousWorld：简化几何与操作抽象，用于检查协议和伙伴机制。结果没有验证真实接触抓取、接触安全、先进 VLA/WLA 推理或真人协作。";
  document.getElementById("setup-description").append(element("p", `这组结果包含 ${episodesByScene.size} 个场景、${report.episodes.length} 次运行。后端：${provenance.backend || "未记录"}；机器人策略：${provenance.policy || "未记录"}；seed：${metric(provenance.seed)}。`));
  document.getElementById("setup-description").append(element("p", `${provenance.policy === "greedy_public" ? "机器人由手写参考策略驱动" : "机器人策略由上方 policy 配置指定，其是否使用训练模型需查看对应适配器"}，人的贡献由可替换伙伴规则驱动。机器人获得公开分工、几何与消息；Genesis 还提供 RGB 像素与关节状态。评分目标和人的内部变量属于评测端。`));
  document.getElementById("provenance").textContent = JSON.stringify(provenance, null, 2);
  const findings = document.getElementById("findings-description");
  findings.append(element("p", `保存记录中 ${success}/${report.episodes.length} 次任务通过。评分沿用各次运行的评测器；查看 activity_success、角色贡献与事件区分活动终态、操作失败和分工变化。这个数字不能解释为训练后具身模型成绩。`));
  if (report.comparisons.length) {
    const equalCount = report.comparisons.filter(group => group.trajectory_equal).length;
    findings.append(element("p", `逐帧核查 ${report.comparisons.length} 个配对场景：其中 ${equalCount} 个场景的三种伙伴在记录的位置、物体、动作和时间上完全一致。这个核查比较实际轨迹，而不只比较总步数。`, "notice"));
    const durations = new Set(report.episodes.map(episode => episode.trace.length));
    findings.append(element("p", durations.size === 1 ? `所有运行都记录 ${report.episodes[0].trace.length} 帧。伙伴条件在这组设置中未表现出充分区分能力；应先激活有后续影响的协作变化，再讨论模型差异。` : "不同伙伴的运行长度存在差异，但仍需分析变化来自协作、操作还是几何难度。"));
  } else {
    findings.append(element("p", "六类场景可完成基础动作并产生事件记录。场景名称是设计意图；请通过动画和消息核查接力、接管、重解释是否实际发生，不能仅据标签归因。"));
  }
  const tbody = document.getElementById("metrics-rows");
  for (const episode of report.episodes) {
    const row = episode.metrics;
    const values = [row.scenario, modeNames[row.partner_mode] || metric(row.partner_mode), `${metric(row.structure_family)} / ${metric(row.structure_split)}`, row.task_success === true ? "通过" : row.task_success === false ? "未通过" : "未记录", metric(row.recovery_status), episode.trace.length, metric(row.robot_failures), metric(row.robot_delay_steps), metric(row.human_reassignments), episode.artifacts.includes("demo.mp4") ? "demo.mp4" : "无", metric(row.human_state_updates)];
    const tableRow = element("tr");
    values.forEach((value, index) => tableRow.append(element("td", String(value), index === 3 ? (row.task_success ? "passed" : "failed") : undefined)));
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
    heading.append(element("h3", modeNames[episode.metrics.partner_mode] || metric(episode.metrics.partner_mode)), element("p", `${episode.metrics.scenario} · seed ${metric(episode.metrics.seed)}`));
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
      button.addEventListener("click", () => { setPlaying(false); seek(frameIndexAt(timeGrid.map(time_s => ({time_s})), eventSeconds)); });
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
    if (episode.artifacts.includes("demo.mp4")) {
      const video = element("video");
      video.controls = true;
      video.preload = "metadata";
      video.style.width = "100%";
      video.src = episode.id.split("/").map(encodeURIComponent).join("/") + "/demo.mp4";
      information.append(element("p", "VC/Genesis 实际仿真视频（独立播放；含初始化热身，视频时间与 benchmark 时钟有约 0.33 秒偏移）"), video);
    }
    panel.append(heading, canvas, information); container.append(panel);
    episode.panel = panel;
  }
}

function seek(index) {
  currentIndex = Math.max(0, Math.min(index, timeGrid.length - 1));
  timeline.value = String(currentIndex);
  const time = timeGrid[currentIndex];
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
  selectedEpisodes = episodesByScene.get(scenarioSelect.value);
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
playButton.addEventListener("click", () => { if (!playing && currentIndex === timeGrid.length - 1) seek(0); setPlaying(!playing); });
document.getElementById("restart").addEventListener("click", () => { setPlaying(false); seek(0); });
document.getElementById("previous-frame").addEventListener("click", () => { setPlaying(false); seek(currentIndex - 1); });
document.getElementById("next-frame").addEventListener("click", () => { setPlaying(false); seek(currentIndex + 1); });
timeline.addEventListener("input", () => { setPlaying(false); seek(Number(timeline.value)); });
document.getElementById("trail-toggle").addEventListener("change", () => seek(currentIndex));
document.addEventListener("visibilitychange", () => { if (document.hidden) setPlaying(false); });
chooseScenario();
