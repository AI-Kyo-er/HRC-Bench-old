/* 独立研究视图，只读保存记录；不改变模型输入或实验视频。 */
(() => {
  const objects = {akita_black_bowl_1: '碗', cream_cheese_1: '奶酪', wine_bottle_1: '酒瓶',
    plate_1: '餐盘', wooden_cabinet_1: '柜子', flat_stove_1: '炉面', wine_rack_1: '酒架'};
  const actions = {wait: '等待或继续原运动', relocate: '搬放', pick: '取起并持有', place: '放下',
    point: '指示', away: '暂离', return: '返回', pause_current: '暂停当前运动', move_hand: '移动手'};
  const phases = {idle: '静止', transfer_raise: '抬高', transfer_translate: '搬运',
    transfer_lower: '放下', transfer_retreat: '退手', pick_approach: '接近物品', pick_lift: '取起物品',
    away: '暂离中', return: '返回中', point: '指示中'};
  const skills = {cream_in_bowl: '奶酪入碗', bottle_on_rack: '酒瓶上架', bottle_on_cabinet: '酒瓶放柜顶',
    open_middle_drawer: '打开中层抽屉', bowl_on_stove: '碗放炉面', bowl_on_cabinet: '碗放柜顶',
    bowl_inside_top_drawer: '碗放上层抽屉', plate_front_stove: '移餐盘到炉前', bowl_on_plate: '碗放餐盘'};
  const plain = value => {
    let text = String(value || '');
    for (const [name, label] of Object.entries(objects)) text = text.replaceAll(name, label);
    return text;
  };
  const destination = name => {
    if (!name) return '';
    const parts = name.split('__');
    if (parts.length === 3) return plain(parts[2]) + (parts[1] === 'in' ? '内' : '上');
    if (name.endsWith('_on_cabinet')) return '柜顶';
    if (name.endsWith('_personal')) return plain(name.slice(0, -9)) + '的个人桌面区';
    return ({serving_ready: '准备区', snack_delivery: '交付区', drink_staging: '饮品准备区',
      drawer_storage: '抽屉内部'})[name] || plain(name);
  };
  const lastAt = (rows, value) => {
    let low = 0, high = rows.length;
    while (low < high) {
      const mid = (low + high) >> 1;
      if (rows[mid].video_time_s <= value) low = mid + 1;
      else high = mid;
    }
    return low ? rows[low - 1] : null;
  };
  for (const panel of document.querySelectorAll('.episode-inspector')) {
    const video = panel.closest('section').querySelector('video');
    const write = (name, value) => {panel.querySelector(`[data-view="${name}"]`).textContent = value;};
    fetch(panel.dataset.inspection).then(response => {
      if (!response.ok) throw new Error('审阅记录无法加载');
      return response.json();
    }).then(data => {
      const select = panel.querySelector('.inspection-seek');
      select.replaceChildren();
      const times = [...new Set([...data.human_decisions, ...data.robot_decisions].map(row => row.benchmark_time_s))].sort((a,b) => a-b);
      for (const time of times) {
        const frame = data.video_frames.find(row => row.benchmark_time_s >= time);
        if (!frame) continue;
        const option = document.createElement('option');
        option.value = frame.video_time_s; option.textContent = `模拟 ${time.toFixed(1)} 秒`;
        select.append(option);
      }
      select.disabled = false;
      select.addEventListener('change', () => {video.currentTime = Number(select.value);});
      const update = () => {
        const frame = lastAt(data.video_frames, video.currentTime);
        if (!frame) {
          write('clock', '视频尚未进入有对应环境记录的时刻');
          for (const name of ['human-need','human-choice','human-speech','robot-choice','robot-speech','execution']) write(name, '尚无该时刻记录');
          panel.querySelector('[data-view="facts"]').replaceChildren();
          return;
        }
        write('clock', `视频 ${video.currentTime.toFixed(2)} 秒 · 模拟 ${frame.benchmark_time_s.toFixed(2)} 秒`);
        const human = data.human_decisions[frame.human_decision_row];
        const robot = data.robot_decisions[frame.robot_decision_row];
        const choice = human?.selected_contribution || {};
        write('human-need', human?.private_agenda?.current_need || '本方法未记录私人需要');
        write('human-choice', (actions[choice.action] || choice.action || '尚未选择') +
          (choice.object_id ? ' ' + plain(choice.object_id) : '') +
          (choice.destination ? ' → ' + destination(choice.destination) : ''));
        write('human-speech', plain(choice.message) || '本次没有公开话语');
        write('robot-choice', robot ? (robot.decision.mode === 'hold' ? '保持／协商' :
          skills[robot.selected_skill_id] || plain(robot.decision.instruction)) : '尚未选择');
        write('robot-speech', plain(robot?.decision.message) || '本次没有公开话语');
        const execution = frame.human_execution;
        const source = frame.actual_robot_action_source;
        const robotActual = source === null ? '没有后续控制记录' : source.includes('hold') ? '实际保持控制' :
          source.includes('vla') ? '实际VLA动作控制' : '实际控制来源：' + source;
        const receipt = execution.last_receipt;
        write('execution', '人：' + (phases[execution.phase] || execution.phase) + '，' +
          (execution.held_object ? '持有' + plain(execution.held_object) : '未持物') +
          (receipt?.accepted === false ? '；最近动作被拒绝：' + receipt.error : '') + '。机器人：' + robotActual + '。');
        const facts = panel.querySelector('[data-view="facts"]');
        facts.replaceChildren(...frame.measured_current_facts.map(text => {
          const li = document.createElement('li');li.textContent = plain(text);return li;
        }));
        panel.dataset.benchmarkTime = String(frame.benchmark_time_s);
      };
      video.addEventListener('timeupdate', update);
      video.addEventListener('seeked', update);
      panel.dataset.inspectionState = 'ready';update();
    }).catch(error => {
      panel.dataset.inspectionState = 'failed';write('clock', error.message);
    });
  }
})();
