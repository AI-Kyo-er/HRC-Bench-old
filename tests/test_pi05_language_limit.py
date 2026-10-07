from types import SimpleNamespace,ModuleType
import sys

import numpy as np
import pytest

from hrc_pilot.libero_torch_policy import LiberoTorchPolicy


def test_oversized_language_and_state_fail_before_model_execution(monkeypatch):
    torch=pytest.importorskip('torch')
    # 该回归在Sim环境运行，不要求安装服务端的OpenPI／JAX依赖。
    model_module=ModuleType('openpi.models.model');model_module.Observation=object
    monkeypatch.setitem(sys.modules,'openpi.models.model',model_module)
    policy=object.__new__(LiberoTorchPolicy)
    policy.stats={'observation.state.mean':torch.zeros(8),'observation.state.std':torch.ones(8)}
    policy.config={'tokenizer_max_length':200}
    policy.tokenizer=SimpleNamespace(_tokenizer=SimpleNamespace(encode=lambda text,add_bos:list(range(201))))
    request={'observation/image':np.zeros((4,4,3),dtype=np.uint8),
        'observation/wrist_image':np.zeros((4,4,3),dtype=np.uint8),'observation/state':np.zeros(8),
        'prompt':'Please wait until the human has finished preparing the bowl.'}
    with pytest.raises(ValueError,match='不能静默截断'):
        policy.infer(request)
