"""Private experimental conditions; never passed into a robot policy."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    initial_red: str
    final_red: str
    intervention: str
    blue_owner: str = "robot"
    human_available: bool = True


SCENARIOS = {
    "history_keep": Scenario(
        "history_keep", "先约定红杯留用，随后人把红杯移开；机器人应保留约定。",
        "keep", "keep", "move",
    ),
    "history_pack": Scenario(
        "history_pack", "先约定红杯收纳，随后发生相同移杯动作；机器人仍应完成收纳。",
        "pack", "pack", "move",
    ),
    "information_update": Scenario(
        "information_update", "人收到新用途信息后修正任务理解；先澄清，物体位置不变。",
        "pack", "keep", "information",
    ),
    "partner_available": Scenario(
        "partner_available", "机器人请求人完成蓝杯贡献，伙伴可用并执行。",
        "keep", "keep", "none", "human", True,
    ),
    "partner_unavailable": Scenario(
        "partner_unavailable", "相同初始分工下伙伴拒绝请求，机器人须重新承担蓝杯贡献。",
        "keep", "keep", "none", "human", False,
    ),
}
