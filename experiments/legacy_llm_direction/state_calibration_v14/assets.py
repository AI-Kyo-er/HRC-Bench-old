"""只读本地模型及官方固定revision元数据；不下载权重。"""
import datetime
import hashlib
import json
import struct
from pathlib import Path
from experiments.physical.run import ROOT,save,sha
from experiments.state_calibration_v14.dataset import RESULT

PATH=ROOT/'models/Qwen3-VL-8B-Instruct'
MODEL='Qwen/Qwen3-VL-8B-Instruct'


def main():
    index=json.loads((PATH/'model.safetensors.index.json').read_text());names=sorted(set(index['weight_map'].values()))
    revisions=set();weights=[];actual_keys=set();assets=[]
    for n in names:
        p=PATH/n;meta=(PATH/'.cache/huggingface/download'/f'{n}.metadata').read_text().splitlines();revisions.add(meta[0])
        with p.open('rb') as f:
            head=struct.unpack('<Q',f.read(8))[0];header=json.loads(f.read(head))
        entries={k:v for k,v in header.items() if k!='__metadata__'};actual_keys.update(entries)
        digest=sha(p)
        weights.append(dict(name=n,bytes=p.stat().st_size,sha256=digest,download_metadata_etag=meta[1],etag_match=digest==meta[1],
            complete_byte_extent=max(v['data_offsets'][1] for v in entries.values())+8+head==p.stat().st_size,
            index_mapping_exact=all(index['weight_map'].get(k)==n for k in entries)))
    for p in sorted(PATH.iterdir()):
        if not p.is_file() or p.name in names:continue
        m=PATH/'.cache/huggingface/download'/f'{p.name}.metadata'
        blob=p.read_bytes();entry=dict(name=p.name,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest())
        if m.exists():
            meta=m.read_text().splitlines();revisions.add(meta[0]);entry.update(download_metadata_etag=meta[1],git_blob_match=hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest()==meta[1])
        assets.append(entry)
    assert len(revisions)==1;revision=next(iter(revisions))
    local_ok=actual_keys==set(index['weight_map']) and all(w['etag_match'] and w['complete_byte_extent'] and w['index_mapping_exact'] for w in weights) and all(a.get('git_blob_match',True) for a in assets)
    remote=dict(queried=False,verified=False)
    try:
        from huggingface_hub import HfApi
        info=HfApi(token=False).model_info(MODEL,revision=revision,files_metadata=True)
        official={s.rfilename:dict(size=s.size,lfs_sha256=(s.lfs.sha256 if s.lfs else None)) for s in info.siblings}
        verified=info.sha==revision and all(official[w['name']]['size']==w['bytes'] and official[w['name']]['lfs_sha256']==w['sha256'] for w in weights)
        remote=dict(queried=True,verified=verified,revision=info.sha,official_shards={n:official[n] for n in names})
    except Exception as e:remote.update(error_type=type(e).__name__,error=str(e))
    receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),model_id=MODEL,revision=revision,
        revision_source='原用户HF local-dir download metadata；官方metadata核验状态单列',path=str(PATH.resolve()),
        config=json.loads((PATH/'config.json').read_text()),weights=weights,assets=assets,total_weight_bytes=sum(w['bytes'] for w in weights),
        index_keys=len(index['weight_map']),local_all_passed=local_ok,official_metadata=remote,no_weights_downloaded=True)
    save(RESULT/'model_receipt.json',receipt);assert local_ok
    print('本地分片/索引一致，revision',revision,'官方metadata verified',remote['verified'],flush=True)


if __name__=='__main__':main()
