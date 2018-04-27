from datetime import datetime
import re

__all__ = ['generate_header', 'handle_time_format']


def generate_header(raw_text=None, delimiter=': '):
    if raw_text is None:
        raw_text = '''\
Accept: application/json, text/javascript, */*; q=0.01
Accept-Encoding: gzip, deflate
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Cache-Control: no-cache
Connection: keep-alive
Content-Length: 0
Pragma: no-cache
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:59.0) Gecko/20100101 Firefox/59.0\
'''
    _header = {}
    for line in raw_text.split('\n'):
        line = line.strip()
        if line:
            k, v = line.split(delimiter)
            _header[k] = v
    return _header


def handle_time_format(string):
    build_formats = [
        '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
        '\d{4}-\d{2}-\d{2} \d{2}:\d{2}',
        '\d{4}-\d{2}-\d{2}',
        '\d{4}年\d{2}月\d{2}日',
        '\d{4}/\d{2}/\d{2}',
        '\d{4}\.\d{2}\.\d{2}',
    ]
    format_mapper = {
        '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}': '%Y-%m-%d %H:%M:%S',
        '\d{4}-\d{2}-\d{2} \d{2}:\d{2}': '%Y-%m-%d %H:%M',
        '\d{4}-\d{2}-\d{2}': '%Y-%m-%d',
        '\d{4}年\d{2}月\d{2}日': '%Y年%月%d日',
        '\d{4}/\d{2}/\d{2}': '%Y/%m/%d',
        '\d{4}\.\d{2}\.\d{2}': '%Y.%m.%d',
    }
    for _format in build_formats:
        match_result = re.search(_format, string)
        if match_result:
            time_string = match_result.group()
            return datetime.strptime(time_string, format_mapper[_format])
    else:
        return False
