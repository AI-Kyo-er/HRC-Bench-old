"""按确定性stem读取原生场景实测数据，不依赖配对manifest或泄露私有成绩。"""
from pathlib import Path

import numpy as np
from PIL import Image


class NativeTrajectoryDataset:
    allow_mixed_controls=False
    def __init__(self, directory):
        self.directory=Path(directory)
        self.stems=sorted(p.name.removesuffix('.state.npy') for p in self.directory.glob('*.state.npy'))
        if not self.stems:raise ValueError('没有原生观测样本')

    def __len__(self):return len(self.stems)

    def __getitem__(self,index):
        stem=self.stems[index];base=self.directory/stem
        source_path=Path(str(base)+'.action_source.txt')
        if source_path.exists() and source_path.read_text().strip()!='learned_vla' and not self.allow_mixed_controls:
            raise ValueError('样本包含协调原语，须使用NativeMixedTrajectoryDataset，不得作为学习VLA监督')
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


class NativeMixedTrajectoryDataset(NativeTrajectoryDataset):
    """混合策略轨迹显式标明控制来源；保持与位移不成为学习VLA动作标签。"""
    SOURCES={'learned_vla','vlm_selected_hold_primitive','vlm_selected_cartesian_primitive','planner_output_rejection_hold_primitive'}
    allow_mixed_controls=True

    def __getitem__(self,index):
        sample=super().__getitem__(index)
        source=(self.directory/(self.stems[index]+'.action_source.txt')).read_text().strip()
        if source not in self.SOURCES:raise ValueError('未知控制来源，不推断为学习VLA')
        sample['action_source']=source
        sample['learned_vla_action_mask']=sample['action_valid'] & (source=='learned_vla')
        return sample
