# 24条合成公开状态控制（审核稿，未冻结、未推理）

全部system逐字沿用v13 state；这里只展示完整user与公开归约真值。真值是审核/评分元数据，不传入messages。

## direct_left_inactive_source

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "public_state_statement",
      "content": "有效外层blue投递目标是left。局部blue指导当前不活动。blue当前应执行的规范目标是left。上述目标是规范要求，实际所在区域不改变该目标。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.42,
          0,
          0.022
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "left", "guidance_active": false, "current_blue_destination": "left"}`

## direct_left_inactive_neutral

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "public_state_statement",
      "content": "有效外层blue投递目标是left。局部blue指导当前不活动。blue当前应执行的规范目标是left。上述目标是规范要求，实际所在区域不改变该目标。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          0,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "neutral"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "left", "guidance_active": false, "current_blue_destination": "left"}`

## direct_left_active_source

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "public_state_statement",
      "content": "有效外层blue投递目标是left。局部blue指导当前活动。blue当前应执行的规范目标是neutral。上述目标是规范要求，实际所在区域不改变该目标。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.42,
          0,
          0.022
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "left", "guidance_active": true, "current_blue_destination": "neutral"}`

## direct_left_active_neutral

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "public_state_statement",
      "content": "有效外层blue投递目标是left。局部blue指导当前活动。blue当前应执行的规范目标是neutral。上述目标是规范要求，实际所在区域不改变该目标。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          0,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "neutral"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "left", "guidance_active": true, "current_blue_destination": "neutral"}`

## scope_left_started_neutral

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "left",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "accepted_child",
      "content": "已接受blue局部指导并开始：暂存neutral；伙伴检查撤离后可finish_guidance终止。局部指导开始不取消外层约定。当前尚未检查，也尚未终止；blue实际区域可能仍在原外层盘或已在neutral。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          0,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "neutral"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "left", "guidance_active": true, "current_blue_destination": "neutral"}`

## scope_left_started_left

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "left",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "accepted_child",
      "content": "已接受blue局部指导并开始：暂存neutral；伙伴检查撤离后可finish_guidance终止。局部指导开始不取消外层约定。当前尚未检查，也尚未终止；blue实际区域可能仍在原外层盘或已在neutral。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "left"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "left", "guidance_active": true, "current_blue_destination": "neutral"}`

## scope_left_ended_neutral

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "left",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "accepted_child",
      "content": "已接受blue局部指导并开始：暂存neutral；伙伴检查撤离后可finish_guidance终止。局部指导开始不取消外层约定。"
    },
    {
      "kind": "action_feedback",
      "choice": "stage_blue_neutral",
      "content": "blue已暂存到neutral。"
    },
    {
      "kind": "inspection_started",
      "content": "伙伴检查进入共享通道，需要先yield。"
    },
    {
      "kind": "partner_released",
      "by": "yield",
      "content": "伙伴已撤离共享通道。"
    },
    {
      "kind": "local_check_passed",
      "content": "blue在neutral，局部检查通过，可终止指导。"
    },
    {
      "kind": "child_finished",
      "content": "finish_guidance已执行，当前局部指导明确终止。"
    },
    {
      "kind": "outer_resumed",
      "content": "恢复当时有效外层blue约定，其他分工与进度保留。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          0,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "neutral"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "left", "guidance_active": false, "current_blue_destination": "left"}`

## scope_left_ended_left

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "left",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "accepted_child",
      "content": "已接受blue局部指导并开始：暂存neutral；伙伴检查撤离后可finish_guidance终止。局部指导开始不取消外层约定。"
    },
    {
      "kind": "action_feedback",
      "choice": "stage_blue_neutral",
      "content": "blue已暂存到neutral。"
    },
    {
      "kind": "inspection_started",
      "content": "伙伴检查进入共享通道，需要先yield。"
    },
    {
      "kind": "partner_released",
      "by": "yield",
      "content": "伙伴已撤离共享通道。"
    },
    {
      "kind": "local_check_passed",
      "content": "blue在neutral，局部检查通过，可终止指导。"
    },
    {
      "kind": "child_finished",
      "content": "finish_guidance已执行，当前局部指导明确终止。"
    },
    {
      "kind": "outer_resumed",
      "content": "恢复当时有效外层blue约定，其他分工与进度保留。"
    },
    {
      "kind": "action_feedback",
      "choice": "place_blue_left",
      "content": "指导终止后blue已投递到left。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "left"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "left", "guidance_active": false, "current_blue_destination": "left"}`

## update_left_accepted_source

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "left",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "update_proposed",
      "proposal_id": "u1",
      "item": "blue",
      "destination": "right",
      "content": "提议将blue的有效外层投递目标调整为right；只调整blue外层投递，red/green约定不变。"
    },
    {
      "kind": "proposal_reply",
      "proposal_id": "u1",
      "decision": "accept",
      "content": "对该提议：接受。"
    },
    {
      "kind": "public_context",
      "content": "本例始终没有开始局部blue指导；只处理这一次外层提议与回应。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.42,
          0,
          0.022
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "right", "guidance_active": false, "current_blue_destination": "right"}`

## update_left_accepted_neutral

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "left",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "update_proposed",
      "proposal_id": "u1",
      "item": "blue",
      "destination": "right",
      "content": "提议将blue的有效外层投递目标调整为right；只调整blue外层投递，red/green约定不变。"
    },
    {
      "kind": "proposal_reply",
      "proposal_id": "u1",
      "decision": "accept",
      "content": "对该提议：接受。"
    },
    {
      "kind": "public_context",
      "content": "本例始终没有开始局部blue指导；只处理这一次外层提议与回应。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          0,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "neutral"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "right", "guidance_active": false, "current_blue_destination": "right"}`

