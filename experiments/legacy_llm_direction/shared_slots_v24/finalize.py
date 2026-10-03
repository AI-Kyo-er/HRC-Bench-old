"""report真实退出后记录完整日志及终态，不改运行/审计结果。"""
import json
from pathlib import Path
from experiments.physical.run import save,sha
from experiments.shared_slots_v24.run import RESULT


def finalize():
    path=RESULT/'execution_receipt.json';receipt=json.loads(path.read_text());raw=RESULT/'raw'
    original=raw/'execution_receipt_report_phase.json'
    assert not original.exists();original.write_bytes(path.read_bytes())
    source=raw/'report_sources';source.mkdir(parents=True,exist_ok=True)
    (source/'report.py').write_bytes(Path(__file__).with_name('report.py').read_bytes())
    receipt.update(report_exit=0,report_terminal_source='exec_command真实exit0；无句柄仍活',finalizer_source_sha256=sha(Path(__file__)),
        report_phase_receipt_sha256=sha(original),report_source_copy_sha256=sha(source/'report.py'),
        log_sha256={p.name:sha(p) for p in raw.glob('*.log')},raw_bytes=sum(p.stat().st_size for p in raw.rglob('*') if p.is_file()))
    save(path,receipt);print('最终回执记录完整日志/实际终态',flush=True)


if __name__=='__main__':finalize()
