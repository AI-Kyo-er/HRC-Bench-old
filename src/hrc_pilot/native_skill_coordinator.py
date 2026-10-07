"""视觉协调系统的明确操作接口；只编码模型所选execute，不选择何时执行。"""
from .robot_coordination import validate_decision


SYSTEM=(
    '你是共同活动中的机械臂协调策略。根据当前真实相机、自身传感器和公开交流决定下一步。'
    '图片依次为初始外部相机、当前外部相机和当前腕部相机；没有人的私人需要或任务评分。'
    'history是你的旧想法，不是当前世界事实；self_execution仅记录实际控制和自身传感器。'
    '你有两种工具：execute执行available_vla_operation；hold保持当前位置和抓持状态。'
    '是否执行由你根据实际活动、人的公开要求和画面决定，程序不会按任务阶段选下一步。'
    '可公开请求协助、澄清或重新分工，回应人的接受、修改或拒绝。'
    '不要把消息、旧计划或一次控制块当操作已完成；不要编造图像中没有发生的物品状态。'
    '人持有或移动容器时不要假设容器已经准备好。保持可能等待，但不等于自动让开。'
    'execute只代表选择已公布的模型支持操作，不支持直接末端运动或任意新抓放技能。'
    '只输出完整JSON：mode（execute/hold）、instruction（execute填写available_vla_operation）、'
    'message（简短英文）、reason、memory_note、current_goal。')


def native_operation(public_task):
    if '\nShared activity: ' not in public_task:
        raise ValueError('原生技能接口需要明确公开的原生任务与活动说明')
    operation=public_task.split('\nShared activity: ',1)[0].strip()
    if not operation:raise ValueError('原生公开操作为空')
    return operation


def encode_selected_operation(raw,operation):
    decision,error=validate_decision(raw)
    generated=decision['instruction']
    selected=None
    if decision['mode']=='move_ee':
        decision={'mode':'hold','instruction':'','message':'','reason':'本系统只支持公开的VLA操作或保持。',
                  'memory_note':'','current_goal':'','plan':[]}
        error='unsupported_direct_motion'
    elif decision['mode']=='execute' and error is None:
        selected='available_vla_operation';decision['instruction']=operation
    return decision,error,{'generated_instruction':generated,'model_selected_operation':selected,
                           'interpretation':'execute由神经策略选择；适配器仅编码公开的已支持操作，不按任务状态调度。'}
