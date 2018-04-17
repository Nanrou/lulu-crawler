from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
from urllib.parse import urlparse, urlunparse

from lxml import etree
from html2text import HTML2Text
import requests

from logger import MyLogger
from exception import OutTryException
from utils import generate_header
from bloom_filter import MyBloomFilter

"""
过滤操作，暂时直接在主逻辑里判断
注意，要针对两种情况分别判断，StaticItem的是url+title，而AjaxItem的是url
"""

HEADER = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:59.0) Gecko/20100101 Firefox/59.0',
}
MAX_TRY_AGAIN_TIME = 3
TIMEOUT = 3
UrlDetail = namedtuple('UrlDetail', ['url', 'detail'])  # url是网址，detail中是字典: {内容1: 规则1, ...}
LOGGER = MyLogger(__file__)
BloomFilter = MyBloomFilter()

TextMaker = HTML2Text()
TextMaker.ignore_links = True
TextMaker.ignore_images = True
TextMaker.ignore_tables = True
TextMaker.single_line_break = True


class Item:
    """ 分类页的任务单位 """
    __slots__ = ['url', 'detail', 'is_direct', 'is_json']

    def __init__(self, url, detail, is_direct=False, is_json=False):
        self.url = url
        self.detail = detail
        self.is_direct = is_direct  # 分类是不是直接到内容
        # self.is_json = is_json  # 内容是不是json格式
        # 现在只针对json数据形式


class StaticItem(Item):
    """ condition 0，普通的前后端分离，可以直接拿到内容 """


class AjaxItem(Item):
    """ condition 1，需要通过索引页拿到相关json数据，然后构造文章URL再去拿内容"""


