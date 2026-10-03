"""显式物理投影与规范容器比较；保留所有物理/接触字段，无容差。"""
import gzip
import hashlib
import json
from experiments.structure_handoff_v15.reference_audit import normalize_containers,physical_equal

PHYSICAL_FIELDS={'tick','time','joint_positions','ee','objects','partner_position','partner_joint','partner_velocity','partner_command','contacts'}
ANNOTATIONS={'phase','availability','delivery_start_tick','delivery_event','delivery_facts','robot_target_item'}


def physics(state):
    assert set(state)==PHYSICAL_FIELDS|ANNOTATIONS,('未分类字段',set(state)-(PHYSICAL_FIELDS|ANNOTATIONS))
    return normalize_containers({k:state[k] for k in sorted(PHYSICAL_FIELDS)})


def physics_equal(a,b):return physical_equal(physics(a),physics(b))


def trace_digest(path,last_tick=None):
    digest=hashlib.sha256();count=0
    with gzip.open(path,'rt') as f:
        for line in f:
            state=json.loads(line)
            if last_tick is not None and state['tick']>last_tick:break
            digest.update(json.dumps(physics(state),sort_keys=True,separators=(',',':')).encode());count+=1
    return dict(canonical_physical_sha256=digest.hexdigest(),ticks=count)
