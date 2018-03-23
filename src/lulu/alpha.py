"""
核心模块，接收网址和规则，返回爬取的内容

demo
爬取每个网站资讯的第一页

细分
1，每天监控，就是那些所有数据均是ajax的
2，以往数据，只有下一页是ajax的

那些前后端完全分离的几乎都是招标类的，而水务行业最多就是webform型

写多个逻辑来做映射，中间写适配

针对分类页:
condition 0: 普通的静态页面解析
condition 1: 需要保持sessionID
condition 2: 构造特定网址去拿到json数据
一般情况下，逻辑是：分类页 -> 文章页 -> 内容，但是后两种情况，有时候会出现：分类页 -> 内容

======================================

安徽城镇供水协会
直接就是get拿数据，可以全拿到
http://admin.ahwsa.com/php/index.php?a=list&page=1&type=2&pageSize=5  只要输入type的参数就可以了

安徽省政府采购
需要post，然后有bug，如果限定时间查，只能拿到第一页，所以不能直接构造请求
需要去逐条判断是否为当天

北京排水集团新闻动态
现在索引页拿到newsId的json数据
http://www.bdc.cn/biz200/mh204XwdtAction!getNewsList.act?pageIndex=1
然后post这个id过去就可以拿到新闻了
http://www.bdc.cn/biz200/mh204XwdtAction!getNewsContent.act?viewObj.newsId=8a82804d6187a83f0162037a0498130d
'JSESSIONID': 无法伪造，所以必须要用selenium去获取session ID
金昌市水务局

包头惠民
在这里post参数page,percount,pid到
http://www.bthmsw.com/WWW/uploads/getlist.php
拿到当前页数据的json，然后构造出对应网址
http://www.bthmsw.com/WWW/uploads/navlist/detail.html?230?3?21
就可以了

广咨电子投招标 http://www.gzebid.cn/
可以直接构造网址去get

======================================

最新页可以直接get到，后续是ajax的

东莞水投 http://www.dgstjt.com
中国环保网 http://hbw.chinaenvironment.com
东江环保 http://www.dongjiang.com.cn/
揭阳水务 http://www.jyslj.gov.cn
中华人民共和国住房和城乡建设部(官网) http://ginfo.mohurd.gov.cn/

webform的特点是首页是直接可以get到，后续分页都是post拿

"""
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from urllib.parse import urlparse, urlunparse

from lxml import etree
import requests

from logger import MyLogger
from exception import OutTryException
from utils import generate_header

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
LOGGER = MyLogger('scrap-part')


# TODO logger，常见异常的处理，DB，前端动态配置

# TODO 第一个请求的逻辑都很相似，看怎么再抽象出来


class Item:
    """ 分类页的任务单位 """
    __slots__ = ['url', 'detail', 'direct', 'json']

    def __init__(self, url, detail, direct=False, json_=False):
        self.url = url
        self.detail = detail
        self.direct = direct  # 分类是不是直接到内容
        self.json = json_  # 内容是不是json格式


class StaticItem(Item):
    """ condition 0，可以直接拿到内容 """


class HeadlessItem(Item):
    """ condition 1，需要通过无头浏览器先拿到sessionID，然后再构造POST去拿内容"""


class AjaxItem(Item):
    """ condition 2，普通的ajax，通过索引页拿到相关json数据，然后构造URL去拿内容"""


