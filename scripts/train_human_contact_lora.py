#!/usr/bin/env python3
"""真实接触范例的Qwen3 LoRA训练；只监督目标回答，不训练输入token。"""
import argparse
from hashlib import sha256
import json,os,random,subprocess,time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
from peft import LoraConfig,get_peft_model
from hrc_pilot.human_learning_dataset import HumanLearningDataset


def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',type=Path,required=True);parser.add_argument('--weights-dir',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--base-model',type=Path,default=Path('/data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B'))
    parser.add_argument('--steps',type=int,default=160);parser.add_argument('--gradient-accumulation',type=int,default=4)
    parser.add_argument('--max-sequence-length',type=int,default=4096);parser.add_argument('--seed',type=int,default=31)
    args=parser.parse_args()
    if args.weights_dir.exists() or args.output_dir.exists():parser.error('使用新的权重与记录目录')
    rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.free','--format=csv,noheader,nounits'],text=True)
    entries={r.split(',')[0].strip():int(r.split(',')[1]) for r in rows.splitlines()};chosen=os.environ.get('CUDA_VISIBLE_DEVICES')
    if chosen not in entries or entries[chosen]<45000:parser.error('14B BF16 LoRA训练需要单卡至少45GB空闲显存')
    paths=[Path(__file__),Path('src/hrc_pilot/human_learning_dataset.py')]
    hashes={str(p):sha256(p.read_bytes()).hexdigest() for p in paths}
    random.seed(args.seed);torch.manual_seed(args.seed)
    train=HumanLearningDataset(args.dataset,'train');dev=HumanLearningDataset(args.dataset,'dev')
    tokenizer=AutoTokenizer.from_pretrained(str(args.base_model),local_files_only=True)
    def encode(dataset):
        encoded=[]
        for i in range(len(dataset)):
            source,target=dataset[i]
            ids=tokenizer.apply_chat_template([{'role':'system','content':source['system_prompt']},{'role':'user','content':source['public_input']}],
                tokenize=True,add_generation_prompt=True,enable_thinking=True)
            answer=target['reason']+'\n</think>\n'+json.dumps(target,ensure_ascii=False,separators=(',',':'))+tokenizer.eos_token
            labels=tokenizer.encode(answer,add_special_tokens=False)
            if len(ids)+len(labels)>args.max_sequence_length:raise ValueError(f'不能静默截断真实输入：{len(ids)+len(labels)}tokens')
            encoded.append((torch.tensor(ids+labels,dtype=torch.long),len(labels)))
        return encoded
    train_tokens=encode(train);dev_tokens=encode(dev)
    args.output_dir.mkdir(parents=True);started=time.time()
    model=AutoModelForCausalLM.from_pretrained(str(args.base_model),local_files_only=True,torch_dtype=torch.bfloat16,
        device_map={'':0},attn_implementation='sdpa',low_cpu_mem_usage=True)
    model.config.use_cache=False
    model=get_peft_model(model,LoraConfig(r=8,lora_alpha=16,lora_dropout=.05,target_modules=['q_proj','v_proj'],bias='none',task_type='CAUSAL_LM'))
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
    model.enable_input_require_grads()
    parameters=[p for p in model.parameters() if p.requires_grad]
    initial_parameters=[p.detach().float().cpu().clone() for p in parameters]
    assert all('lora_' in name for name,p in model.named_parameters() if p.requires_grad)
    optimizer=torch.optim.AdamW(parameters,lr=1e-4,weight_decay=.01,foreach=False)
    def loss(sample):
        ids,n=sample;ids=ids[None].to('cuda');keep=n+1
        labels=ids[:,-keep:].clone();labels[:,0]=-100
        # Qwen3仅计算回答及其前一个输入token的logits，损失覆盖全部回答token。
        return model(input_ids=ids,attention_mask=torch.ones_like(ids),labels=labels,logits_to_keep=keep).loss
    log=args.output_dir/'training.jsonl';order=list(range(len(train_tokens)));cursor=0
    def evaluate():
        model.eval()
        with torch.no_grad():values=[float(loss(s)) for s in dev_tokens[::max(1,len(dev_tokens)//12)]]
        model.train();return sum(values)/len(values)
    initial_dev=evaluate();print('initial_dev_loss',initial_dev,flush=True)
    for step in range(args.steps):
        model.train();optimizer.zero_grad(set_to_none=True);value=0.
        for _ in range(args.gradient_accumulation):
            if cursor%len(order)==0:random.shuffle(order)
            sample=train_tokens[order[cursor%len(order)]];cursor+=1
            batch_loss=loss(sample);value+=float(batch_loss.detach())/args.gradient_accumulation
            (batch_loss/args.gradient_accumulation).backward()
        norm=float(torch.nn.utils.clip_grad_norm_(parameters,1.));optimizer.step()
        row={'step':step+1,'train_loss':value,'gradient_norm':norm,'elapsed_s':time.time()-started,
            'cuda_peak_allocated_mib':torch.cuda.max_memory_allocated()/1024**2}
        if (step+1)%40==0:
            row['dev_loss']=evaluate()
            checkpoint=args.weights_dir/'checkpoints'/f'step{step+1:04d}'
            model.save_pretrained(str(checkpoint));tokenizer.save_pretrained(str(checkpoint))
        with log.open('a') as f:f.write(json.dumps(row)+'\n')
        print(json.dumps(row),flush=True)
    model.save_pretrained(str(args.weights_dir));tokenizer.save_pretrained(str(args.weights_dir))
    final_dev=evaluate()
    delta=sum(float(((p.detach().float().cpu()-initial)**2).sum()) for p,initial in zip(parameters,initial_parameters))**.5
    assert delta>0
    summary={'status':'trained','steps':args.steps,'train_samples':len(train),'dev_samples':len(dev),
        'trainable_parameters':sum(p.numel() for p in parameters),'initial_dev_loss':initial_dev,'final_dev_loss':final_dev,
        'base_model':str(args.base_model),'adapter_weights':str(args.weights_dir),'dataset':str(args.dataset),
        'answer_only_supervision':True,'logits_keep_semantics':'answer_length+1, first label ignored, standard shifted causal loss',
        'initial_intention_normalization':'time0 previous targets and intention cleared only in loader',
        'cuda_visible_devices':chosen,'cuda_peak_allocated_mib':torch.cuda.max_memory_allocated()/1024**2,
        'source_sha256':hashes,'source_files_changed_during_run':[str(p) for p in paths if sha256(p.read_bytes()).hexdigest()!=hashes[str(p)]],
        'adapter_parameter_delta_norm':delta,'base_parameters_frozen':True,
        'interpretation':'损失及真实参数更新不是闭环能力证明；需要未用于训练的实际Sim运行与视频。'}
    write(args.output_dir/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
