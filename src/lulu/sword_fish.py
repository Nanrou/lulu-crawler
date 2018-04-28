from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import redis
import requests

from utils.bloom_filter import MyBloomFilter

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
        browser.get('https://www.jianyu360.com/jylab/supsearch/index.html')

        # todo sign in
        # todo 存cookies

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


if __name__ == '__main__':
    sf = SwordFish()
    sf._headless_request()