## update_left_rejected_source

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "left",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "update_proposed",
      "proposal_id": "u1",
      "item": "blue",
      "destination": "right",
      "content": "提议将blue的有效外层投递目标调整为right；只调整blue外层投递，red/green约定不变。"
    },
    {
      "kind": "proposal_reply",
      "proposal_id": "u1",
      "decision": "reject",
      "content": "对该提议：拒绝。"
    },
    {
      "kind": "public_context",
      "content": "本例始终没有开始局部blue指导；只处理这一次外层提议与回应。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.42,
          0,
          0.022
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "left", "guidance_active": false, "current_blue_destination": "left"}`

## update_left_rejected_neutral

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "left",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "update_proposed",
      "proposal_id": "u1",
      "item": "blue",
      "destination": "right",
      "content": "提议将blue的有效外层投递目标调整为right；只调整blue外层投递，red/green约定不变。"
    },
    {
      "kind": "proposal_reply",
      "proposal_id": "u1",
      "decision": "reject",
      "content": "对该提议：拒绝。"
    },
    {
      "kind": "public_context",
      "content": "本例始终没有开始局部blue指导；只处理这一次外层提议与回应。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          0,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "neutral"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "left", "guidance_active": false, "current_blue_destination": "left"}`

## direct_right_inactive_source

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "public_state_statement",
      "content": "有效外层blue投递目标是right。局部blue指导当前不活动。blue当前应执行的规范目标是right。上述目标是规范要求，实际所在区域不改变该目标。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.42,
          0,
          0.022
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "right", "guidance_active": false, "current_blue_destination": "right"}`

## direct_right_inactive_neutral

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "public_state_statement",
      "content": "有效外层blue投递目标是right。局部blue指导当前不活动。blue当前应执行的规范目标是right。上述目标是规范要求，实际所在区域不改变该目标。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          0,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "neutral"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "right", "guidance_active": false, "current_blue_destination": "right"}`

## direct_right_active_source

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "public_state_statement",
      "content": "有效外层blue投递目标是right。局部blue指导当前活动。blue当前应执行的规范目标是neutral。上述目标是规范要求，实际所在区域不改变该目标。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.42,
          0,
          0.022
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "right", "guidance_active": true, "current_blue_destination": "neutral"}`

## direct_right_active_neutral

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "public_state_statement",
      "content": "有效外层blue投递目标是right。局部blue指导当前活动。blue当前应执行的规范目标是neutral。上述目标是规范要求，实际所在区域不改变该目标。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          0,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "neutral"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "right", "guidance_active": true, "current_blue_destination": "neutral"}`

## scope_right_started_neutral

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "right",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "accepted_child",
      "content": "已接受blue局部指导并开始：暂存neutral；伙伴检查撤离后可finish_guidance终止。局部指导开始不取消外层约定。当前尚未检查，也尚未终止；blue实际区域可能仍在原外层盘或已在neutral。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          0,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "neutral"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "right", "guidance_active": true, "current_blue_destination": "neutral"}`

