import json

from hrc_pilot.native_run_journal import NativeRunJournal,native_time_limits


def test_sustained_horizon_covers_warmup_and_never_resets_at_native_limit():
    options=native_time_limits(1200,10,True)
    assert options['horizon']>1210 and options['ignore_done']
    assert not native_time_limits(280,10,False)['ignore_done']


def test_streaming_logs_remain_readable_after_interrupted_batch(tmp_path):
    journal=NativeRunJournal(tmp_path);records=[{'time_s':0.,'raw_output':'保持自己的目标'}]
    journal.flush({'human_planner_io.jsonl':records});journal.flush({'human_planner_io.jsonl':records})
    records.append({'time_s':6.,'raw_output':'依据真实接触调整'})
    journal.flush({'human_planner_io.jsonl':records})
    saved=[json.loads(l) for l in (tmp_path/'human_planner_io.jsonl').read_text().splitlines()]
    assert saved==records
