"""下一版日常任务的明确需要；定义成果与信息边界，不定义策略或动作顺序。"""
from dataclasses import replace

from .interaction_contracts import CONTRACTS


PUBLIC_DESCRIPTIONS={
    'snack_service':(
        'Prepare an actual snack kit and serving arrangement for a guest together. '
        'The food item is cream_cheese_1, the bowl is akita_black_bowl_1, and plate_1 can support the bowl as a tray. '
        'An empty bowl or arranged dishware alone does not satisfy the food need. '
        'The human knows how and when the guest will use the kit. '
        'The robot has declared operations for filling and arranging available containers; '
        'the human can provide containers, arrange or receive items, or take over a contribution. '
        'Agree on contributions using public speech and visible state. '
        'A held or moving container is different from a released available one. '
        'Preserve the food need when changing where or how the kit is collected, unless that need is explicitly revised.'),
    'drink_storage':(
        'Organize wine_bottle_1 and clear the drink workspace for its next use. '
        'The human knows the household use plan; the bottle destination is not yet a shared agreement. '
        'Rack storage and temporary cabinet placement serve different purposes. '
        'The human can provide or retain the bottle and clear personal dishware. '
        'The robot can perform its declared bottle and dishware operations or request clarification and assistance. '
        'Establish what is needed and who contributes before treating a proposed action as assigned to the other agent. '
        'A placement must be distinguished from releasing the object and making it usable by the partner.'),
    'drawer_access':(
        'Clear the work area and make the middle drawer usable for the human personal storage or access need. '
        'plate_1 is a human personal item to clear or retain, separate from the item needing storage. '
        'The object needing storage or retrieval is a separate fact that the human can communicate. '
        'The robot can open the drawer and ask about the needed item, workspace clearance or participation. '
        'Drawer opening alone does not complete the personal storage need. '
        'Use observable drawer state and actual item placement when coordinating. '
        'Participation and item use can change; preserve completed contributions and clarify remaining needs.'),
}

PRIVATE_NEEDS={
    'snack_service':(
        '你要为朋友准备可实际取用的点心套装，不只是整理空容器。食品是cream_cheese_1，'
        '容器是akita_black_bowl_1，plate_1可作托盘；食品与容器身份不同。'
        '起初朋友计划在桌边取用，准备好的食品应可取用且不被任何一方继续占着。'
        '朋友的取用时间和堂食／带走计划是你的私人信息。新情况可以改变这些需要及你的可用性。'
        '改变摆放或堂食／带走方式本身不取消食品需要；如要取消或替换需要，应有生活情境依据并考虑公开说明。'
        '你可以决定承担什么、请机器人帮什么、暂缓或拒绝；这里没有规定谁必须先做哪一步。'),
    'drink_storage':(
        '你起初希望把wine_bottle_1长期收在酒架，并整理台面以便下一次使用。'
        '柜顶可以暂放，但不是原来长期收纳需要已经满足的证明。近期是否马上取用只有你知道。'
        '你还可以清理或保留自己的plate_1；这与酒瓶的用途是不同需要。'
        '新来客、用餐或日程信息可以使你改变留用／收纳、优先级和参与意愿。'
        '你对伙伴提出的请求可以接受、修改、拒绝或先澄清，新的需要不等于新的动作已完成。'
        '你的提议是自己愿意做什么或希望对方做什么，要依实际表达和对方回应建立分工。'),
    'drawer_access':(
        '你起初希望把cream_cheese_1收进中层抽屉，并清理工作区域。'
        'plate_1是自己的盘子，需要清理或保留；它不是拟存物品cream_cheese_1。'
        '你可以改变存取对象和用途，但要依据新需要说明，不因手里恰好有盘子就把两件物品当作同一需要。'
        '你也有私人联系和日程，是否处理、离开或返回取决于事情的重要性、当前进度及伙伴的贡献。'
        '返回时根据已经发生的结果重新考虑尚有需要的部分；需要合理取消或已满足时无需强行继续。'),
}


WORKSPACE_CONTRACTS={key:replace(contract,activity=replace(contract.activity,
    public_description=PUBLIC_DESCRIPTIONS[key]+(
        ' serving_ready is the operation preparation surface; snack_delivery is the guest collection surface; '
        'drink_staging is a human-side temporary-use surface. These are different locations, '
        'not accepted assignments or guarantees of robot manipulation success.'),
    private_background=PRIVATE_NEEDS[key]))
    for key,contract in CONTRACTS.items()}