class Crawler:
    def __init__(self, items, debug: bool=False):
        if not isinstance(items, list):
            items = [items]
        self.items = items
        self.item_handle_mapper = {
            'StaticItem': self._scrape_static_core,
            'AjaxItem': self._scrap_ajax_core,
        }
        self.debug = debug

    def _scrap(self):
        res = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            url_mapper = {
                executor.submit(self.item_handle_mapper[type(url_detail).__name__], url_detail): url_detail.url
                for url_detail in self.items
            }  # 做了映射
            for future in as_completed(url_mapper):
                _u = url_mapper[future]
                try:
                    res[_u] = future.result()
                except OutTryException:
                    LOGGER.warning('超过重试次数 {}'.format(_u))
                except Exception as exc:
                    LOGGER.warning((_u, '最外层: ', exc))

        # 统计
        _count = 0
        for k, v in res.items():
            _count += len(v)
        LOGGER.info('本次爬取新增[{}]条记录'.format(_count))

        return res  # {'url1': [urlDetail(url1-1, {key: value})], ...}

    def _scrape_static_core(self, url_detail):  # 只处理普通的json式数据
        response = self._handle_request(url_detail.url)
        # 去掉无用规则
        url_detail.detail.pop('article_url_rule')
        url_detail.detail.pop('article_middle_url_rule')
        url_detail.detail.pop('article_query_url')

        return self._fetch_json_static(response.json(), url_detail)  # 从json中提取数据

    def _scrap_ajax_core(self, url_detail):
        category_response = self._handle_request(url_detail.url)
        # 通过索引页提取文章的参数
        article_params = eval(url_detail.detail.pop('article_url_rule').format('category_response.json()'))
        query_url = url_detail.detail.pop('article_query_url')

        if url_detail.is_direct:  # 索引页 -> content_json
            url_detail.detail.pop('article_middle_url_rule')  # 去掉无用属性
            article_urls = [query_url.format(param) for param in article_params]  # 构造查询文章的url
            url_details = [(UrlDetail(url, url_detail.detail), None) for url in article_urls]  # 将cookie也包到tuple中
        else:  # 索引页 -> 文章页面 -> content_json
            param_cookies_mapper = {}
            with requests.Session() as session:  # 这一步是去拿每个文章页的cookie
                session.headers.update(HEADER)
                _middle_url = url_detail.detail.pop('article_middle_url_rule')
                with ThreadPoolExecutor(max_workers=3) as executor:
                    url_mapper = {
                        executor.submit(self._handle_request, _middle_url.format(_param), session): _param
                        for _param in article_params
                    }
                    for future in as_completed(url_mapper):
                        _param = url_mapper[future]
                        try:
                            param_cookies_mapper[_param] = future.result().cookies
                        except Exception as exc:
                            LOGGER.warning(('获取cookie失败 ', _middle_url.format(_param), exc))

            url_details = [(UrlDetail(query_url.format(k), url_detail.detail), v)
                           for k, v in param_cookies_mapper.items() if v]  # 每个文章有自己的sessionID/cookie
        # 过滤
        if self.debug:
            filter_url_details = [u for u in url_details]
        else:
            filter_url_details = [u for u in url_details if not BloomFilter.is_contain(u[0].url)]

        with requests.Session() as session:  # 后面改成协程
            session.headers.update(HEADER)
            res = []
            with ThreadPoolExecutor(max_workers=3) as executor:
                url_mapper = {executor.submit(self._thread_func_fetch_json, session, *url_detail): url_detail[0]
                              for url_detail in filter_url_details}
                for future in as_completed(url_mapper):
                    _u = url_mapper[future]
                    try:
                        res.append(future.result())
                        if not self.debug:
                            BloomFilter.insert(_u.url)
                    except Exception as exc:
                        LOGGER.warning(('获取content_json失败 ', _u.url, exc))
        return res

    def _fetch_json_static(self, json_, url_detail):
        if not isinstance(json_, list):  # 适配单个的情况
            json_ = [json_]
        res = []
        for index, obj in enumerate(json_):
            scrape_res = {}
            fail_time = 0
            for k, v in url_detail.detail.items():
                try:
                    if v is None:
                        scrape_res[k] = None
                        continue
                    scrape_res[k] = eval(v.format('obj'))
                except KeyError:
                    scrape_res[k] = None
                    LOGGER.info('{} 的 {} 部分规则有问题'.format(url_detail.url, k))
                    fail_time += 1
                except Exception as exc:  # 后面可以看一下需要捕捉什么异常
                    LOGGER.warning(('In statics core json: ', exc))
                    fail_time += 1
            if fail_time > 3:
                LOGGER.warning('提取数据失败 {}的第{}项'.format(url_detail.url, index))
            else:  # 过滤判断
                if self.debug:
                    res.append(UrlDetail(url=url_detail.url, detail=scrape_res))
                else:
                    if BloomFilter.is_contain(''.join([url_detail.url, scrape_res['article_title_rule']])):
                        continue
                    else:
                        res.append(UrlDetail(url=url_detail.url, detail=scrape_res))
                        BloomFilter.insert(''.join([url_detail.url, scrape_res['article_title_rule']]))
        return res

    @staticmethod
    def _fetch_json_ajax(json_, url_detail):
        scrape_res = {}
        fail_time = 0
        for k, v in url_detail.detail.items():
            try:
                if v is None:
                    scrape_res[k] = None
                    continue
                scrape_res[k] = eval(v.format('json_'))  # 注意这里动态解析
            except KeyError:
                scrape_res[k] = None
                LOGGER.info('{} 的 {} 部分规则有问题'.format(url_detail.url, k))
                fail_time += 1
            except Exception as exc:  # 后面可以看一下需要捕捉什么异常
                LOGGER.warning(('In ajax core json: ', exc))
                fail_time += 1
        if fail_time > 3:
            LOGGER.warning('提取数据失败 {}'.format(url_detail.url))
        else:
            return UrlDetail(url=url_detail.url, detail=scrape_res)

    def _thread_func_fetch_json(self, session, url_detail, extra_cookie=None):
        response = self._handle_request(url_detail.url, session, extra_cookie)
        return self._fetch_json_ajax(response.json(), url_detail)

    @staticmethod
    def _handle_request(url, session=None, extra_cookie=None):  # 将请求这个动作单独抽象出来
        max_try_again_time = MAX_TRY_AGAIN_TIME
        if session and extra_cookie:
            session.cookies = extra_cookie
        while max_try_again_time:
            try:
                if session:
                    resp = session.get(url, timeout=TIMEOUT)
                else:
                    resp = requests.get(url, headers=HEADER, timeout=TIMEOUT)
                if resp.status_code == 200:
                    return resp
                else:
                    max_try_again_time -= 1
            except requests.Timeout:
                max_try_again_time -= 1
        else:
            raise OutTryException

    # TODO: rename to crawl
    def first_crawl(self):
        return self._scrap()

    def crawl(self):
        return self._scrap()

    # 单次测试爬取
    def test_crawl(self):
        res = []
        for k, v in self._scrap().items():
            if not v:
                continue
            for single_url in v:
                single_part = dict(
                    url=single_url.url,

                    title=TextMaker.handle(single_url.detail['article_title_rule'])
                    if single_url.detail['article_title_rule'] else None,
                    author=TextMaker.handle(single_url.detail['article_author_rule'])
                    if single_url.detail['article_author_rule'] else None,
                    publish_time=TextMaker.handle(single_url.detail['article_publish_time_rule'])
                    if single_url.detail['article_publish_time_rule'] else datetime.now(),
                    content=TextMaker.handle(single_url.detail['article_content_rule'])
                    if single_url.detail['article_content_rule'] else None,
                )
                res.append(single_part)
        return res


if __name__ == '__main__':
    pass
