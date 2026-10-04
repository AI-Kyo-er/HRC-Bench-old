"""VLA/WLA 接入 HRC-Continuous 的最小适配示例。

真实模型只需替换 ``predict_vla`` 或 ``predict_wla``。它们接收公开观测，
返回 Action JSON；评测器私有目标、伙伴潜变量和评分标签不会进入输入。
"""
from __future__ import annotations

from typing import Any, Callable

from hrc_pilot.benchmark import ExternalPolicyAdapter


def make_vla_adapter(model: Callable[[Any], Any]) -> ExternalPolicyAdapter:
    """将接收 RGB 加结构化观测的 VLA 包装成 benchmark 策略。"""
    def predict_vla(observation: dict[str, Any]) -> Any:
        return model({"rgb": observation["rgb"], "state": observation})

    return ExternalPolicyAdapter(predict_vla, adapter_name="example-vla")


def make_wla_adapter(model: Callable[[str], Any]) -> ExternalPolicyAdapter:
    """将接收结构化/文本状态的 WLA 包装成 benchmark 策略。"""
    def predict_wla(observation: dict[str, Any]) -> Any:
        state = {key: value for key, value in observation.items() if key != "rgb"}
        return model(repr(state))

    return ExternalPolicyAdapter(predict_wla, adapter_name="example-wla")


if __name__ == "__main__":
    print("将此示例中的 model 替换为实际 VLA/WLA 推理函数，再传给 run_continuous_episode。")
