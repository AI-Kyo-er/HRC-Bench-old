"""将外部生活事实绑定到具体活动／物品；不生成双方的动作或下一策略。"""
from copy import deepcopy


ACTIVITY_CUES={
    'snack_service':{
        'join':('朋友发来消息：与你一起核对的私人安排已经处理完，你现在有空参与桌边的点心准备。',),
        'leave_return':('同事联系你讨论一个紧急且私人的问题，希望现在简短通话；点心的接收碗akita_black_bowl_1仍是桌边共同使用的物品。',
                        '同事告知问题已经处理完，这次联系不再需要你的注意。'),
        'change_use':('朋友临时需要带走准备好的点心，plate_1餐盘作为托盘、盛点心的akita_black_bowl_1放在餐盘上会更方便；原先仅在桌边取用单个碗的安排不再适合这次需要。',),
        'detour':('来客说马上到达，想先喝桌边wine_bottle_1中的饮品，点心可以稍后取用。',
                   '来客告知行程改变，暂时不需要饮品，原先的点心安排仍有需要。'),
        'correction':('家人澄清：akita_black_bowl_1是要交还给另一位家人的空碗；先前以为它可以盛当前点心的理解需要重新讨论。',),
        'robot_request':('你收到日程提醒：个人事务很快需要你的注意；你还未确定能额外参与多久，是否帮助取决于机器人提出的具体需要。',),
    },
    'drink_storage':{
        'join':('你刚处理的私人事务已经结束；家里仍有整理wine_bottle_1和饮品台面的共同需要。',),
        'leave_return':('同事联系你讨论一个紧急且私人的问题，希望现在简短通话；你原本与机器人一起整理wine_bottle_1。',
                        '同事告知问题已经处理完，这次联系不再需要你的注意。'),
        'change_use':('来客提前到达，wine_bottle_1这瓶酒现在需要在台面柜顶暂放以便马上取用，而不是长期收在酒架；家人不知道当前整理进度。',),
        'detour':('家人发来消息，马上需要plate_1这只餐盘用餐；饮品的长期收纳没有同样紧迫。',
                   '家人说明用餐推迟，餐盘暂时没有额外需要，饮品整理仍可继续。'),
        'correction':('家人澄清：wine_bottle_1这瓶酒是马上要在台面柜顶取用的个人物品；之前把它当成待长期收进酒架的安排有误。',),
        'robot_request':('你收到日程提醒：个人事务很快需要你的注意；当前酒瓶wine_bottle_1的取用安排由你决定，额外协助取决于请求和剩余时间。',),
    },
    'drawer_access':{
        'join':('你刚处理的私人事务已经结束；桌边仍有清理抽屉入口和整理cream_cheese_1的共同需要。',),
        'leave_return':('同事联系你讨论一个紧急且私人的问题，希望现在简短通话；你原本与机器人一起清理抽屉和整理cream_cheese_1。',
                        '同事告知问题已经处理完，这次联系不再需要你的注意。'),
        'change_use':('家人马上要取用cream_cheese_1准备点心，不再需要将这包奶酪收进抽屉；家人不知道抽屉整理是否已完成。',),
        'detour':('来客说马上到达，希望先取用wine_bottle_1中的饮品；抽屉收纳可以稍后处理。',
                   '来客告知行程改变，暂时不需要饮品，抽屉整理仍有需要。'),
        'correction':('家人澄清：cream_cheese_1这包奶酪是接下来用餐需要的物品，之前准备将它长期收进抽屉的安排有误。',),
        'robot_request':('你收到日程提醒：个人事务很快需要你的注意；抽屉入口附近plate_1是你可以处理的个人物品，是否协助取决于具体请求。',),
    },
}


def specialize_private_context(sampled,activity):
    value=deepcopy(sampled)
    texts=ACTIVITY_CUES[activity][sampled['situation']]
    if len(texts)!=len(value['private_cues']):raise ValueError('外部事实数量与采样时间窗不一致')
    for cue,text in zip(value['private_cues'],texts):cue['text']=text
    value['context_design']='activity_specific_external_facts_v1'
    value['interpretation']='外部事实涉及具体物品／需要；是否接受、表达、改变、接管或坚持由在线策略决定。'
    return value
