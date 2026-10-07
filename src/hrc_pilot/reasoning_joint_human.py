"""同一Qwen3的原生推理模式人策略；不增加教师决策、目标评分或物理动作。"""
from .contribution_joint_human import ContributionJointHumanPolicy


class ReasoningJointHumanPolicy(ContributionJointHumanPolicy):
    enable_thinking=True
    generation_token_limit=4096
