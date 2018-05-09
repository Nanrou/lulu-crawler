from concurrent.futures import ThreadPoolExecutor, as_completed
import smtplib
from email.header import Header
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pickle
import time
from random import randint
import os

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from lxml import etree
import requests

import sys

PROJECT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_DIR)

from db.orm import SwordFishTable, MYSQL_DB
from exception import OutTryException
from lulu.beta import HEADER
from logger import MyLogger
from utils.bloom_filter import MyBloomFilter

from unfollow import EMAIL, PSW, MAIL_HOST, RECEIVERS

EMAIL_HTML = '''
<html>
  <head></head>
  <body>
    <img src="cid:image">
  </body>
</html>
'''

BloomFilter = MyBloomFilter(key_name='shuiwujia:sf')
LOGGER = MyLogger(__file__)

QR_CODE_XPATH = "//img[@id='layerImg-login']"
DATE_XPATH = "//div[@class='fl timer']/ul/li[2]"
CATEGORY_XPATH = "//div[@class='searchControl']//div[@class='info-content']//font[@class='parent-node'][2]"
INPUT_XPATH = "//input[@id='searchinput']"
DATA_ID_XPATH = "//div[@class='lucene'][1]/ul/li/div/div//div[@class='left-title']/a"
ORIGINAL_XPATH = "//div[@class='original-text']/a/@href"


