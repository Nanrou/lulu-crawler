from concurrent.futures import ThreadPoolExecutor, as_completed
import smtplib
from email.header import Header
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

from lulu.beta import HEADER
from db.orm import SwordFishTable
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

QR_CODE_XPATH = "//img[@id='layerImg-login']"
DATE_XPATH = "//div[@class='fl timer']/ul/li[2]"
CATEGORY_XPATH = "//div[@class='searchControl']//div[@class='info-content']//font[@class='parent-node'][2]"
INPUT_XPATH = "//input[@id='searchinput']"
DATA_ID_XPATH = "//div[@class='lucene'][1]/ul/li/div/div//div[@class='left-title']/a"
ORIGINAL_XPATH = "//div[@class='original-text']/a/@href"


class SwordFish:
    def __init__(self, debug=False):
        self.debug = debug

    def _headless_request(self):
        op = webdriver.FirefoxOptions()
        # op.add_argument('-headless')
        browser = webdriver.Firefox(options=op)

        _cookie = self._load_local_cookie()  # 注意brower的cookie格式
        browser.add_cookie(_cookie)
        browser.get('https://www.jianyu360.com/jylab/supsearch/index.html')

        # todo sign in
        # todo 存cookies
        try:
            browser.find_element_by_xpath('//div[@id="login"]/img')
        except NoSuchElementException:
            qr_url = browser.find_element_by_xpath(QR_CODE_XPATH).get_attribute('src')
            self._send_email(qr_url)  # TODO WeChat robot
            try:
                WebDriverWait(browser, 60 * 10).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@id="login"]/img'))
                )  # 等待登陆
                self._save_cookie(browser.get_cookies())
            except NoSuchElementException:
                # TODO log
                browser.close()

        browser.find_element_by_xpath(DATE_XPATH).click()  # 选择7天以内
        browser.find_element_by_xpath(CATEGORY_XPATH).click()  # 只选招标

        browser.find_element_by_xpath(INPUT_XPATH).send_keys('水务', Keys.ENTER)  # TODO 多个关键字

        pagination_flag = True
        filter_articles = []

        # 搜索结果页操作
        try:
            while pagination_flag:
                WebDriverWait(browser, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@class='lucene'][1]/ul/li"))
                )  # 等待加载内容
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
                filter_articles.extend(_filter_articles)
        except NoSuchElementException:
            pass
        else:
            self._scrap_core()
        print(filter_articles)
        print(len(filter_articles))
        browser.close()

    def _scrap_core(self):
        pass

    def _load_local_cookie(self):
        pass

    @staticmethod
    def _send_email(qr_url):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header('登陆验证', 'utf-8')
        _response = requests.get(qr_url, headers=HEADER)
        msg_image = MIMEImage(_response.content)
        msg_image.add_header('Content-ID', '<image>')
        msg.attach(msg_image)

        content = MIMEText(EMAIL_HTML, 'html', 'utf-8')
        msg.attach(content)

        msg['From'] = 'SF_robot'
        msg['To'] = ','.join(RECEIVERS)

        try:
            smtp_obj = smtplib.SMTP()
            smtp_obj.connect(MAIL_HOST, 25)
            smtp_obj.login(EMAIL, PSW)
            smtp_obj.sendmail(
                EMAIL, RECEIVERS, msg.as_string()
            )
            smtp_obj.quit()
        except smtplib.SMTPException as e:
            print('error', e)

    def run(self):
        self._headless_request()


if __name__ == '__main__':
    sf = SwordFish(debug=True)
    sf.run()
