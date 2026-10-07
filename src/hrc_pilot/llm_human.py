"""本地语言模型驱动的公开观察人类伙伴策略。"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .continuous import HumanCommand, PartnerOutput
from .protocol import Message, Observation


PERSONAS = {
    "cooperative": "你愿意共同完成活动，也会在机器人明显受阻时主动提供帮助。",
    "independent": "你优先完成自己认为重要的贡献，只有在明确需要时才介入机器人的工作。",
    "cautious": "你谨慎观察机器人动作，避免同时接近同一物体，并在不确定时等待或询问。",
    "assertive": "你会清楚表达自己的工作意图，发现冲突时主动让机器人协调空间。",
}


class QwenHumanPolicy:
    """以本地 Qwen 生成伙伴意图；动作执行仍由仿真器的连续控制器负责。

    模型提示只包含公开观察、公开对话和该伙伴自己的先前公开决定。评测器
    状态、场景 JSON、机器人私有计划和预设人类目标都不会进入模型输入。
    """

    def __init__(self, scenario, *, model_path: str | Path,
                 decision_interval_steps: int = 10,
                 persona_id: str | None = None,
                 memory_scope: str = "episode",
                 generator: Callable[[str], str] | None = None):
        self.scenario = scenario
        self.model_path = Path(model_path)
        self.decision_interval_steps = max(1, int(decision_interval_steps))
        self.generator = generator
        if persona_id is not None and persona_id not in PERSONAS:
            raise ValueError("未知的人类 persona")
        self.fixed_persona_id = persona_id
        if memory_scope not in {"episode", "session"}:
            raise ValueError("未知伙伴记忆范围")
        self.memory_scope = memory_scope
        self.session_experiences = []
        self.activity_index = -1
        self._model = None
        self._tokenizer = None
        self.reset(0)

    def reset(self, seed: int) -> None:
        if self.memory_scope == "session":
            self.session_experiences.extend(getattr(self, "experience_memory", [])[-12:])
            self.session_experiences = self.session_experiences[-48:]
        self.activity_index += 1
        self.rng = np.random.default_rng(seed)
        if self.memory_scope != "session" or not hasattr(self, "persona_id"):
            self.persona_id = self.fixed_persona_id or str(self.rng.choice(tuple(PERSONAS)))
        self.seen_messages = 0
        self.last_inference_step = -self.decision_interval_steps
        self.last_message_count = -1
        self.last_action_signature = None
        self.command = HumanCommand("observe")
        self.policy_io: list[dict[str, Any]] = []
        self.public_decision_history: list[dict[str, Any]] = []
        self.observation_history: list[dict[str, Any]] = []
        self.experience_memory: list[dict[str, Any]] = []
        self.public_task_memory: dict[str, dict[str, Any]] = {}
        self.current_goal = ""
        self.public_activity_context = None
        self.public_activity_epoch = 0
        self.goal_activity_epoch = 0
        self.memory_retrievals = []

    def initial_messages(self) -> tuple[Message, ...]:
        return self.scenario.initial_messages()

    def prepare(self):
        """在仿真器初始化前加载模型，隔离 Torch/Genesis 的编译器导入顺序。"""
        self._load_model()

    def _load_model(self) -> None:
        if self.generator is not None or self._model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(
            str(self.model_path), local_files_only=True, trust_remote_code=True)
        self._model = AutoModelForCausalLM.from_pretrained(
            str(self.model_path), local_files_only=True, trust_remote_code=True,
            torch_dtype=torch.bfloat16, device_map={"": 0}, low_cpu_mem_usage=True)
        self._model.eval()

    def _generate(self, prompt: str) -> str:
        if self.generator is not None:
            return self.generator(prompt)
        self._load_model()
        import torch

        messages = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": prompt},
        ]
        encoded = self._tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            enable_thinking=getattr(self,'enable_thinking',False), return_tensors="pt")
        encoded = encoded.to(self._model.device)
        input_ids = (encoded["input_ids"] if hasattr(encoded, "keys")
                     and "input_ids" in encoded else encoded)
        with torch.inference_mode():
            generation_kwargs = {
                "max_new_tokens": self.generation_token_limit, "do_sample": True,
                "temperature": 0.45, "top_p": 0.85,
                "pad_token_id": self._tokenizer.eos_token_id,
            }
            if hasattr(encoded, "keys") and "input_ids" in encoded:
                generated = self._model.generate(**encoded, **generation_kwargs)
            else:
                generated = self._model.generate(encoded, attention_mask=torch.ones_like(encoded), **generation_kwargs)
        return self._tokenizer.decode(
            generated[0, input_ids.shape[-1]:], skip_special_tokens=True).strip()

    generation_token_limit = 256

    def _system_prompt(self) -> str:
        return (
            "你是一个在共享工作台工作的真实人类伙伴模拟策略。根据公开观察和公开对话，"
            "自主决定下一步意图；不得假设你知道未公开的任务标签或机器人计划。"
            f"你的稳定行为倾向是：{PERSONAS[self.persona_id]} "
            "只输出一个 JSON 对象，字段为 intent、object_id、destination、message、speed_mps、reason、memory_note、current_goal。"
            "你就是speaker为human的伙伴，value为robot的初始分工属于机器人，value为human属于你。"
            "公开任务板持续保留承诺与附加条件，最近对话只补充新变化；接管是改变分工，"
            "不要把机器人原先的任务误称为自己的原始任务。current_goal用一句话表述你当前"
            "要完成或重新协调的目标，允许随公开进展改变。几何接近目标不等于贡献已提交，"
            "公开未提交或action_blocked反馈应结合任务板理解，不假定它只是距离误差。"
            "过去活动的经验只供参考，不能当作当前物体状态或当前分工；先比较现在的公开任务板与观察。"
            "公开activity_change表示上一安排已被替代；保留的旧目标是你先前的意图，"
            "需要依据新活动自行决定继续、修改或放弃，并在current_goal中明确当前目标。"
            "reason 简短解释为何继续、改变或暂缓当前贡献；memory_note 记录你从公开观察"
            "确认的新经验，它将作为你的个人记忆进入后续决定。记忆只写有观察依据的事实，"
            "不得编造机器人隐藏计划或信任分数。比较带时间的可见历史，判断是否有实际进展。"
            "intent 只能是 observe、approach、carry、yield、away、return。approach/carry 应选择"
            "公开对话中提到且当前未完成的对象与区域；若信息不足则 observe。"
            "approach 表示伸手取指定物体，carry 表示拿着物体放到指定区域。公开对话中"
            "‘我先处理’是你的承诺，‘请你处理’是给机器人的分工；两者可以并行，"
            "无需仅因机器人正在动就停止自己的工作。根据双方实际位置决定是否冲突。"
            "机器人长期停顿或未完成时，你可以询问、提出改变分工或主动接管，"
            "也可以保留自己的优先事项；只能依据当前可见进度判断。"
            "yield 表示给机器人让出共享空间；away 表示暂离，return 表示回来继续活动。"
            "速度范围 0.15 到 0.65 m/s。"
            "message 可为空；需要协调时写一句简短中文公开消息。不要输出 Markdown。"
        )

    def _prompt(self, observation: Observation) -> str:
        messages = [
            {"speaker": message.speaker, "kind": message.kind, "text": message.text,
             "object_id": message.object_id, "value": message.value,
             "destination": message.destination}
            for message in observation.messages[-16:]
        ]
        visible = {
            "time_s": round(float(observation.time_s), 2),
            "objects_xyz": {key: [round(float(x), 3) for x in value]
                            for key, value in observation.objects.items()},
            "regions_xyz": {key: [round(float(x), 3) for x in value]
                            for key, value in observation.regions.items()},
            "public_goal_surfaces": observation.goal_surfaces,
            "human_position_xyz": [round(float(x), 3) for x in observation.human_position],
            "robot_ee_xyz": [round(float(x), 3) for x in observation.robot_ee],
            "human_holds": list(observation.held_by_human),
            "your_hand_position_xyz": observation.human_hand_position,
            "your_visible_motor_phase": observation.human_motor_phase,
            "publicly_completed_contributions": list(observation.completed_skills),
            "robot_action": observation.active_robot_action,
            "robot_action_phase": observation.action_phase,
            "public_dialogue": messages,
            "persistent_public_task_board": list(self.public_task_memory.values()),
            "current_public_activity": self.public_activity_context,
            "your_current_generated_goal": self.current_goal,
            "generated_goal_predates_current_activity": self.goal_activity_epoch < self.public_activity_epoch,
            "your_recent_public_decisions": self.public_decision_history[-4:],
            "your_recent_observation_history": self.observation_history[-10:],
            "your_personal_experience_memory": self.experience_memory[-12:],
            "your_previous_activity_experiences": self.session_experiences[-12:] if self.memory_scope == "session" else [],
        }
        return "根据以下当前公开信息选择下一步伙伴意图：\n" + json.dumps(
            visible, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _parse(raw: str) -> dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end < start:
            raise ValueError("模型输出不含 JSON 对象")
        value = json.loads(text[start:end + 1])
        if not isinstance(value, dict):
            raise ValueError("模型输出必须是 JSON 对象")
        return value

    def _validated_command(self, value: dict[str, Any], observation: Observation) -> HumanCommand:
        intent = value.get("intent", "observe")
        if intent not in {"observe", "approach", "carry", "yield", "away", "return"}:
            intent = "observe"
        object_id = value.get("object_id")
        destination = value.get("destination")
        if object_id not in observation.objects:
            object_id = None
        if destination not in observation.regions:
            destination = None
        if intent in {"approach", "carry"} and (object_id is None or destination is None):
            intent, object_id, destination = "observe", None, None
        if intent == "carry" and object_id not in observation.held_by_human:
            intent = "approach"
        if intent == "approach" and object_id in observation.held_by_human:
            intent = "carry"
        if intent == "carry":
            region = observation.regions[destination]
            target = (float(region[0]), float(region[1]), 0.0)
        elif intent == "approach":
            point = observation.objects[object_id]
            target = (float(point[0]), float(point[1]), 0.0)
        elif intent == "yield":
            target = (0.50, 0.78, 0.0)
        elif intent == "away":
            target = (0.50, 0.90, 0.0)
        elif intent == "return":
            target = (0.50, 0.70, 0.0)
        else:
            target = tuple(float(x) for x in observation.human_position)
        try:
            speed = float(value.get("speed_mps", 0.42))
        except (TypeError, ValueError):
            speed = 0.42
        speed = float(np.clip(speed, 0.15, 0.65))
        return HumanCommand(intent, object_id, destination, target,
                            speed_mps=speed, acceleration_mps2=1.2,
                            gaze_target=(tuple(observation.objects[object_id])
                                         if object_id else None))

    def step(self, observation: Observation) -> PartnerOutput:
        step = int(round(observation.time_s * self.scenario.tick_hz))
        message_count = len(observation.messages)
        action_signature = (observation.active_robot_action, observation.action_phase)
        infer = (not self.policy_io or step - self.last_inference_step >= self.decision_interval_steps
                 or message_count != self.last_message_count
                 or action_signature != self.last_action_signature)
        if not infer:
            return PartnerOutput(self.command)
        for message in observation.messages[self.seen_messages:]:
            if message.kind == "activity_change":
                self.public_activity_epoch += 1
                self.public_activity_context = {
                    "source": "public_dialogue", "epoch": self.public_activity_epoch,
                    "observed_at_s": observation.time_s, "text": message.text,
                    "previous_generated_goal": self.current_goal,
                }
                # The public announcement explicitly replaces the task board.
                # Personal goals, decisions, and experiences remain model-owned.
                self.public_task_memory.clear()
            if message.kind in {"assignment", "reassignment", "correction"}:
                key = message.object_id or f"global_{len(self.public_task_memory)}"
                self.public_task_memory[key] = {
                    "source": "public_dialogue", "observed_at_s": observation.time_s,
                    "speaker": message.speaker, "kind": message.kind, "text": message.text,
                    "object_id": message.object_id, "assigned_role": message.value,
                    "destination": message.destination,
                }
        self.observation_history.append({
            "time_s": round(float(observation.time_s), 2),
            "objects_xyz": {key: [round(float(x), 3) for x in value] for key, value in observation.objects.items()},
            "robot_ee_xyz": [round(float(x), 3) for x in observation.robot_ee],
            "human_holds": list(observation.held_by_human),
            "publicly_completed_contributions": list(observation.completed_skills),
            "visible_human_motor_phase": observation.human_motor_phase,
        })
        prompt = self._prompt(observation)
        self.memory_retrievals.append({"time_s": observation.time_s,
                                      "current_memory_ids": [row['memory_id'] for row in self.experience_memory[-12:]],
                                      "previous_activity_memory_ids": [row['memory_id'] for row in self.session_experiences[-12:]]
                                      if self.memory_scope == 'session' else []})
        started = time.perf_counter()
        raw = self._generate(prompt)
        latency = time.perf_counter() - started
        parse_error = None
        try:
            decision = self._parse(raw)
            command = self._validated_command(decision, observation)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            parse_error = str(exc)
            decision = {"intent": "observe"}
            command = HumanCommand("observe", target=tuple(observation.human_position))
        self.command = command
        generated_goal = str(decision.get("current_goal", "")).strip()[:500]
        if generated_goal:
            self.current_goal = generated_goal
            self.goal_activity_epoch = self.public_activity_epoch
        self.last_inference_step = step
        self.last_message_count = message_count
        self.last_action_signature = action_signature
        self.seen_messages = message_count
        safe_decision = {
            "time_s": observation.time_s,
            "intent": command.intent,
            "object_id": command.object_id,
            "destination": command.destination,
            "message": str(decision.get("message", ""))[:240],
            "speed_mps": command.speed_mps,
            "reason": str(decision.get("reason", ""))[:500],
            "current_goal": self.current_goal,
        }
        memory_note = str(decision.get("memory_note", "")).strip()[:800]
        if memory_note:
            self.experience_memory.append({"memory_id": f"activity_{self.activity_index:04d}_experience_{len(self.experience_memory):04d}",
                                           "time_s": observation.time_s, "text": memory_note,
                                           "activity_index": self.activity_index,
                                           "public_activity_epoch": self.public_activity_epoch,
                                           "source": "qwen_generated_from_public_observation"})
        self.public_decision_history.append(safe_decision)
        outgoing = ()
        text = safe_decision["message"].strip()
        if text:
            outgoing = (Message("human", "policy_message", text,
                                command.object_id, command.intent, command.destination),)
        # The next observation includes this very message; it must not trigger a
        # fresh model call as though it were new information from the robot.
        self.last_message_count = message_count + len(outgoing)
        self.policy_io.append({
            "step": step, "time_s": observation.time_s,
            "public_input": prompt, "raw_output": raw,
            "parsed_decision": safe_decision, "parse_error": parse_error,
            "latency_s": round(latency, 6), "persona_id": self.persona_id,
        })
        return PartnerOutput(command, outgoing)

    def audit_state(self) -> dict[str, Any]:
        return {"policy": "qwen_llm_human_policy", "profile": {"profile_id": self.persona_id},
                "public_task_board": list(self.public_task_memory.values()), "generated_goal": self.current_goal,
                "public_activity_context": self.public_activity_context,
                "memory_scope": self.memory_scope, "previous_activity_memory": self.session_experiences,
                "memory_retrievals": self.memory_retrievals,
                "memory": self.experience_memory, "memory_size": len(self.experience_memory),
                "policy_io": self.policy_io, "inference_count": len(self.policy_io),
                "mean_inference_latency_s": (
                    float(np.mean([row["latency_s"] for row in self.policy_io]))
                    if self.policy_io else None)}
