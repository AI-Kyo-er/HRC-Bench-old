#!/usr/bin/env python3
"""核对终态案例解释的证据引用，不改动原始实验记录。"""
import argparse
import json
from pathlib import Path

from hrc_pilot.joint_review_evidence import verify_review


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    args = parser.parse_args()
    result = verify_review(args.input_dir)
    (args.input_dir / 'review_evidence_verification.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({'status': result['status'], 'findings': len(result['findings']),
                      'semantic_validity': result['semantic_validity']}, ensure_ascii=False))
