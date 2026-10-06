"""按确定性stem读取原生场景实测数据，不依赖配对manifest或泄露私有成绩。"""
from pathlib import Path

import numpy as np
from PIL import Image


class NativeTrajectoryDataset:
    def __init__(self, directory):
        self.directory=Path(directory)
        self.stems=sorted(p.name.removesuffix('.state.npy') for p in self.directory.glob('*.state.npy'))
        if not self.stems:raise ValueError('没有原生观测样本')

    def __len__(self):return len(self.stems)

    def __getitem__(self,index):
        stem=self.stems[index];base=self.directory/stem
        state=np.load(str(base)+'.state.npy',allow_pickle=False)
        actions=np.load(str(base)+'.action.npy',allow_pickle=False)
        valid=np.load(str(base)+'.action_valid.npy',allow_pickle=False)
        if state.shape!=(8,) or actions.ndim!=2 or actions.shape[1]!=7 or valid.shape!=(len(actions),):
            raise ValueError('要求8维末端状态、N×7原生OSC动作及N维有效标记；不能与关节目标域混用')
        if not np.isfinite(state).all() or not np.isfinite(actions).all() or valid.dtype!=np.bool_:
            raise ValueError('非法数值或动作有效标记')
        rgb=np.asarray(Image.open(str(base)+'.png').convert('RGB'))
        wrist=np.asarray(Image.open(str(base)+'_wrist.png').convert('RGB'))
        if rgb.shape!=(256,256,3) or wrist.shape!=rgb.shape:raise ValueError('要求原始256×256双相机')
        return {'observation/image':rgb,'observation/wrist_image':wrist,'observation/state':state,
                'prompt':Path(str(base)+'.prompt.txt').read_text(),
                'actions':actions,'action_valid':valid}
