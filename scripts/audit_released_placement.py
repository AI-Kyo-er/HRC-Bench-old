#!/usr/bin/env python3
"""离线重建显式持物与载荷下的放置释放边界，保留原始摘要。"""
import argparse
import json
from pathlib import Path

from hrc_pilot.released_placement_audit import audit_run


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True)
    parser.add_argument('--object-id',required=True)
    parser.add_argument('--receiver-id',required=True)
    parser.add_argument('--required-release-object-ids',nargs='+')
    args=parser.parse_args()
    result=audit_run(args.input_dir,args.object_id,args.receiver_id,args.required_release_object_ids)
    (args.input_dir/'released_placement_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({key:result[key] for key in ['status','original_first_success_s',
        'released_first_success_s','terminal_released_stable_placement',
        'conflicting_original_success_samples','human_owned_conflicting_samples']},ensure_ascii=False))
