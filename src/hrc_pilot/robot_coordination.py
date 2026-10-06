"""视觉协调器的公共请求、命令校验与保持姿态原语，不包含任务路由。"""
import base64
from hashlib import sha256
from io import BytesIO
import json

import numpy as np
from PIL import Image


PUBLIC_KEYS={'time_s','robot_task','human_task','dialogue','state','images','history','current_goal'}


def image_payload(pixels):
    rgb=np.asarray(pixels)
    if rgb.ndim!=3 or rgb.shape[2]!=3 or rgb.dtype!=np.uint8:raise ValueError('需要真实RGB uint8相机帧')
    buffer=BytesIO();Image.fromarray(rgb).save(buffer,format='PNG')
    return {'png_base64':base64.b64encode(buffer.getvalue()).decode(),
            'rgb_sha256':sha256(rgb.tobytes()).hexdigest()}


def decode_image(payload):
    image=Image.open(BytesIO(base64.b64decode(payload['png_base64']))).convert('RGB')
    assert sha256(np.asarray(image).tobytes()).hexdigest()==payload['rgb_sha256']
    return image


def coordination_request(*, time_s, robot_task, human_task, dialogue, state, images, history, current_goal):
    state=np.asarray(state,dtype=float)
    if state.shape!=(8,) or not np.isfinite(state).all():raise ValueError('需要机械臂自身8维状态')
    return {'time_s':float(time_s),'robot_task':robot_task,'human_task':human_task,
            'dialogue':[{'speaker':m.speaker,'kind':m.kind,'text':m.text} for m in dialogue[-20:]],
            'state':state.tolist(),'images':{key:image_payload(value) for key,value in images.items()},
            'history':history[-6:],'current_goal':current_goal}


def validate_decision(raw):
    error=None
    try:
        value=json.loads(raw[raw.find('{'):raw.rfind('}')+1])
        if not isinstance(value,dict) or value.get('mode') not in {'execute','hold'}:raise ValueError('mode必须为execute或hold')
        if value['mode']=='execute' and (not isinstance(value.get('instruction'),str) or not value['instruction'].strip()):raise ValueError('execute必须给出运动目标指令')
    except (ValueError,TypeError) as exc:
        error=str(exc);value={'mode':'hold','reason':'输出无效，维持当前姿态。'}
    decision={key:str(value.get(key,''))[:500] for key in ['mode','instruction','message','reason','memory_note','current_goal']}
    decision['message']=decision['message'][:240]
    decision['plan']=[str(v)[:180] for v in value.get('plan',[])[:5]] if isinstance(value.get('plan',[]),list) else []
    return decision,error


def hold_actions(state, steps):
    """执行模型选择的保持姿态；根据自身夹爪开度维持开/闭，不选协作策略。"""
    state=np.asarray(state,dtype=float)
    actions=np.zeros((steps,7),dtype=float)
    actions[:,-1]=-1. if np.abs(state[-2:]).sum()>=.04 else 1.
    return actions


class CoordinatorClient:
    def __init__(self, port):
        import requests
        self.session=requests.Session();self.session.trust_env=False
        self.url=f'http://127.0.0.1:{port}'
        response=self.session.get(self.url+'/metadata',timeout=10);response.raise_for_status()
        self.metadata=response.json()

    def infer(self, request):
        if set(request)!=PUBLIC_KEYS:raise ValueError('协调器只能读取公开请求字段')
        response=self.session.post(self.url+'/infer',json=request,timeout=180);response.raise_for_status()
        return response.json()