## scope_right_started_right

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "right",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "accepted_child",
      "content": "已接受blue局部指导并开始：暂存neutral；伙伴检查撤离后可finish_guidance终止。局部指导开始不取消外层约定。当前尚未检查，也尚未终止；blue实际区域可能仍在原外层盘或已在neutral。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "right"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "right", "guidance_active": true, "current_blue_destination": "neutral"}`

## scope_right_ended_neutral

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "right",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "accepted_child",
      "content": "已接受blue局部指导并开始：暂存neutral；伙伴检查撤离后可finish_guidance终止。局部指导开始不取消外层约定。"
    },
    {
      "kind": "action_feedback",
      "choice": "stage_blue_neutral",
      "content": "blue已暂存到neutral。"
    },
    {
      "kind": "inspection_started",
      "content": "伙伴检查进入共享通道，需要先yield。"
    },
    {
      "kind": "partner_released",
      "by": "yield",
      "content": "伙伴已撤离共享通道。"
    },
    {
      "kind": "local_check_passed",
      "content": "blue在neutral，局部检查通过，可终止指导。"
    },
    {
      "kind": "child_finished",
      "content": "finish_guidance已执行，当前局部指导明确终止。"
    },
    {
      "kind": "outer_resumed",
      "content": "恢复当时有效外层blue约定，其他分工与进度保留。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          0,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "neutral"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "right", "guidance_active": false, "current_blue_destination": "right"}`

## scope_right_ended_right

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "right",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "accepted_child",
      "content": "已接受blue局部指导并开始：暂存neutral；伙伴检查撤离后可finish_guidance终止。局部指导开始不取消外层约定。"
    },
    {
      "kind": "action_feedback",
      "choice": "stage_blue_neutral",
      "content": "blue已暂存到neutral。"
    },
    {
      "kind": "inspection_started",
      "content": "伙伴检查进入共享通道，需要先yield。"
    },
    {
      "kind": "partner_released",
      "by": "yield",
      "content": "伙伴已撤离共享通道。"
    },
    {
      "kind": "local_check_passed",
      "content": "blue在neutral，局部检查通过，可终止指导。"
    },
    {
      "kind": "child_finished",
      "content": "finish_guidance已执行，当前局部指导明确终止。"
    },
    {
      "kind": "outer_resumed",
      "content": "恢复当时有效外层blue约定，其他分工与进度保留。"
    },
    {
      "kind": "action_feedback",
      "choice": "place_blue_right",
      "content": "指导终止后blue已投递到right。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "right"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "right", "guidance_active": false, "current_blue_destination": "right"}`

## update_right_accepted_source

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "right",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "update_proposed",
      "proposal_id": "u1",
      "item": "blue",
      "destination": "left",
      "content": "提议将blue的有效外层投递目标调整为left；只调整blue外层投递，red/green约定不变。"
    },
    {
      "kind": "proposal_reply",
      "proposal_id": "u1",
      "decision": "accept",
      "content": "对该提议：接受。"
    },
    {
      "kind": "public_context",
      "content": "本例始终没有开始局部blue指导；只处理这一次外层提议与回应。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.42,
          0,
          0.022
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "left", "guidance_active": false, "current_blue_destination": "left"}`

## update_right_accepted_neutral

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "right",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "update_proposed",
      "proposal_id": "u1",
      "item": "blue",
      "destination": "left",
      "content": "提议将blue的有效外层投递目标调整为left；只调整blue外层投递，red/green约定不变。"
    },
    {
      "kind": "proposal_reply",
      "proposal_id": "u1",
      "decision": "accept",
      "content": "对该提议：接受。"
    },
    {
      "kind": "public_context",
      "content": "本例始终没有开始局部blue指导；只处理这一次外层提议与回应。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          0,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "neutral"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "left", "guidance_active": false, "current_blue_destination": "left"}`

## update_right_rejected_source

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "right",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "update_proposed",
      "proposal_id": "u1",
      "item": "blue",
      "destination": "left",
      "content": "提议将blue的有效外层投递目标调整为left；只调整blue外层投递，red/green约定不变。"
    },
    {
      "kind": "proposal_reply",
      "proposal_id": "u1",
      "decision": "reject",
      "content": "对该提议：拒绝。"
    },
    {
      "kind": "public_context",
      "content": "本例始终没有开始局部blue指导；只处理这一次外层提议与回应。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.42,
          0,
          0.022
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "right", "guidance_active": false, "current_blue_destination": "right"}`

## update_right_rejected_neutral

```json

