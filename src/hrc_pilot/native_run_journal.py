"""运行中追加原始记录，防止环境异常或终止造成整段证据丢失。"""
import json
from pathlib import Path


def native_time_limits(steps,settle_steps=10,continuous=False):
    return {'horizon':max(1000,steps+settle_steps+1),'ignore_done':bool(continuous)}


class NativeRunJournal:
    def __init__(self,directory):
        self.directory=Path(directory);self.cursors={}

    def flush(self,streams):
        for name,records in streams.items():
            cursor=self.cursors.get(name,0)
            assert cursor<=len(records)
            if cursor==len(records):continue
            with (self.directory/name).open('a',encoding='utf-8') as out:
                for row in records[cursor:]:out.write(json.dumps(row,ensure_ascii=False)+'\n')
            self.cursors[name]=len(records)
