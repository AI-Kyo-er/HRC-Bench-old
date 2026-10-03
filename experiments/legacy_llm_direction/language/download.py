"""只下载公开模型，不读取或发送HF凭据。"""
from huggingface_hub import snapshot_download
from experiments.language.run import MODEL_ID, REVISION

if __name__ == '__main__':
    snapshot_download(MODEL_ID, revision=REVISION,
        local_dir='models/Qwen2.5-3B-Instruct', token=False,
        allow_patterns=['*.json','*.safetensors','*.txt','*.md'],max_workers=3)
