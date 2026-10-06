#!/usr/bin/env python3
"""离线重建真实OpenVLA推理消费的图像，核对保存帧与来源。"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image

from hrc_pilot.openvla_preprocessing import preprocess_image


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args();count=0
    for path in sorted(args.input_dir.rglob('model_calls.jsonl')):
        for raw in path.read_text().splitlines():
            call=json.loads(raw);evidence=call['model_input_evidence']
            source=np.asarray(Image.open(path.parent/call['exterior_artifact']).convert('RGB'))
            actual=np.asarray(Image.open(path.parent/evidence['processed_artifact']).convert('RGB'))
            assert sha256(source.tobytes()).hexdigest()==evidence['source_rgb_sha256']
            assert sha256(actual.tobytes()).hexdigest()==evidence['processed_rgb_sha256']
            np.testing.assert_array_equal(preprocess_image(source),actual)
            assert evidence['prompt']==f'In: What action should the robot take to {call["prompt"].lower()}?\nOut:'
            count+=1
    assert count
    result={'status':'verified','model_call_count':count,'pixel_exact_reconstruction':True,
            'interpretation':'独立重建官方图像/语言预处理及保存帧，不证明模型能力或上游权重身份。'}
    (args.input_dir/'preprocessing_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(f'{count}次真实模型输入逐像素重建通过')


if __name__=='__main__':main()
