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
                 generator: Callable[[str], str] | None = None):
        self.scenario = scenario
        self.model_path = Path(model_path)
        self.decision_interval_steps = max(1, int(decision_interval_steps))
        self.generator = generator
        if persona_id is not None and persona_id not in PERSONAS:
            raise ValueError("未知的人类 persona")
        self.fixed_persona_id = persona_id
        self._model = None
        self._tokenizer = None
        self.reset(0)

    def reset(self, seed: int) -> None:
        self.rng = np.random.default_rng(seed)
        self.persona_id = self.fixed_persona_id or str(self.rng.choice(tuple(PERSONAS)))
        self.seen_messages = 0
        self.last_inference_step = -self.decision_interval_steps
        self.last_message_count = -1
        self.last_action_signature = None
        self.command = HumanCommand("observe")
        self.policy_io: list[dict[str, Any]] = []
        self.public_decision_history: list[dict[str, Any]] = []

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
            enable_thinking=False, return_tensors="pt")
        encoded = encoded.to(self._model.device)
        input_ids = (encoded["input_ids"] if hasattr(encoded, "keys")
                     and "input_ids" in encoded else encoded)
        with torch.inference_mode():
            generation_kwargs = {
                "max_new_tokens": 160, "do_sample": True,
                "temperature": 0.45, "top_p": 0.85,
                "pad_token_id": self._tokenizer.eos_token_id,
            }
            if hasattr(encoded, "keys") and "input_ids" in encoded:
                generated = self._model.generate(**encoded, **generation_kwargs)
            else:
                generated = self._model.generate(encoded, **generation_kwargs)
        return self._tokenizer.decode(
            generated[0, input_ids.shape[-1]:], skip_special_tokens=True).strip()

    def _system_prompt(self) -> str:
        return (
            "你是一个在共享工作台工作的真实人类伙伴模拟策略。根据公开观察和公开对话，"
            "自主决定下一步意图；不得假设你知道未公开的任务标签或机器人计划。"
            f"你的稳定行为倾向是：{PERSONAS[self.persona_id]} "
            "只输出一个 JSON 对象，字段为 intent、object_id、destination、message、speed_mps。"
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
            "human_position_xyz": [round(float(x), 3) for x in observation.human_position],
            "robot_ee_xyz": [round(float(x), 3) for x in observation.robot_ee],
            "human_holds": list(observation.held_by_human),
            "your_hand_position_xyz": observation.human_hand_position,
            "your_visible_motor_phase": observation.human_motor_phase,
            "publicly_completed_contributions": list(observation.completed_skills),
            "robot_action": observation.active_robot_action,
            "robot_action_phase": observation.action_phase,
            "public_dialogue": messages,
            "your_recent_public_decisions": self.public_decision_history[-4:],
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
        prompt = self._prompt(observation)
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
        self.last_inference_step = step
        self.last_message_count = message_count
        self.last_action_signature = action_signature
        self.seen_messages = message_count
        safe_decision = {
            "intent": command.intent,
            "object_id": command.object_id,
            "destination": command.destination,
            "message": str(decision.get("message", ""))[:240],
            "speed_mps": command.speed_mps,
        }
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
                "policy_io": self.policy_io, "inference_count": len(self.policy_io),
                "mean_inference_latency_s": (
                    float(np.mean([row["latency_s"] for row in self.policy_io]))
                    if self.policy_io else None)}
