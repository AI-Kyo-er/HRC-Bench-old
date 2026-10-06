from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from hrc_pilot.native_trajectory_dataset import NativeTrajectoryDataset


def sample(path, *, state_dim=8):
    base=path/'sample';img=Image.new('RGB',(256,256))
    img.save(str(base)+'.png');img.save(str(base)+'_wrist.png')
    np.save(str(base)+'.state.npy',np.zeros(state_dim,dtype=np.float32))
    np.save(str(base)+'.action.npy',np.zeros((10,7),dtype=np.float32))
    np.save(str(base)+'.action_valid.npy',np.ones(10,dtype=np.bool_))
    Path(str(base)+'.prompt.txt').write_text('public task')


def test_native_loader_exposes_only_public_model_inputs_and_executed_actions(tmp_path):
    sample(tmp_path)
    (tmp_path/'private_score.json').write_text('{"success":true}')
    s=NativeTrajectoryDataset(tmp_path)[0]
    assert set(s)=={'observation/image','observation/wrist_image','observation/state','prompt','actions','action_valid'}


def test_joint_state_domain_cannot_silently_be_loaded_as_native_eef_state(tmp_path):
    sample(tmp_path,state_dim=9)
    with pytest.raises(ValueError):NativeTrajectoryDataset(tmp_path)[0]
