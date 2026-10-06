"""录制同一模拟时刻的广角、模型外部相机与腕部相机；不是轨迹重渲染。"""
import numpy as np
from PIL import Image, ImageDraw


def compose_runtime_views(wide_rgb,observation,layout='wide'):
    if layout=='wide':return np.ascontiguousarray(wide_rgb)
    if layout!='wide_and_policy':raise ValueError('未知视频布局')
    exterior=np.ascontiguousarray(observation['agentview_image'][::-1,::-1])
    wrist=np.ascontiguousarray(observation['robot0_eye_in_hand_image'][::-1,::-1])
    if wide_rgb.shape!=(480,640,3) or exterior.shape!=(256,256,3) or wrist.shape!=(256,256,3):
        raise ValueError('多机位运行视频需要640×480广角与两路256×256相机')
    canvas=np.full((512,896,3),24,dtype=np.uint8)
    canvas[16:496,:640]=wide_rgb;canvas[:256,640:]=exterior;canvas[256:,640:]=wrist
    frame=Image.fromarray(canvas);draw=ImageDraw.Draw(frame)
    for point,label in [((8,0),'Runtime wide Sim'),((648,0),'Policy exterior'),((648,256),'Policy wrist')]:
        draw.text(point,label,fill='white',stroke_width=1,stroke_fill='black')
    return np.asarray(frame)
