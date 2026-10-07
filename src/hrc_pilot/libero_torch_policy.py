"""中国源LeRobot π0.5-LIBERO权重的离线OpenPI Torch推理适配。"""
from pathlib import Path
import json
import time

import numpy as np


class LiberoTorchPolicy:
    def __init__(self, checkpoint, device='cuda:0'):
        import torch
        from safetensors.torch import load_file
        from openpi.models.pi0_config import Pi0Config
        from openpi.models_pytorch.pi0_pytorch import PI0Pytorch
        from openpi.models.tokenizer import PaligemmaTokenizer
        from openpi.shared import download
        from transformers.modeling_utils import no_init_weights

        self.root = Path(checkpoint)
        receipt = json.loads((self.root / 'download_receipt.json').read_text())
        if receipt['status'] != 'downloaded_and_verified':
            raise ValueError('模型没有完成中国源下载核验')
        config = json.loads((self.root / 'config.json').read_text())
        # Non-persistent rotary buffers need actual values; meta allocation was
        # used only for the separate shape audit, never for runtime inference.
        with torch.device('cpu'), no_init_weights():
            model = PI0Pytorch(Pi0Config(pi05=True, action_horizon=config['chunk_size'], pytorch_compile_mode=None))
        weights = load_file(self.root / 'model.safetensors', device='cpu')
        weights = {key.removeprefix('model.'): value for key, value in weights.items()}
        model.load_state_dict(weights, strict=True, assign=True)
        model.paligemma_with_expert.to_bfloat16_for_selected_params('bfloat16')
        self.model = model.to(device).eval()
        self.device = torch.device(device)
        self.stats = load_file(self.root / 'policy_preprocessor_step_2_normalizer_processor.safetensors')
        self.output_stats = load_file(self.root / 'policy_postprocessor_step_0_unnormalizer_processor.safetensors')
        # The exact same PaliGemma sentencepiece asset is already cached locally.
        cached = Path('/data1/sieniwgroup/sieniw/models/Physical-Intelligence/openpi-cache/big_vision/paligemma_tokenizer.model')
        original_download = download.maybe_download
        def offline_asset(url, **kwargs):
            if str(url) == 'gs://big_vision/paligemma_tokenizer.model' and cached.exists():
                return cached
            raise FileNotFoundError('禁止推理过程中隐式下载额外模型资产')
        download.maybe_download = offline_asset
        try:
            self.tokenizer = PaligemmaTokenizer(max_len=config['tokenizer_max_length'])
        finally:
            download.maybe_download = original_download
        self.config = config
        self.metadata = {'config': 'pi05_libero', 'checkpoint': str(self.root),
                         'language_token_limit':config['tokenizer_max_length'],
                         'action_encoding': 'libero_osc_delta', 'action_dim': 7,
                         'state_encoding': 'eef_xyz_axisangle_signed_finger_positions',
                         'weight_key_mapping': 'strip_model_prefix_strict_813_key_shape_match',
                         'normalization': 'checkpoint_mean_std', 'image_normalization': '[-1,1]',
                         'offline_assets_only': True}

    def infer(self, value):
        import torch
        from openpi.models.model import Observation

        expected = {'observation/image', 'observation/wrist_image', 'observation/state', 'prompt'}
        if set(value) != expected:
            raise ValueError('LIBERO推理仅接受双相机、8维末端状态与公开语言')
        state = np.asarray(value['observation/state'], dtype=np.float32)
        if state.shape != (8,) or not np.isfinite(state).all():
            raise ValueError('LIBERO末端状态必须为8个有限值')
        mean = self.stats['observation.state.mean'].numpy()
        std = self.stats['observation.state.std'].numpy()
        normalized = (state - mean) / (std + 1e-8)
        cleaned=value['prompt'].strip().replace('_',' ').replace('\n',' ')
        bins=np.digitize(normalized,bins=np.linspace(-1,1,257)[:-1])-1
        full_prompt=f'Task: {cleaned}, State: '+ ' '.join(map(str,bins))+';\nAction: '
        full_ids=self.tokenizer._tokenizer.encode(full_prompt,add_bos=True)
        if len(full_ids)>self.config['tokenizer_max_length']:
            raise ValueError(f'不能静默截断实际VLA语言和状态：{len(full_ids)}>{self.config["tokenizer_max_length"]}')
        tokens, mask = self.tokenizer.tokenize(value['prompt'], normalized)
        def image(key):
            from openpi_client.image_tools import resize_with_pad
            pixels = np.asarray(value[key], dtype=np.uint8)
            pixels = resize_with_pad(pixels, 224, 224)
            return torch.from_numpy(pixels.copy()).permute(2, 0, 1).unsqueeze(0).to(self.device).float() / 127.5 - 1
        base, wrist = image('observation/image'), image('observation/wrist_image')
        padded = np.pad(normalized, (0, 32 - len(normalized)))
        observation = Observation(images={'base_0_rgb':base, 'left_wrist_0_rgb':wrist, 'right_wrist_0_rgb':torch.zeros_like(base)},
                                  image_masks={key:torch.tensor([flag],device=self.device) for key,flag in
                                               [('base_0_rgb',True),('left_wrist_0_rgb',True),('right_wrist_0_rgb',False)]},
                                  state=torch.tensor(padded,device=self.device).unsqueeze(0),
                                  tokenized_prompt=torch.tensor(tokens,device=self.device).unsqueeze(0),
                                  tokenized_prompt_mask=torch.tensor(mask,device=self.device).unsqueeze(0))
        started = time.perf_counter()
        with torch.inference_mode():
            actions = self.model.sample_actions(self.device, observation, num_steps=self.config['num_inference_steps'])
        actions = actions[0, :, :7].float().cpu()
        actions = actions * (self.output_stats['action.std'] + 1e-8) + self.output_stats['action.mean']
        return {'actions':actions.numpy(), 'policy_timing':{'infer_ms':(time.perf_counter()-started)*1000},
                'language_input_evidence':{'token_count':len(full_ids),'token_limit':self.config['tokenizer_max_length'],
                    'truncated':False,'token_ids':np.asarray(tokens,dtype=int).tolist(),
                    'token_mask':np.asarray(mask,dtype=bool).tolist(),
                    'decoded_actual_input':self.tokenizer._tokenizer.decode(tokens[mask].tolist())}}
