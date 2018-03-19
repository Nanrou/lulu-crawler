"""
核心模块，接收网址和规则，返回爬取的内容

"""
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from lxml import etree
import requests

HEADER = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:59.0) Gecko/20100101 Firefox/59.0'}
MAX_TRY_AGAIN_TIME = 3
TIMEOUT = 3
UrlDetail = namedtuple('UrlDetail', ['url', 'detail'])  # url是网址，detail中是字典: {内容1: 规则1, ...}


def fetch():
    pass


def transform2utf8(resp):
    if resp.encoding == 'utf-8':
        return resp.text
    else:
        return resp.content.encode('gbk').decode('gbk').encode('utf-8')  #  待验证


def scrape_core(url_detail):
    max_try_again_time = MAX_TRY_AGAIN_TIME
    while max_try_again_time:
        try:
            response = requests.get(url_detail.url, headers=HEADER, timeout=TIMEOUT)
            if response.status_code == 200:
                text = transform2utf8(response)  # 要注意编码
                html = etree.HTML(text)
                scrape_res = {}
                for k, v in url_detail.detail.items():
                    try:
                        ele = html.xpath(v)[0]  # 提取内容
                        scrape_res[k] = etree.tostring(ele, encoding='utf-8').decode('utf-8')  # 提取内容
                    except IndexError:
                        scrape_res[k] = None
                    except Exception as exc:  # 后面可以看一下需要捕捉什么异常
                        print('inside', exc)
                return UrlDetail(url=url_detail.url, detail=scrape_res)

            else:  # 非超时的请求失败，后面可以再看怎么处理
                max_try_again_time -= 1
                continue
        except requests.Timeout:
            max_try_again_time -= 1
    else:
        raise requests.RequestException  # request部分失败，抛出特定异常给上层处理


def scrape(url_details):
    res = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        url_mapper = {executor.submit(scrape_core, url_detail): url_detail for url_detail in url_details}
        for future in as_completed(url_mapper):
            _u = url_mapper[future]
            try:
                res.append({_u.url: future.result()})
            except requests.RequestException:
                print()
            except Exception as exc:
                print('outside', exc)
    return res  # ['url1': urlDetail(url1, {key: value})]


if __name__ == '__main__':
    pass
