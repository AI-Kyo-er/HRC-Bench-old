"""中国源OpenVLA-LIBERO的显式离线入口，不经远程auto_map加载代码。"""
import importlib.util
import json
from pathlib import Path
import sys
import types

import numpy as np
from .openvla_preprocessing import preprocess_image


SOURCE_ROOT=Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/external/openvla')


def libero_gripper(action):
    result=np.asarray(action,dtype=float).copy()
    if result.shape!=(7,) or not np.isfinite(result).all():
        raise ValueError('OpenVLA必须输出7个有限操作空间动作')
    # Upstream LIBERO evaluator: [0,1] -> sign([-1,1]) -> invert.
    result[-1]=-np.sign(2*result[-1]-1)
    return result


def load_official_classes():
    package_name='hrc_offline_openvla_hf'
    source=SOURCE_ROOT/'prismatic/extern/hf'
    if package_name not in sys.modules:
        package=types.ModuleType(package_name);package.__path__=[str(source)]
        sys.modules[package_name]=package
        for name in ['configuration_prismatic','modeling_prismatic','processing_prismatic']:
            spec=importlib.util.spec_from_file_location(package_name+'.'+name,source/(name+'.py'))
            module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    config=sys.modules[package_name+'.configuration_prismatic']
    model=sys.modules[package_name+'.modeling_prismatic']
    processing=sys.modules[package_name+'.processing_prismatic']
    return config.OpenVLAConfig,model.OpenVLAForActionPrediction,processing.PrismaticImageProcessor,processing.PrismaticProcessor


class OpenVLANativePolicy:
    def __init__(self, checkpoint, device='cuda:0'):
        import torch
        from transformers import AutoTokenizer
        from hashlib import sha256
        import subprocess

        root=Path(checkpoint)
        receipt=json.loads((root/'download_receipt.json').read_text())
        if receipt.get('status')!='downloaded_and_verified' or receipt.get('source')!='China_ModelScope':
            raise ValueError('权重须完成中国源完整校验')
        Config,Model,ImageProcessor,Processor=load_official_classes()
        config=Config.from_pretrained(root,local_files_only=True)
        self.model,loading=Model.from_pretrained(root,config=config,torch_dtype=torch.bfloat16,
                        low_cpu_mem_usage=True,attn_implementation='sdpa',local_files_only=True,
                        output_loading_info=True)
        if any(loading.get(key) for key in ['missing_keys','unexpected_keys','mismatched_keys','error_msgs']):
            raise ValueError(f'权重载入不完整：{loading}')
        self.device=torch.device(device);self.model.to(self.device).eval()
        self.processor=Processor(ImageProcessor.from_pretrained(root,local_files_only=True),
                                 AutoTokenizer.from_pretrained(root,local_files_only=True))
        self.metadata={'config':'openvla_libero_spatial','checkpoint':str(root),
                       'action_encoding':'libero_osc_delta','action_dim':7,
                       'consumed_inputs':['observation/image','prompt'],
                       'unused_compatibility_inputs':['observation/wrist_image','observation/state'],
                       'center_crop':True,'crop_area':.9,'image_preprocessing':'JPEG roundtrip -> TF Lanczos3 224 -> TF center crop 0.9 area -> uint8',
                       'attention_implementation':'sdpa','offline_assets_only':True,
                       'adapter_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
                       'preprocessing_sha256':sha256(Path(__file__).with_name('openvla_preprocessing.py').read_bytes()).hexdigest(),
                       'checkpoint_mirror_identity':'ModelScope file SHA256 verified; upstream hash identity not checked',
                       'source_commit':subprocess.check_output(['git','-C',str(SOURCE_ROOT),'rev-parse','HEAD'],text=True).strip(),
                       'source_sha256':{name:sha256((SOURCE_ROOT/'prismatic/extern/hf'/name).read_bytes()).hexdigest()
                                        for name in ['configuration_prismatic.py','modeling_prismatic.py','processing_prismatic.py']},
                       'weight_loading_info':loading}

    def infer(self, value):
        import torch
        from PIL import Image
        from hashlib import sha256
        if set(value)!={'observation/image','observation/wrist_image','observation/state','prompt'}:
            raise ValueError('需要原生机器人接口输入，禁止额外私有状态')
        image=np.asarray(value['observation/image'])
        if image.ndim!=3 or image.shape[2]!=3 or image.dtype!=np.uint8:
            raise ValueError('需要真实RGB uint8相机输入')
        prompt=f'In: What action should the robot take to {value["prompt"].lower()}?\nOut:'
        processed=preprocess_image(image)
        encoded=self.processor(prompt,Image.fromarray(processed).convert('RGB')).to(self.device,dtype=torch.bfloat16)
        with torch.inference_mode():
            action=self.model.predict_action(**encoded,unnorm_key='libero_spatial',do_sample=False)
        return {'actions':libero_gripper(action)[None,:],
                'model_input_evidence':{'source_rgb_sha256':sha256(image.tobytes()).hexdigest(),
                    'processed_rgb_sha256':sha256(processed.tobytes()).hexdigest(),
                    'processed_rgb':processed,'prompt':prompt}}