{
  "history": [
    {
      "kind": "background_source",
      "content": "公开事实合成的纯文本字段控制；未运行机器人或伙伴，不是实际物理轨迹。"
    },
    {
      "kind": "accepted_outer",
      "goals": {
        "red": "left",
        "blue": "right",
        "green": "right"
      },
      "content": "已共同接受blue外层投递目标；当前没有活动的局部blue指导。"
    },
    {
      "kind": "update_proposed",
      "proposal_id": "u1",
      "item": "blue",
      "destination": "left",
      "content": "提议将blue的有效外层投递目标调整为left；只调整blue外层投递，red/green约定不变。"
    },
    {
      "kind": "proposal_reply",
      "proposal_id": "u1",
      "decision": "reject",
      "content": "对该提议：拒绝。"
    },
    {
      "kind": "public_context",
      "content": "本例始终没有开始局部blue指导；只处理这一次外层提议与回应。"
    }
  ],
  "physical": {
    "objects": {
      "red": {
        "position": [
          0.59,
          -0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "blue": {
        "position": [
          0.65,
          0,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      },
      "green": {
        "position": [
          0.71,
          0.26,
          0.032
        ],
        "orientation": [
          0,
          0,
          0,
          1
        ],
        "velocity": [
          0,
          0,
          0
        ]
      }
    },
    "partner_position": [
      0.54,
      0.6,
      0.24
    ],
    "direct_path_blocked": false
  },
  "physical_placements": {
    "red": [
      "left"
    ],
    "blue": [
      "neutral"
    ],
    "green": [
      "right"
    ]
  },
  "remaining_decisions": 12,
  "candidates": [
    {
      "id": "place_red_left",
      "meaning": "独立沿共享通道抓放 red 到 left"
    },
    {
      "id": "careful_red_left",
      "meaning": "独立绕行抓放 red 到 left"
    },
    {
      "id": "assisted_red_left",
      "meaning": "利用已接受的清道协助抓放 red 到 left"
    },
    {
      "id": "place_red_right",
      "meaning": "独立沿共享通道抓放 red 到 right"
    },
    {
      "id": "careful_red_right",
      "meaning": "独立绕行抓放 red 到 right"
    },
    {
      "id": "assisted_red_right",
      "meaning": "利用已接受的清道协助抓放 red 到 right"
    },
    {
      "id": "place_blue_left",
      "meaning": "独立沿共享通道抓放 blue 到 left"
    },
    {
      "id": "careful_blue_left",
      "meaning": "独立绕行抓放 blue 到 left"
    },
    {
      "id": "assisted_blue_left",
      "meaning": "利用已接受的清道协助抓放 blue 到 left"
    },
    {
      "id": "place_blue_right",
      "meaning": "独立沿共享通道抓放 blue 到 right"
    },
    {
      "id": "careful_blue_right",
      "meaning": "独立绕行抓放 blue 到 right"
    },
    {
      "id": "assisted_blue_right",
      "meaning": "利用已接受的清道协助抓放 blue 到 right"
    },
    {
      "id": "place_green_left",
      "meaning": "独立沿共享通道抓放 green 到 left"
    },
    {
      "id": "careful_green_left",
      "meaning": "独立绕行抓放 green 到 left"
    },
    {
      "id": "assisted_green_left",
      "meaning": "利用已接受的清道协助抓放 green 到 left"
    },
    {
      "id": "place_green_right",
      "meaning": "独立沿共享通道抓放 green 到 right"
    },
    {
      "id": "careful_green_right",
      "meaning": "独立绕行抓放 green 到 right"
    },
    {
      "id": "assisted_green_right",
      "meaning": "利用已接受的清道协助抓放 green 到 right"
    },
    {
      "id": "request_clear",
      "meaning": "请求伙伴释放共享通道；不放置任何物品"
    },
    {
      "id": "yield",
      "meaning": "让伙伴先撤离占位物；不放置任何物品"
    },
    {
      "id": "finish_guidance",
      "meaning": "报告局部检查完成并终止当前指导/操作，不抓放"
    },
    {
      "id": "stage_blue_neutral",
      "meaning": "真实抓放blue到独立neutral检查盘，触发伙伴脚本检查"
    }
  ]
}

```

公开归约真值：`{"outer_blue_destination": "right", "guidance_active": false, "current_blue_destination": "right"}`
