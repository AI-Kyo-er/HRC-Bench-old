import ast
from pathlib import Path

import numpy as np
import pytest

from hrc_pilot.openvla_preprocessing import preprocess_image


def test_images_match_pinned_official_resize_and_crop_functions_pixel_for_pixel():
    tf=pytest.importorskip('tensorflow')
    import torch
    from PIL import Image
    root=Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/external/openvla')
    namespace={'np':np,'tf':tf,'torch':torch,'Image':Image,'DEVICE':'cpu'}
    for file,names in [('libero/libero_utils.py',{'resize_image'}),
                       ('openvla_utils.py',{'crop_and_resize','get_vla_action'})]:
        parsed=ast.parse((root/'experiments/robot'/file).read_text())
        functions=[node for node in parsed.body if isinstance(node,ast.FunctionDef) and node.name in names]
        assert len(functions)==len(names)
        exec(compile(ast.Module(body=functions,type_ignores=[]),str(root/file),'exec'),namespace)
    captured=[]
    class Inputs(dict):
        def to(self,*args,**kwargs):return self
    class Model:
        def predict_action(self,**kwargs):return np.zeros(7)
    def processor(prompt,image):
        captured.append(np.asarray(image));return Inputs()
    samples=[np.zeros((256,256,3),np.uint8),np.full((256,256,3),255,np.uint8),
             np.random.default_rng(0).integers(0,256,(256,256,3),dtype=np.uint8)]
    for image in samples:
        resized=namespace['resize_image'](image,(224,224))
        namespace['get_vla_action'](Model(),processor,'openvla',{'full_image':resized},
                                   'place the bowl','libero_spatial',center_crop=True)
        np.testing.assert_array_equal(preprocess_image(image),captured[-1])
