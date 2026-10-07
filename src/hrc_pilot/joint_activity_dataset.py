"""按实际观测stem加载共同活动动作块，私有研究记录不进入机器人输入。"""
import json
from pathlib import Path

import numpy as np
from PIL import Image


class JointActivityDataset:
    def __init__(self,root):
        self.root=Path(root)
        self.episodes=sorted(p.parent for p in self.root.rglob('model_calls.jsonl'))
        self.samples=[]
        for ep in self.episodes:
            for line in (ep/'model_calls.jsonl').read_text().splitlines():
                if line.strip():self.samples.append((ep,json.loads(line)))

    def __len__(self):return len(self.samples)

    def __getitem__(self,index):
        ep,call=self.samples[index];stem=f'observation_{call["step"]:06d}'
        source={'image':np.asarray(Image.open(ep/(stem+'.png')).convert('RGB')),
            'wrist_image':np.asarray(Image.open(ep/(stem+'_wrist.png')).convert('RGB')),
            'state':np.load(ep/(stem+'_state.npy')),'prompt':call['prompt']}
        target=np.load(ep/(stem+'_actions.npy'))
        if target.shape!=(call['executed_action_count'],7):raise ValueError('动作块与原始推理长度不一致')
        # 推理动作块可在新的公开消息到来时被提前中断，必须用实际control还原标签。
        actual=[]
        for line in (ep/'robot_control.jsonl').read_text().splitlines():
            if line.strip():
                c=json.loads(line)
                if c['model_call_id']==call['call_id']:actual.append(c['action'])
        executed=np.asarray(actual,dtype=float).reshape(-1,7)
        np.testing.assert_allclose(executed,target[:len(executed)])
        return source,executed,{'episode':ep.name,'stem':stem,'action_source':call['action_source'],
            'role':'actual_behavior_not_success_expert_label','planned_block_steps':len(target),
            'executed_block_steps':len(executed),'truncated_by_reobservation':len(executed)<len(target)}
