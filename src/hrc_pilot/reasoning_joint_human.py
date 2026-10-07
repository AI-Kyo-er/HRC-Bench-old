"""同一Qwen3的原生推理模式人策略；不增加教师决策、目标评分或物理动作。"""
from .contribution_joint_human import ContributionJointHumanPolicy


class ReasoningJointHumanPolicy(ContributionJointHumanPolicy):
    enable_thinking=True
    generation_token_limit=4096
    contribution_schema_version=5

    def _system_prompt(self):
        return super()._system_prompt().replace(
            '改变参与位置时action选message或wait，别同时请求搬物。',
            'step_aside时action选message或wait；return_to_work可以配合relocate，'
            '该单个搬运贡献自身包含连续接近工作区，不是后台选择后续计划。')
