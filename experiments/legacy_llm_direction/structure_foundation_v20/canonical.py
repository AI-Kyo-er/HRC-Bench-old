"""新World全物理投影；容器规范化，保留精度与完整contact。"""
import gzip
import hashlib
import json
from experiments.responsive_transport_v16.canonical import PHYSICAL_FIELDS,ANNOTATIONS
from experiments.structure_handoff_v15.reference_audit import normalize_containers

NEW_ANNOTATIONS={'inspection_facts','presence_motion','presence_events','return_start_tick','return_origin','return_event','payload_return_event','return_facts'}
def physics(state):
    assert set(state)==PHYSICAL_FIELDS|ANNOTATIONS|NEW_ANNOTATIONS|{'presence'}
    result={k:state[k] for k in PHYSICAL_FIELDS}
    result['presence']=None if state['presence'] is None else {k:state['presence'][k] for k in ('joint','velocity','position','target')}
    return normalize_containers(result)
def equal(a,b):return physics(a)==physics(b)
def digest(path):
    h=hashlib.sha256();count=0
    with gzip.open(path,'rt') as f:
        for line in f:h.update(json.dumps(physics(json.loads(line)),sort_keys=True,separators=(',',':')).encode());count+=1
    return dict(sha256=h.hexdigest(),ticks=count)
