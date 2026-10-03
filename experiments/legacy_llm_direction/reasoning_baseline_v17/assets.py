"""官方Qwen3-14B一次固定revision；数据盘下载与官方逐LFS校验。"""
import argparse
import datetime
import json
import os
from pathlib import Path
from huggingface_hub import HfApi,hf_hub_download,snapshot_download
from experiments.physical.run import ROOT,save,sha

RESULT=ROOT/'results/reasoning_baseline_v17'
SPEC=RESULT/'model_spec.json'
DEST=Path('/data1/sieniwgroup/sieniw/HRC-Bench/models/Qwen3-14B')
REPO='Qwen/Qwen3-14B'


def prepare():
    if SPEC.exists():raise RuntimeError('已固定revision，禁止重新选择。')
    info=HfApi(token=False).model_info(REPO,revision='main',files_metadata=True,token=False);revision=info.sha
    assert len(revision)==40
    pinned=HfApi(token=False).model_info(REPO,revision=revision,files_metadata=True,token=False);assert pinned.sha==revision
    files={f.rfilename:dict(bytes=f.size,sha256=f.lfs.sha256) for f in pinned.siblings if f.rfilename.endswith('.safetensors')}
    assert files and all(v['bytes']>0 and len(v['sha256'])==64 for v in files.values())
    DEST.mkdir(parents=True,exist_ok=True)
    for name in ('config.json','generation_config.json','model.safetensors.index.json','tokenizer_config.json','tokenizer.json'):
        hf_hub_download(REPO,name,revision=revision,local_dir=DEST,token=False,force_download=False)
    config=json.loads((DEST/'config.json').read_text());assert config['model_type']=='qwen3' and config['architectures']==['Qwen3ForCausalLM']
    save(SPEC,dict(model_id=REPO,revision=revision,path=str(DEST),fixed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),official_weights=files,total_weights_bytes=sum(v['bytes'] for v in files.values()),config=config,
        metadata_sha256={n:sha(DEST/n) for n in ('config.json','generation_config.json','model.safetensors.index.json','tokenizer_config.json','tokenizer.json')},official_metadata_source='HF官方仓库main只解析一次commit，后续所有文件使用该完整revision，无认证凭据/外部推理。'))
    link=ROOT/'models/Qwen3-14B'
    if not link.exists():link.symlink_to(DEST)
    print('固定官方模型',revision,'bytes',sum(v['bytes'] for v in files.values()),flush=True)


def download():
    spec=json.loads(SPEC.read_text());assert spec['model_id']==REPO
    save(RESULT/'raw/download_started.json',dict(pid=os.getpid(),revision=spec['revision'],utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),max_workers=4,force_download=False,cache_path=str(DEST/'.cache/huggingface')))
    snapshot_download(REPO,revision=spec['revision'],local_dir=DEST,token=False,force_download=False,max_workers=4,allow_patterns=['*.json','*.safetensors','*.txt','*.md'])
    verify()


def verify():
    spec=json.loads(SPEC.read_text());actual={}
    for name,expected in spec['official_weights'].items():
        path=DEST/name;actual[name]=dict(bytes=path.stat().st_size,sha256=sha(path));assert actual[name]==expected
        print('官方权重SHA通过',name,actual[name]['bytes'],flush=True)
    for name,digest in spec['metadata_sha256'].items():assert sha(DEST/name)==digest
    index=json.loads((DEST/'model.safetensors.index.json').read_text());assert set(index['weight_map'].values())==set(actual)
    save(RESULT/'download_receipt.json',dict(model_id=REPO,revision=spec['revision'],path=str(DEST),all_weights_match_official=True,official_weights=spec['official_weights'],local_weights=actual,metadata_sha256=spec['metadata_sha256'],utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    print('完整官方权重与metadata校验完成',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('prepare','download','verify'));a=p.parse_args();globals()[a.stage]()