class Crawler:
    def __init__(self, items):
        if not isinstance(items, list):
            items = [items]
        self.items = items
        self.item_handle_mapper = {
            'StaticItem': self._scrape_static_core,
            # 'HeadlessItem': self._scrap_headless_core,
            'AjaxItem': self._scrap_ajax_core,
        }

    def crawl(self):
        return self._scrap()

    def _scrap(self):
        res = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            url_mapper = {
                executor.submit(self.item_handle_mapper[type(url_detail).__name__], url_detail): url_detail.url
                for url_detail in self.items
            }  # 做了映射
            # url_mapper = {executor.submit(self._scrape_static_core, url_detail): url_detail.url for url_detail in
            #               self.static_items}
            for future in as_completed(url_mapper):
                _u = url_mapper[future]
                try:
                    res[_u] = future.result()
                except OutTryException:
                    LOGGER.warning('{} 超过重试次数'.format(_u))
                except Exception as exc:
                    LOGGER.warning(('scrap static outside: ', exc))
        return res  # {'url1': urlDetail(url1, {key: value}), ...}

    def _scrape_static_core(self, url_detail):  # todo 计数
        max_try_again_time = MAX_TRY_AGAIN_TIME
        while max_try_again_time:
            try:
                response = requests.get(url_detail.url, headers=HEADER, timeout=TIMEOUT)
                if response.status_code == 200:
                    if url_detail.direct:  # 如果是直接可以获得内容，则数据形式肯定是json
                        url_detail.detail.pop('article_url_rule')  # 去掉无用规则
                        return self.fetch_json(response.json(), url_detail)
                    else:  # 否则就要从当前分类页获取文章页面的url，然后去各页面取
                        html = etree.HTML(self.transform2utf8(response))  # 要注意编码
                        article_urls = html.xpath(url_detail.detail.pop('article_url_rule'))
                        try:
                            o = urlparse(article_urls[0])
                            if not (o.scheme and o.netloc):  # 如果这部分的url是相对url，则需要拼接起来
                                _o = urlparse(url_detail.url)
                                article_urls = [urlunparse([_o.scheme, _o.netloc, _url, '', '', ''])
                                                for _url in article_urls]
                            with requests.Session() as session:  # 后面改成协程
                                session.headers.update(HEADER)
                                res = []
                                url_details = [UrlDetail(url, url_detail.detail) for url in article_urls][:5]
                                with ThreadPoolExecutor(max_workers=10) as executor:
                                    url_mapper = {executor.submit(self.fetch_thread, session, url_detail): url_detail
                                                  for url_detail in url_details}
                                    for future in as_completed(url_mapper):
                                        _u = url_mapper[future]
                                        try:
                                            res.append(future.result())
                                        except Exception as exc:
                                            LOGGER.warning(('scrap static normal: ', _u.detail, exc))
                            return res
                        except IndexError:
                            LOGGER.warning('{} 的 article url rule 部分有问题'.format(url_detail.url))
                else:  # 非超时的请求失败，后面可以再看怎么处理
                    max_try_again_time -= 1
                    continue
            except requests.Timeout:
                max_try_again_time -= 1
        else:
            raise OutTryException  # request部分失败，抛出特定异常给上层处理

    @staticmethod
    def fetch_json(json_, url_detail):  # 返回的是所有文章的UrlDetail列表
        if not isinstance(json_, list):  # 适配单个的情况
            json_ = [json_]
        res = []
        for obj in json_:
            scrape_res = {}
            for k, v in url_detail.detail.items():
                try:
                    scrape_res[k] = eval('obj{}'.format(v))
                except KeyError:
                    scrape_res[k] = None
                    LOGGER.warning('{} 的 {} 部分规则有问题'.format(url_detail.url, k))
                except Exception as exc:  # 后面可以看一下需要捕捉什么异常
                    LOGGER.warning('In fetch json: ', exc)
            res.append(UrlDetail(url=url_detail.url, detail=scrape_res))
        return res

    @staticmethod
    def fetch(text, url_detail):  # 返回的是每一个文章的UrlDetail
        html = etree.HTML(text)
        scrape_res = {}
        for k, v in url_detail.detail.items():
            try:
                ele = html.xpath(v)[0]
                # scrape_res[k] = etree.tostring(ele, encoding='utf-8').decode('utf-8')  # 提取内容
                scrape_res[k] = etree.tostring(ele, encoding='utf-8').decode('utf-8')  # 提取内容
            except IndexError:
                scrape_res[k] = None
                LOGGER.warning('{} 的 {} 部分规则有问题'.format(url_detail.url, k))
            except Exception as exc:  # 后面可以看一下需要捕捉什么异常
                LOGGER.warning('In fetch: ', exc)
        return UrlDetail(url=url_detail.url, detail=scrape_res)

    # 文章的线程函数
    def fetch_thread(self, session, url_detail, extra_cookie):
        if extra_cookie:
            session.cookies = extra_cookie
        try:
            resp = session.get(url_detail.url, timeout=TIMEOUT)
            html = etree.HTML(self.transform2utf8(resp))
            scrape_res = {}
            for k, v in url_detail.detail.items():
                try:
                    ele = html.xpath(v)[0]
                    # scrape_res[k] = etree.tostring(ele, encoding='utf-8').decode('utf-8')  # 提取内容
                    scrape_res[k] = etree.tostring(ele, encoding='utf-8').decode('utf-8')  # 提取内容
                except IndexError:
                    scrape_res[k] = None
                    LOGGER.warning('{} 的 {} 部分规则有问题'.format(url_detail.url, k))
                except Exception as exc:  # 后面可以看一下需要捕捉什么异常
                    LOGGER.warning('In fetch: ', exc)
            return UrlDetail(url=url_detail.url, detail=scrape_res)

        except requests.Timeout:
            LOGGER.warning('超时 {}'.format(url_detail.url))

    @staticmethod
    def fetch_json_thread(session, url_detail, extra_cookie):
        if extra_cookie:
            session.cookies = extra_cookie
        try:
            resp = session.get(url_detail.url, timeout=TIMEOUT)
            assert resp.status_code == 200
            scrape_res = {}
            for k, v in url_detail.detail.items():
                try:
                    scrape_res[k] = eval(v.format('resp.json()'))  # 拿到json内的数据
                except KeyError:
                    scrape_res[k] = None
                    LOGGER.warning('{} 的 {} 部分规则有问题'.format(url_detail.url, k))
                except Exception as exc:  # 后面可以看一下需要捕捉什么异常
                    LOGGER.warning('In fetch: ', exc)
            return UrlDetail(url=url_detail.url, detail=scrape_res)

        except requests.Timeout:
            LOGGER.warning('超时 {}'.format(url_detail.url))

    @staticmethod
    def get_cookies(session, url):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            return resp.cookies
        except requests.Timeout:
            pass

    @classmethod
    def transform2utf8(cls, resp):
        if resp.encoding == 'utf-8':
            return resp.text
        else:
            return resp.content.encode('gbk').decode('gbk').encode('utf-8')  # 待验证

    def _scrap_keep_alive_core(self):
        pass

    def _scrap_ajax_core(self, url_detail):
        max_try_again_time = MAX_TRY_AGAIN_TIME
        while max_try_again_time:
            try:
                response = requests.get(url_detail.url, headers=HEADER, timeout=TIMEOUT)
                if response.status_code == 200:
                    if url_detail.json:
                        _proxy_func = self.fetch_json_thread
                    else:
                        _proxy_func = self.fetch_thread

                    article_params = eval(url_detail.detail.pop('article_url_rule').format('response.json()'))
                    if url_detail.direct:  # 分类 -> content
                        query_url = url_detail.detail.pop('article_query_url')
                        article_urls = [query_url.format(param) for param in article_params]  # 构造查询文章的url

                        extra_cookies = None
                        url_details = [(UrlDetail(url, url_detail.detail), extra_cookies) for url in article_urls]

                    else:  # 分类 -> 文章 -> content
                        param_cookies_mapper = {}
                        with requests.Session() as session:
                            session.headers.update(HEADER)
                            # session.cookies = response.cookies
                            _middle_url = url_detail.detail.pop('article_middle_url_rule')
                            with ThreadPoolExecutor(max_workers=10) as executor:
                                url_mapper = {
                                    executor.submit(self.get_cookies, session, _middle_url.format(_param)): _param
                                    for _param in article_params
                                }
                                for future in as_completed(url_mapper):
                                    _param = url_mapper[future]
                                    try:
                                        param_cookies_mapper[_param] = future.result()
                                    except Exception as exc:
                                        LOGGER.warning(('scrap sub get cookie: ', _middle_url.format(_param), exc))
                        _query_url = url_detail.detail.pop('article_query_url')
                        url_details = [(UrlDetail(_query_url.format(k), url_detail.detail), v)
                                       for k, v in param_cookies_mapper.items() if v]  # 每个id有自己的sessionID

                    with requests.Session() as session:  # 后面改成协程
                        session.headers.update(HEADER)
                        res = []
                        with ThreadPoolExecutor(max_workers=10) as executor:
                            url_mapper = {executor.submit(_proxy_func, session, *url_detail): url_detail[0]
                                          for url_detail in url_details}
                            for future in as_completed(url_mapper):
                                _u = url_mapper[future]
                                try:
                                    res.append(future.result())
                                except Exception as exc:
                                    LOGGER.warning(('scrap ajax normal: ', _u.detail, exc))
                    return res
                else:  # 非超时的请求失败，后面可以再看怎么处理
                    max_try_again_time -= 1
                    continue
            except requests.Timeout:
                max_try_again_time -= 1
        else:
            raise OutTryException  # request部分失败，抛出特定异常给上层处理


if __name__ == '__main__':
    hh_text = '''
    Accept: application/json, text/javascript, */*; q=0.01
Accept-Encoding: gzip, deflate
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Cache-Control: no-cache
Connection: keep-alive
Content-Length: 0
Cookie: JSESSIONID=2ABC83592DE4F87623AEB5D90696FE27
Pragma: no-cache
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:59.0) Gecko/20100101 Firefox/59.0
X-Requested-With: XMLHttpRequest
'''
    # from utils import generate_header
    #
    # rr = requests.post(
    #     'http://www.bdc.cn/biz200/mh204XwdtAction!getNewsContent.act?viewObj.newsId=8a82804d6187a83f0162037a0498130d',
    #     headers=generate_header(hh_text),
    #     proxies={'http': '127.0.0.1:8877'},
    # )
    # print(rr.json())
    pass
