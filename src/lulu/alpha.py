"""
核心模块，接收网址和规则，返回爬取的内容

细分
1，每天监控，就是那些所有数据均是ajax的
2，以往数据，只有下一页是ajax的

那些前后端完全分离的几乎都是招标类的，而水务行业最多就是webform型

写多个逻辑来做映射，中间写适配

condition 0: 普通的静态页面分析
condition 1: 需要用无头浏览器去拿sessionID
condition 2: 可以通过构造特定网址去get

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
from urllib.parse import unquote

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


class Item:
    """ 单个任务单位 """
    __slots__ = ['url', 'detail']

    def __init__(self, url, detail):
        self.url = url
        self.detail = detail


class StaticItem(Item):
    """ condition 0，可以直接拿到内容 """


class HeadlessItem(Item):
    """ condition 1，需要通过无头浏览器先拿到sessionID，然后再构造POST去拿内容"""


class AjaxItem(Item):
    """ condition 3，普通的ajax，通过索引页拿到相关json数据，然后构造URL去拿内容"""


def fetch():
    pass


def transform2utf8(resp):
    if resp.encoding == 'utf-8':
        return resp.text
    else:
        return resp.content.encode('gbk').decode('gbk').encode('utf-8')  # 待验证


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
                        ele = html.xpath(v)[0]
                        # scrape_res[k] = etree.tostring(ele, encoding='utf-8').decode('utf-8')  # 提取内容
                        scrape_res[k] = etree.tostring(ele, encoding='utf-8').decode('utf-8')  # 提取内容
                    except IndexError:
                        scrape_res[k] = None
                        LOGGER.warning('{} 的 {} 部分规则有问题'.format(url_detail.url, k))
                    except Exception as exc:  # 后面可以看一下需要捕捉什么异常
                        LOGGER.warning('inside', exc)
                return UrlDetail(url=url_detail.url, detail=scrape_res)

            else:  # 非超时的请求失败，后面可以再看怎么处理
                max_try_again_time -= 1
                continue
        except requests.Timeout:
            max_try_again_time -= 1
    else:
        raise OutTryException  # request部分失败，抛出特定异常给上层处理


def scrape(url_details):
    res = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        url_mapper = {executor.submit(scrape_core, url_detail): url_detail for url_detail in url_details}
        for future in as_completed(url_mapper):
            _u = url_mapper[future]
            try:
                res.append({_u.url: future.result()})
            except OutTryException:
                LOGGER.warning('{} 超过重试次数'.format(_u.url))
            except Exception as exc:
                print('outside', exc)
    return res  # ['url1': urlDetail(url1, {key: value})]


def ajax_core(url_detail):
    pass


def scrape_ajax(url_detail):
    pass


if __name__ == '__main__':
    rr = '''
'''

    # pp = {'http': '127.0.0.1:8877'}
    # rr = requests.post(
    #     'http://admin.ahwsa.com/php/index.php?a=list&page=1&type=1&pageSize=5',
    # 'http://www.bdc.cn/biz200/mh204XwdtAction!getNewsContent.act?viewObj.newsId=8a82804d6187a83f0162037a0498130d',
    # headers=HEADER,
    # headers=generate_header(rr),
    # proxies=pp)
    # print(rr.json())
    uu = UrlDetail('ss', 'bb')
    print(type(uu).__name__)