class SwordFish:
    def __init__(self, debug=False):
        self.debug = debug
        if self.debug:
            LOGGER.debug('------- DEBUG MODE --------')

    def _headless_request(self):
        op = webdriver.FirefoxOptions()
        op.add_argument('-headless')
        browser = webdriver.Firefox(options=op)
        LOGGER.debug('SF: browser start')

        browser.get('https://www.jianyu360.com/jylab/supsearch/index.html')
        LOGGER.debug('SF: get index.html')

        if os.path.exists('./cookie.pickle'):
            for _cookie in self._load_cookie('browser_cookie'):  # 注意browser的cookie格式
                browser.add_cookie({'name': _cookie['name'], 'value': _cookie['value']})
            browser.get('https://www.jianyu360.com/jylab/supsearch/index.html')

        # 登陆，存cookies
        try:
            browser.find_element_by_xpath('//div[@id="login"]/img')
        except NoSuchElementException:
            qr_url = browser.find_element_by_xpath(QR_CODE_XPATH).get_attribute('src')
            LOGGER.debug('SF: get qr {}'.format(qr_url))
            try:
                self._send_email(qr_url)  # TODO WeChat robot
                LOGGER.debug('SF: waiting to signIn')
            except smtplib.SMTPException as e:
                LOGGER.warning('SF: email error: ', e)
                browser.quit()
            try:
                WebDriverWait(browser, 60 * 10).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@id="login"]/img'))
                )  # 等待登陆
                self._save_cookie(browser.get_cookies())
            except NoSuchElementException or KeyboardInterrupt:
                # TODO log
                browser.quit()

        LOGGER.debug('SF: signIn success')

        browser.find_element_by_xpath(DATE_XPATH).click()  # 选择7天以内
        browser.find_element_by_xpath(CATEGORY_XPATH).click()  # 只选招标

        browser.find_element_by_xpath(INPUT_XPATH).send_keys('水务', Keys.ENTER)  # TODO 多个关键字

        pagination_flag = True
        filter_article_ids = []

        # 搜索结果页操作
        try:
            while pagination_flag:
                WebDriverWait(browser, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@class='lucene'][1]/ul/li"))
                )  # 等待加载内容
                time.sleep(2)
                data_elements = browser.find_elements_by_xpath(DATA_ID_XPATH)
                if self.debug:
                    _filter_articles = [ele.get_attribute('dataid') for ele in data_elements]
                    pagination_flag = False
                else:
                    _filter_articles = [ele.get_attribute('dataid') for ele in data_elements if
                                        not BloomFilter.is_contain(ele.get_attribute('dataid'))]
                    # 有过滤的id 或者 翻页disable
                    next_ele = browser.find_element_by_xpath("//div[@class='pagination-inner fr']/a[2]")
                    if len(_filter_articles) != len(data_elements) or 'disabled' in next_ele.get_attribute('class'):
                        pagination_flag = False
                    else:
                        WebDriverWait(browser, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//div[@class='pagination-inner fr']/a[2]"))
                        )  # 等待加载翻页
                        next_ele.click()
                filter_article_ids.extend(_filter_articles)
        except NoSuchElementException:
            pass
        else:
            LOGGER.debug('SF: {} articles to being crawler'.format(len(filter_article_ids)))
            self._scrap_core(filter_article_ids)
        finally:
            browser.quit()

    def _scrap_core(self, filter_articles):
        with requests.Session() as session:  # 后面改成协程
            session.headers.update(HEADER)
            session.cookies.update(self._load_cookie('request_cookie'))
            res = []
            with ThreadPoolExecutor(max_workers=3) as executor:
                url_mapper = {executor.submit(self._thread_scrap_func, session, data_id): data_id
                              for data_id in filter_articles}
                for future in as_completed(url_mapper):
                    _u = url_mapper[future]
                    try:
                        res.append(future.result())
                        if not self.debug:
                            BloomFilter.insert(_u)  # 去重
                    except Exception as exc:
                        LOGGER.warning(('SF: 获取content失败 ', _u, exc))
        self._store(res)

    def _thread_scrap_func(self, session, data_id):
        resp = self._handle_session(session, 'https://www.jianyu360.com/article/content/{}.html'.format(data_id))
        return [data_id] + self._fetch_content(self.transform2utf8(resp))

    @staticmethod
    def _handle_session(session, url):
        max_try_again_time = 3
        while max_try_again_time:
            try:
                resp = session.get(url, timeout=randint(1, 3))
                if resp.status_code == 200:
                    return resp
                else:
                    max_try_again_time -= 1
            except requests.Timeout:
                max_try_again_time -= 1
        else:
            raise OutTryException

    @staticmethod
    def _fetch_content(content):
        body = etree.HTML(content)
        title = body.xpath('string(//head/title)').replace(' - 剑鱼招标订阅', '')
        original_url = body.xpath('string(' + ORIGINAL_XPATH + ')')
        return [title, original_url]

    @staticmethod
    def _load_cookie(type_):
        with open('./cookie.pickle', 'rb') as rf:
            return pickle.load(rf).get(type_)

    @staticmethod
    def _save_cookie(cookie_dict):
        with open('./cookie.pickle', 'wb') as wf:
            pickle.dump({
                'browser_cookie': cookie_dict,
                'request_cookie': {item['name']: item['value'] for item in cookie_dict},
            }, wf)

    @staticmethod
    def _send_email(qr_url):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header('要扫描登陆', 'utf-8')
        _response = requests.get(qr_url, headers=HEADER)
        msg_image = MIMEImage(_response.content)
        msg_image.add_header('Content-ID', '<image>')
        msg.attach(msg_image)

        content = MIMEText(EMAIL_HTML, 'html', 'utf-8')
        msg.attach(content)

        msg['From'] = 'SF_小可爱'
        msg['To'] = ','.join(RECEIVERS)

        # smtp_obj = smtplib.SMTP()
        # smtp_obj.connect(MAIL_HOST, 25)
        smtp_obj = smtplib.SMTP_SSL(MAIL_HOST)
        smtp_obj.login(EMAIL, PSW)
        smtp_obj.sendmail(
            EMAIL, RECEIVERS, msg.as_string()
        )
        smtp_obj.quit()

    def run(self):
        self._headless_request()

    @classmethod
    def transform2utf8(cls, resp: requests.Response):
        if resp.encoding == 'utf-8':
            return resp.text
        try:
            return resp.content.decode('utf-8')  # 先猜文档本身是utf8，只是没从头部识别出来
        except UnicodeDecodeError:
            return resp.content.decode('gbk').encode('utf-8').decode('utf-8')

    def _store(self, items):  # 保存记录 id, title, original_url
        bulk_items = []
        for item in items:
            if '' in item:
                LOGGER.warning('miss attribute, {}'.format(item))
                continue
            bulk_items.append({
                'article_id': item[0],
                'title': item[1],
                'origin_url': item[2],
            })
        if self.debug:
            for item in bulk_items:
                print(item)
        else:
            with MYSQL_DB.atomic():
                SwordFishTable.insert_many(bulk_items).execute()


if __name__ == '__main__':
    # sf = SwordFish(debug=True)
    sf = SwordFish()
    sf.run()
    # print('dddd')
