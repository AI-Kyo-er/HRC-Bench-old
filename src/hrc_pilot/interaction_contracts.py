"""日常共同活动契约：约束信息与贡献意义，不按阶段选择人或机器人动作。"""
from dataclasses import dataclass

from .joint_activity import JointActivity


@dataclass(frozen=True)
class InteractionContract:
    activity: JointActivity
    jointly_organize: str
    human_contributions: tuple[str,...]
    robot_contributions: tuple[str,...]
    human_private_information: tuple[str,...]
    observable_channels: tuple[str,...]
    unresolved_questions: tuple[str,...]
    evidence_requirements: tuple[str,...]

    def public(self):
        return {'activity':self.activity.public(),'jointly_organize':self.jointly_organize,
            'possible_human_contributions':list(self.human_contributions),
            'possible_robot_contributions':list(self.robot_contributions),
            'observable_channels':list(self.observable_channels),
            'questions_that_can_be_resolved_by_interaction':list(self.unresolved_questions),
            'scope':'可协商的活动契约，非动作队列、已达成约定、私人需要真值或当前完成评分。'}


CONTRACTS={c.activity.key:c for c in [
    InteractionContract(
        JointActivity('snack_service','food_into_bowl','来客接待：点心、饮品与取用安排',
            'Prepare a guest snack and drink setting together. The human knows the guest plans and their own availability. '
            'The robot can prepare or fill an available bowl and arrange dishware using its declared operations. '
            'The human can make containers available, arrange the plate, receive or serve prepared food, and handle a drink. '
            'Negotiate which contribution is needed now and where objects should remain usable. '
            'Filling requires an available container; delivering a bowl is different from delivering prepared food. '
            'Guest use and work order can change. Preserve completed contributions and resolve unfinished needs.',
            ('container made available -> robot food contribution',
             'food physically prepared and released -> human can serve',
             'guest use or availability changes -> arrangement may require public revision'),
            '你在准备接待来客，希望最后能方便取用点心与饮品。你愿意提供容器和负责取用，'
            '但不是在任何情况下都要立刻领取。客人的计划及你的个人安排只有你知道；'
            '可以调整先后、拒绝不合适的安排或临时离开，重要改变需要给伙伴可观察的线索。',
            '客人的到达和取用计划发生变化；根据实际进度决定是否调整共同安排。'),
        '可用的点心、饮品及取用位置，不只是让一个空碗到点。',
        ('提供或保留容器','安排餐盘和取用位置','接收或服务准备好的点心','说明来客需要与自己的参与'),
        ('准备容器／摆放碗盘','填装可用容器','询问优先级、提供位置或参与意愿'),
        ('客人的取用顺序与时间','自己的可用性及是否愿意参与'),
        ('实际公开语言','容器和餐盘的位置及持物','手势、等待、离开和返回'),
        ('人是否已提供容器？','现在先准备什么？','成品是否真正可取用？'),
        ('实际容器关系与释放','人的需要变化及公开线索','双方分工与后续反馈','当前安排下的结果')),
    InteractionContract(
        JointActivity('drink_storage','bottle_on_rack','饮品整理：留用、收纳与台面安排',
            'Organize drink supplies while preserving the human household needs. There is no default bottle destination. '
            'The human knows whether wine_bottle_1 is needed soon or can be stored and can communicate a proposal. '
            'The robot can use its declared operations to arrange an available bottle and dishware, or ask for clarification. '
            'Cabinet placement and rack storage are different available operations, not an agreed preference. '
            'Confirm or visibly ground the current use before treating a destination as the shared arrangement. '
            'The human can revise use, take over a contribution, or ask the robot to continue after releasing resources.',
            ('human use information becomes observable -> bottle arrangement can be selected',
             'available bottle -> robot can perform an agreed manipulation',
             'use clarification or takeover -> preserve or revise remaining contributions'),
            '你在整理饮品和台面物品，知道家里近期的使用计划。起初倾向把酒瓶收起来，'
            '但新情况可以使你临时保留。你手里拿酒瓶不表示已同意机器人上架。'
            '你可以主动说明或回答询问；不要用机器人尚不知道的私人计划判断它应该已经知道目的地。',
            '家里的饮品使用计划有新说明；根据目前安排决定保留、纠正或继续。'),
        '台面整理与饮品用途，不预先把酒架指令当作双方已同意的目标。',
        ('提供物品','决定和公开留用／收纳需求','核对安排','接管、保留或交还工作'),
        ('上架或柜顶等已声明操作','核对物品是否可操作','询问用途、位置或分工'),
        ('近期饮品使用计划','个人偏好与保留意愿'),
        ('回答与提议','实际提供、收回或放置物品','指示与等待'),
        ('现在留用还是收纳？','当前位置是暂放还是最终约定？','谁正在使用这个资源？'),
        ('公开选择与确认','当前约定下的位置和释放','变更后的继续／接管／交还')),
    InteractionContract(
        JointActivity('drawer_access','drawer_access','个人物品整理：工作区与抽屉取用',
            'Make the drawer area usable for the human personal storage and access needs. '
            'The human can clear or retain their plate and knows which personal item currently needs storage or immediate use. '
            'The robot can open the middle drawer using its declared operation and ask which item or access arrangement is needed. '
            'Moving a plate out of the way does not mean that the plate is the intended storage item. '
            'Drawer opening and completed personal storage are different contributions. '
            'Participation may pause or resume; use public signals to preserve the current arrangement and unfinished work.',
            ('workspace access and consent -> robot drawer contribution',
             'drawer becomes accessible -> human can store or retrieve the selected item',
             'absence or changed item use -> continuation needs updated public arrangement'),
            '你希望把奶酪放入抽屉并清理工作区。初始拿盘子是为了清理或保留自己的物品，'
            '不等于要把盘子代替奶酪收进抽屉。你可以改变存储需求，但需要说明原因和新的安排。'
            '你还可能处理私人联系，是否暂离、回来或让机器人继续应依据实际需要。',
            '私人联系或物品使用需要有变化；结合已完成和未完成贡献决定是否继续。'),
        '明确的个人物品取用需求及可用工作区，开抽屉不是整个活动完成。',
        ('清理或保留个人盘子','公开需要存取的物品','存储／取回物品','协调自己的可用性'),
        ('打开可用抽屉','请求清理空间或澄清物品需求','保留进度并询问后续分工'),
        ('要存储或借用哪件个人物品','私人联系和参与意愿'),
        ('指示、提议和回应','障碍物、持物及抽屉实际状态','暂离／返回及实际后续动作'),
        ('入口是否可用？','哪件物品需要存取？','人暂停后哪些工作仍未完成？'),
        ('实际抽屉状态和物品关系','对象身份与公开安排一致性','暂离返回或拒绝后的连续性')),
]}


def validate_contracts():
    for key,contract in CONTRACTS.items():
        if key!=contract.activity.key or not contract.activity.dependencies:
            raise ValueError('活动标识和跨主体依赖必须明确')
        if not all([contract.human_contributions,contract.robot_contributions,
                    contract.human_private_information,contract.observable_channels,contract.unresolved_questions]):
            raise ValueError('双方贡献、信息不对称及可观察渠道不能缺少')
        if {'private_background','external_context','human_private_information','evidence_requirements'}.intersection(contract.public()):
            raise ValueError('私有信息或评价口径不能当作公开事实')
    return True
