from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import redis
import requests

from utils import bloom_filter

QR_CODE_XPATH = "//img[@id='layerImg-login']"
DATE_XPATH = "//div[@class='fl timer']/ul/li[2]"
CATEGORY_XPATH = "//div[@class='searchControl']//div[@class='info-content']//font[@class='parent-node'][2]"
INPUT_XPATH = "//input[@id='searchinput']"
DATA_ID_XPATH = "//div[@class='lucene'][1]/ul/li/div/div//div[@class='left-title']/a"
ORIGINAL_XPATH = "//div[@class='original-text']/a/@href"


class SwordFish:
    def __init__(self):
        pass

    def _headless_request(self):
        op = webdriver.FirefoxOptions()
        # op.add_argument('-headless')
        browser = webdriver.Firefox(options=op)
        browser.get('https://www.jianyu360.com/jylab/supsearch/index.html')

        # todo sign in

        browser.find_element_by_xpath(DATE_XPATH).click()  # 选择7天以内
        browser.find_element_by_xpath(CATEGORY_XPATH).click()  # 只选招标

        browser.find_element_by_xpath(INPUT_XPATH).send_keys('水务', Keys.ENTER)

        try:
            WebDriverWait(browser, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[@class='lucene'][1]/ul/li"))
            )

            articles = []
            for ele in browser.find_elements_by_xpath(DATA_ID_XPATH):
                articles.append(ele.get_attribute('dataid'))

            # todo 翻页
            # todo 存cookies
        except NoSuchElementException:
            pass
        else:
            self._scrap_core()
        finally:
            browser.close()

    def _scrap_core(self):
        pass


if __name__ == '__main__':
    pass
