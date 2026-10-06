#!/usr/bin/env python3
"""单卡离线视觉协调器；仅处理相机、自身状态、公开任务和对话。"""
import argparse
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import subprocess
import time

from hrc_pilot.robot_coordination import PUBLIC_KEYS, decode_image, validate_decision


SYSTEM=(
    '你是与人共同工作的机械臂协调策略。根据实际相机、自身状态和公开对话自主决定当前动作。'
    '图片依次是本次开始时的外部相机、当前外部相机和当前腕部相机。初始图帮助理解工作区变化。'
    'robot_task是你的公开任务，human_task是人的公开工作；不要把人的工作当作已经完成。'
    '你可以通过message回应人的等待、请求和冲突，也可以请求对方说明进度或协调先后顺序。'
    '根据当前画面与对话重估计划，文字消息和之前的计划不等于执行事实；不得假定知道评分。'
    'mode为execute时，instruction给出当前要完成的简短英文机械臂运动目标，由真实VLA执行。'
    'mode为hold时保持当前位置和抓持状态，允许等待人让出空间或准备物体。'
    '明确的任务前置条件须通过当前观察理解；程序不会替你规划后续步骤，plan只记录你的想法。'
    '不必每次重复发同一句消息。等待时说明具体条件，遇到持续停顿可以重新协调。'
    '只输出JSON：mode、instruction、message、reason、memory_note、current_goal、plan。'
    'message/instruction用简短英文，reason/memory_note/current_goal/plan用中文。')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,default=Path('/data1/sieniwgroup/sieniw/models/Qwen/Qwen3-VL-8B-Instruct'))
    parser.add_argument('--port',type=int,default=8780)
    args=parser.parse_args()
    rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.free','--format=csv,noheader,nounits'],text=True)
    free={r.split(',')[0].strip():int(r.split(',')[1]) for r in rows.splitlines()}
    selected=os.environ.get('CUDA_VISIBLE_DEVICES')
    required=sum(p.stat().st_size for p in args.model.glob('*.safetensors'))//1024**2+8192
    if selected not in free or free[selected]<required:parser.error(f'请指定单卡至少{required}MiB空闲显存')
    import torch
    from transformers import AutoProcessor,Qwen3VLForConditionalGeneration
    processor=AutoProcessor.from_pretrained(args.model,local_files_only=True)
    model=Qwen3VLForConditionalGeneration.from_pretrained(args.model,local_files_only=True,
              torch_dtype=torch.bfloat16,attn_implementation='sdpa',device_map={'':0}).eval()
    metadata={'model':str(args.model),'model_type':'Qwen3VLForConditionalGeneration','local_files_only':True,
              'inputs':'initial/current RGB, wrist RGB, own state, public task/dialogue, own generated history',
              'task_scores_available':False,'policy':'neural_visual_coordination','cuda_visible_devices':selected,
              'source_sha256':{str(path):sha256(path.read_bytes()).hexdigest() for path in
                  [Path(__file__),Path('src/hrc_pilot/robot_coordination.py')]}}
    print('Qwen3-VL视觉协调器已离线载入',flush=True)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path!='/metadata':self.send_error(404);return
            self.reply(metadata)

        def reply(self,value):
            data=json.dumps(value,ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)))
            self.end_headers();self.wfile.write(data)

        def log_message(self,*args):pass

        def do_POST(self):
            if self.path!='/infer':self.send_error(404);return
            request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if set(request)!=PUBLIC_KEYS:self.send_error(400,'Only public fields allowed');return
            images=[decode_image(request['images'][name]) for name in ['initial','current','wrist']]
            visible={key:value for key,value in request.items() if key!='images'}
            text='根据公开信息和真实画面更新当前协作计划：\n'+json.dumps(visible,ensure_ascii=False)
            messages=[{'role':'system','content':SYSTEM},{'role':'user','content':[
                {'type':'image','image':image} for image in images]+[{'type':'text','text':text}]}]
            template=processor.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
            inputs=processor(text=[template],images=images,return_tensors='pt').to(model.device)
            started=time.perf_counter()
            with torch.inference_mode():generated=model.generate(**inputs,max_new_tokens=384,do_sample=False)
            raw=processor.batch_decode(generated[:,inputs['input_ids'].shape[1]:],skip_special_tokens=True)[0]
            decision,error=validate_decision(raw)
            self.reply({'raw_output':raw,'decision':decision,'parse_error':error,
                        'latency_s':time.perf_counter()-started,'public_input':visible,
                        'image_sha256':{key:value['rgb_sha256'] for key,value in request['images'].items()}})

    HTTPServer(('127.0.0.1',args.port),Handler).serve_forever()


if __name__=='__main__':main()
