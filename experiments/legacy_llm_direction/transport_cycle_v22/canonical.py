"""复用已验证的完整物理投影，仅剥离新循环观测/历史注解。"""
import gzip
import hashlib
import json
from experiments.structure_foundation_v20.canonical import physics as parent_physics
from experiments.structure_handoff_v15.reference_audit import normalize_containers


def physics(state):
    return parent_physics({k:v for k,v in state.items() if k not in ('cycle','current_carrier_facts')})


def equal(a,b):return physics(a)==physics(b)


def content_equal(a,b):return normalize_containers(a)==normalize_containers(b)


def digest(path):
    h=hashlib.sha256();count=0
    with gzip.open(path,'rt') as f:
        for line in f:h.update(json.dumps(physics(json.loads(line)),sort_keys=True,separators=(',',':')).encode());count+=1
    return dict(sha256=h.hexdigest(),ticks=count)
