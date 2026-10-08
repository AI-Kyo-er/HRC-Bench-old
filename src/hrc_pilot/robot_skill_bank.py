"""公开的LIBERO-goal指令库：神经策略选技能，适配器不读取任务进度。"""
import json

from .robot_coordination import CoordinatorClient,PUBLIC_KEYS,validate_decision


SKILLS={
    'open_middle_drawer':'open the middle drawer of the cabinet',
    'bowl_on_stove':'put the bowl on the stove',
    'bottle_on_cabinet':'put the wine bottle on top of the cabinet',
    'bowl_inside_top_drawer':'open the top drawer and put the bowl inside',
    'bowl_on_cabinet':'put the bowl on top of the cabinet',
    'plate_front_stove':'push the plate to the front of the stove',
    'cream_in_bowl':'put the cream cheese in the bowl',
    'bowl_on_plate':'put the bowl on the plate',
    'bottle_on_rack':'put the wine bottle on the rack',
}
# 额外语言操作不属于已验证的LIBERO技能；仍须由真实VLA生成动作。
WITHDRAW_OPERATION={'withdraw_from_workspace':'move the gripper up and away from the objects and the open drawer'}
SYSTEM=(
    '你是与人共同活动的机器人协调策略。依据实际观察、自身执行与公开交流决定当前贡献。'
    'available_vla_operations是公开的原生操作指令库，不是待执行队列，也不是已经验证成功的技能保证。'
    '原始任务描述不是当前强制动作。当前安排由公开提议、回应与实际进度形成，可以变化或取消。'
    '只有两种mode：execute从公开技能库选择一个skill_id，交由真实VLA执行；hold保持并可公开协调。'
    '你可以依据伙伴公开的新用途选择另一个已有技能；不要把人的私有需要、评分或未发生的动作当依据。'
    'history是以前的想法，self_execution是已经发生的控制。先核对当前世界，不凭消息宣布完成。'
    '人可以接受、修改或拒绝你的请求。人持有物品或尚未准备好时，不要假定已提供。'
    '不支持直接末端移动、瞬移或后台完成。你选择何时执行、哪个技能及当前公开表达。'
    '只输出完整JSON：mode（execute/hold）、skill_id（execute必须是公开库里的名字）、'
    'message（简短英文）、reason、memory_note、current_goal。不要输出动作清单。')


def encode_skill_selection(raw,operations):
    selected=None;generated=None
    try:
        value=json.loads(raw[raw.find('{'):raw.rfind('}')+1])
        if value.get('mode') not in {'execute','hold'}:raise ValueError('技能库只支持execute或hold')
        if value['mode']=='execute':
            selected=value.get('skill_id')
            if selected not in operations:raise ValueError('所选技能不在公开库中')
            generated=value.get('instruction')
            value['instruction']=operations[selected]
        decision,error=validate_decision(json.dumps(value,ensure_ascii=False))
    except (ValueError,TypeError,AttributeError) as exc:
        error=str(exc);selected=None
        decision={'mode':'hold','instruction':'','message':'','reason':'无效技能选择，维持现场。',
                  'memory_note':'','current_goal':'','plan':[]}
    return decision,error,{'model_selected_skill_id':selected,'generated_instruction':generated,
        'interpretation':'技能由神经策略从公开库选择；只编码其指令，没有任务状态路由或成功保证。'}


class SkillBankCoordinatorClient(CoordinatorClient):
    def infer(self,request):
        if set(request)!=PUBLIC_KEYS|{'available_vla_operations'}:
            raise ValueError('视觉技能库协调器只读取明确公开字段')
        response=self.session.post(self.url+'/infer',json=request,timeout=180)
        response.raise_for_status();return response.json()
