"""
核心模块，接收网址和规则，返回爬取的内容

"""
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
import requests

HEADER = {}
MAX_TRY_AGAIN_TIME = 3
TIMEOUT = 3
UrlRule = namedtuple('UrlRule', ['url', 'rule'])  # url是网址，rule中是字典: {内容1: 规则1, ...}


def fetch():
    pass


def scrape_core(url_rule):
    max_try_again_time = MAX_TRY_AGAIN_TIME
    while max_try_again_time:
        try:
            response = requests.get(url_rule.url, headers=HEADER, timeout=TIMEOUT)
            if response.status_code == 200:
                pass
            else:  # 非超时的请求失败，后面可以再看怎么处理
                max_try_again_time -= 1
                continue
        except requests.Timeout:
            max_try_again_time -= 1
    else:
        raise requests.RequestException  # request部分失败，抛出特定异常给上层处理


def scrape(url_rules):
    # with requests.Session() as session:  # 无复用session的意义
    #     session.headers.update(HEADER)
    res = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        url_mapper = {executor.submit(scrape, url_rule): url_rule for url_rule in url_rules}
        for future in as_completed(url_mapper):
            _u = url_mapper[future]
            try:
                res.append({_u.url: future.result()})
            except requests.RequestException:
                print()
            except Exception as exc:
                print(exc)


if __name__ == '__main__':
    test_url = [
        'http://www.zjswater.gov.cn/ContentSubList.aspx?sortid=2&typeid=2&title=%E6%B0%B4%E5%8A%A1%E8%A6%81%E9%97%BB&subtitle=%E6%B0%B4%E5%8A%A1%E5%8A%A8%E6%80%81']