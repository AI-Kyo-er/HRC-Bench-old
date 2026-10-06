#!/usr/bin/env python3
"""本地浏览实验报告，支持Sim视频HTTP Range以便拖动时间轴。"""
import argparse
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import re


class ReportHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        self.remaining=None
        header=self.headers.get('Range')
        path=Path(self.translate_path(self.path))
        if not header or not path.is_file():return super().send_head()
        match=re.fullmatch(r'bytes=(\d*)-(\d*)',header.strip())
        size=path.stat().st_size
        if not match or not any(match.groups()) or not size:
            self.send_error(416,'Invalid byte range');return None
        first,last=match.groups()
        start=int(first) if first else max(0,size-int(last))
        end=min(size-1,int(last)) if first and last else size-1
        if start> end or start>=size:
            self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return None
        stream=path.open('rb');stream.seek(start);self.remaining=end-start+1
        self.send_response(206)
        self.send_header('Content-type',self.guess_type(str(path)))
        self.send_header('Content-Length',str(self.remaining))
        self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.send_header('Accept-Ranges','bytes');self.end_headers()
        return stream

    def copyfile(self,source,output):
        if self.remaining is None:return super().copyfile(source,output)
        while self.remaining:
            data=source.read(min(65536,self.remaining))
            if not data:break
            output.write(data);self.remaining-=len(data)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8123)
    args=parser.parse_args()
    print(f'http://127.0.0.1:{args.port}/README.md',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),ReportHandler).serve_forever()


if __name__=='__main__':main()
