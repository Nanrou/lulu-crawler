__all__ = ['generate_header']


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
