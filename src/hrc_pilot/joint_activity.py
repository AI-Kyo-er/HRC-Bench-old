"""共同活动的语义定义；不调度人或机器人的动作。"""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class JointActivity:
    key: str
    scene_case: str
    label: str
    public_description: str
    dependencies: tuple[str, ...]
    private_background: str
    external_context: str

    def public(self):
        return {k:v for k,v in asdict(self).items()
                if k not in {'private_background','external_context'}}


ACTIVITIES={a.key:a for a in [
    JointActivity('snack_service','food_into_bowl','共同准备点心',
        'Prepare a snack together. The human provides the akita_black_bowl_1 as a serving container; '
        'the robot puts cream_cheese_1 into that bowl. The human receives or serves the prepared snack. '
        'Agree on timing and placement using visible actions and public speech. '
        'Do not fill a container while the human is moving it. Current requests can revise the arrangement.',
        ('human prepares serving container -> robot fills it',
         'robot finishes filling and releases -> human serves or receives snack'),
        '你希望与机器人准备点心，起初愿意提供碗并负责最后取用。你有自己的需要，可以协商。'
        '你还可能要接电话；无需为了展示变化而改变意图。',
        '朋友发来消息：临时有事，点心需要打包带走而不是在桌边吃。你可依据实际进度考虑怎么处理。'),
    JointActivity('drink_storage','bottle_on_rack','共同整理饮品',
        'Organize the drinks together. The human decides which drink to keep available and stages '
        'wine_bottle_1 for storage if desired. The robot places the staged wine_bottle_1 on the wooden rack. '
        'The human checks the arrangement and clears personal belongings. Respect publicly changed needs '
        'and do not manipulate an object the partner is holding.',
        ('human communicates keep/store choice and makes bottle available -> robot stores',
         'robot releases stored bottle -> human checks arrangement or requests a correction'),
        '你起初希望把酒瓶收进酒架，自己负责台面整理和确认。你可以决定临时留用酒瓶；'
        '不要假设机器人已经理解你没说的话。',
        '收到来客消息：客人提前到了，可能马上需要桌边的饮品。根据目前安排决定是否调整。'),
    JointActivity('drawer_access','drawer_access','共同清理取用区',
        'Clear and organize the drawer area together. The human prepares access by moving personal '
        'tabletop items out of the way. The robot opens the middle drawer. The human then stores '
        'cream_cheese_1 in the accessible drawer or publicly revises its intended use. '
        'Coordinate access and wait while the partner is using the same area.',
        ('human clears access -> robot opens middle drawer',
         'robot makes drawer accessible -> human stores or retrieves personal item'),
        '你起初希望与机器人整理抽屉，自己负责清理和放入奶酪。你可能需要暂时离开，'
        '也可以接手或请求机器人协助，但不要把观察或发消息当成完成整理。',
        '家人询问能否先借用奶酪准备点心；你可根据当前整理进度选择先借用、继续收纳或协商。'),
]}


PROFILES={
    'participating':'愿意承担互补工作，表达简短明确；有新需要时会协商，而非无理由频繁改变。',
    'busy':'还有别的事情要处理；会说明暂离或交接，返回后核对进度，不必把全部工作抢回来。',
    'particular':'对物品用途和布置有偏好；发现不符合需要时解释原因、纠正或接手，也会接受合理建议。',
}
