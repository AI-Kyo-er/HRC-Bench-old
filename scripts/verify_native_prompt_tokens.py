#!/usr/bin/env python3
"""离线重建π0.5公开语言和8维状态的完整token长度，不加载GPU模型。"""
import argparse
import json
from pathlib import Path

import numpy as np
import sentencepiece
from safetensors.numpy import load_file


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args()
    checkpoint=Path('/data1/sieniwgroup/sieniw/models/lerobot/pi05-libero')
    config=json.loads((checkpoint/'config.json').read_text());limit=config['tokenizer_max_length']
    tokenizer=sentencepiece.SentencePieceProcessor(model_file='/data1/sieniwgroup/sieniw/models/Physical-Intelligence/openpi-cache/big_vision/paligemma_tokenizer.model')
    stats=load_file(checkpoint/'policy_preprocessor_step_2_normalizer_processor.safetensors')
    episodes=[]
    for file in sorted(args.input_dir.rglob('model_calls.jsonl')):
        calls=[json.loads(line) for line in file.read_text().splitlines() if line.strip()]
        lengths=[]
        for call in calls:
            normalized=(np.asarray(call['state'],dtype=np.float32)-stats['observation.state.mean'])/(stats['observation.state.std']+1e-8)
            cleaned=call['prompt'].strip().replace('_',' ').replace('\n',' ')
            state=' '.join(map(str,np.digitize(normalized,bins=np.linspace(-1,1,257)[:-1])-1))
            tokens=tokenizer.encode(f'Task: {cleaned}, State: {state};\nAction: ',add_bos=True)
            lengths.append({'step':call['step'],'time_s':call['time_s'],'tokens':len(tokens),'truncated':len(tokens)>limit})
        episodes.append({'episode':str(file.parent),'max_tokens':max(r['tokens'] for r in lengths),'calls':lengths})
    assert episodes
    truncated=sum(r['truncated'] for e in episodes for r in e['calls'])
    output={'status':'verified_no_truncation' if not truncated else 'truncation_detected','token_limit':limit,
            'truncated_calls':truncated,'episodes':episodes,'interpretation':'按已运行π0.5适配器和本地官方sentencepiece资产重建；不证明语言被模型理解。'}
    (args.input_dir/'prompt_token_verification.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
    print(f'完整token最大长度{max(e["max_tokens"] for e in episodes)}/{limit}；截断调用{truncated}')


if __name__=='__main__':main()
