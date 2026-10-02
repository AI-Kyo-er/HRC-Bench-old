# v15运行前公开协议变更

```diff
--- v11
+++ v15
@@ -2,7 +2,7 @@
 公开历史中的已接受约定由脚本共同背景预置，不表示你亲自协商。
 局部blue指导要求真实暂存到neutral检查盘；伙伴进入检查后先yield让其撤离。
 外层blue投递调整只有对应提议被接受才生效，拒绝保留原约定。指导期间的已接受外层调整不取消neutral检查，终止指导后按最新有效外层约定投递；red/green约定及物理进度保留。
-stage_blue_neutral执行上述暂存。检查通过后finish_guidance终止局部指导并恢复当时有效外层blue约定，不移动物品；red/green约定与已实现进度保留。
+stage_blue_neutral执行上述暂存。局部指导活动且实际检查通过、伙伴已撤离时，伙伴公开交还blue即终止局部指导并恢复当时有效外层blue约定，不移动物品；不需机器人再finish_guidance。机器人也可在满足检查条件时用finish_guidance主动终止；已终止后重复finish_guidance无效。red/green约定与已实现进度保留。
 place直接抓放；careful绕行；assisted需已接受清道协助；request_clear只求清道；yield让行，可合法但不推进物品。
 全部22候选是公开通用能力集合，包含当前错误或不可执行动作，拒绝与额外动作计决策成本并提供反馈。
 依据公开原始历史和真实区域继续任务，自主选择尚未满足约定的物品。
```

accepted_child：

旧：已接受blue局部指导：暂存neutral，伙伴检查并撤离后可finish_guidance终止，恢复当时有效外层blue约定；red/green继续原约定。

新：已接受blue局部指导：暂存neutral，实际检查通过且伙伴已撤离后，伙伴明确交还或机器人finish_guidance均可终止，恢复当时有效外层blue约定；red/green继续原约定。

local_check_passed原“可终止指导”保持；伙伴交还不透露左右。以下仅旧实际D4承载计划事件的审核样例，不是新轨迹。

```json
[
  {
    "kind": "background_source",
    "content": "脚本预置初始共同接受背景，非模型协商。"
  },
  {
    "kind": "accepted_outer",
    "goals": {
      "red": "left",
      "blue": "left",
      "green": "right"
    },
    "content": "已共同接受外层目标，允许自主物品顺序。"
  },
  {
    "kind": "prefix_action",
    "content": "red已真实放到left并停车。"
  },
  {
    "kind": "update_proposed",
    "proposal_id": "u1",
    "item": "blue",
    "destination": "right",
    "content": "只调整blue检查结束后的外层投递；neutral检查与red/green约定不变。"
  },
  {
    "kind": "proposal_reply",
    "proposal_id": "u1",
    "decision": "accept",
    "content": "对该提议：接受。"
  },
  {
    "kind": "accepted_child",
    "content": "已接受blue局部指导：暂存neutral，实际检查通过且伙伴已撤离后，伙伴明确交还或机器人finish_guidance均可终止，恢复当时有效外层blue约定；red/green继续原约定。"
  },
  {
    "kind": "inspection_started",
    "content": "伙伴真实进入共享通道进行脚本检查，已接受顺序要求先yield令其撤离。"
  },
  {
    "kind": "action_feedback",
    "choice": "stage_blue_neutral",
    "content": "物品静止在目标槽"
  },
  {
    "kind": "partner_released",
    "by": "yield",
    "content": "伙伴实际撤离共享通道。"
  },
  {
    "kind": "local_check_passed",
    "content": "伙伴脚本依据实际blue在neutral的位姿完成检查，可终止指导。"
  },
  {
    "kind": "action_feedback",
    "choice": "yield",
    "content": "伙伴已撤离，现有物品约定继续有效。"
  },
  {
    "kind": "action_feedback",
    "choice": "place_green_right",
    "content": "物品静止在目标槽"
  },
  {
    "kind": "partner_handoff",
    "content": "局部检查已结束，现在交还blue，按当前有效外层约定继续。"
  }
]
```
