#!/usr/bin/env python3
"""配置已安装的隔离原生环境，仅复用本地模型依赖、代码与资产，不下载。"""
from pathlib import Path
from hashlib import sha256
import json
import subprocess


def main():
    project=Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench')
    environment=project/'envs/libero-native'
    site=environment/'lib/python3.11/site-packages'
    source=project/'external/openpi/third_party/libero'
    base=source/'libero/libero'
    paths={'existing_openpi_dependencies':project/'envs/openpi/lib/python3.11/site-packages',
           'native_libero_source':source,
           'native_openpi_client':project/'external/openpi/packages/openpi-client/src'}
    for name,path in paths.items():
        if not path.exists():raise FileNotFoundError(path)
        (site/(name+'.pth')).write_text(str(path)+'\n')
    config=project/'cache/libero-native/config.yaml'
    config.parent.mkdir(parents=True,exist_ok=True)
    values={'benchmark_root':base,'bddl_files':base/'bddl_files','init_states':base/'init_files',
            'assets':base/'assets','datasets':project/'datasets/libero_native'}
    values['datasets'].mkdir(exist_ok=True)
    config.write_text('\n'.join(f'{key}: {value}' for key,value in values.items())+'\n')
    binding=site/'robosuite/utils/binding_utils.py'
    original=binding.read_text()
    old='''assert MUJOCO_EGL_DEVICE_ID.isdigit() and (
            MUJOCO_EGL_DEVICE_ID in CUDA_VISIBLE_DEVICES
        ), "MUJOCO_EGL_DEVICE_ID needs to be set to one of the device id specified in CUDA_VISIBLE_DEVICES"'''
    new='''assert MUJOCO_EGL_DEVICE_ID.isdigit(), "MUJOCO_EGL_DEVICE_ID must be an EGL ordinal; physical PCI binding is checked by the HRC runner"'''
    backup=config.parent/'robosuite_binding_original.py'
    if old in original:
        if not backup.exists():backup.write_text(original)
        binding.write_text(original.replace(old,new))
    elif new not in original:
        raise RuntimeError('Robosuite GPU保护代码不匹配预期版本，不能应用本地修正')
    receipt={'libero_commit':subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),
             'paths':{key:str(path) for key,path in paths.items()},
             'package_source':'Tsinghua PyPI, environment proxies disabled during installation',
             'model_or_dataset_downloaded':False,
             'robosuite_gpu_assert_patch':{'original_sha256':sha256(backup.read_bytes()).hexdigest(),
                                          'patched_sha256':sha256(binding.read_bytes()).hexdigest(),
                                          'scope':'this isolated environment only; runner validates EGL and CUDA through PCI bus, not equal ordinals'},
             'interpretation':'native site packages take priority; existing Torch and client dependencies are fallback paths. Other project environments are not changed.'}
    (config.parent/'environment_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
    print(config)


if __name__=='__main__':main()
