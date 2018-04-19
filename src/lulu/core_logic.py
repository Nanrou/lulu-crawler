from datetime import datetime

from html2text import HTML2Text

from lulu.alpha import Crawler, StaticItem, AjaxItem
from lulu.beta import Crawler
from db.orm import CategoryTable, ArticleTable, MYSQL_DB
from bloom_filter import MyBloomFilter

TextMaker = HTML2Text()
TextMaker.ignore_links = True
TextMaker.ignore_images = True
TextMaker.ignore_tables = True
TextMaker.single_line_break = True

BloomFilter = MyBloomFilter()


def first_crawl():
    items = []
    url_company_category_mapper = dict()
    for category in CategoryTable.select():
        item_class = AjaxItem if category.condition else StaticItem
        items.append(
            item_class(
                url=category.url,
                detail={
                    'article_url_rule': category.article_url_rule,
                    'article_middle_url_rule': category.article_middle_url_rule,
                    'article_query_url': category.article_query_url,
                    'article_json_rule': category.article_json_rule,
                    'article_title_rule': category.article_title_rule,
                    'article_author_rule': category.article_author_rule,
                    'article_publish_time_rule': category.article_publish_time_rule,
                    'article_content_rule': category.article_content_rule,
                },
                is_direct=category.is_direct,
                # is_json=category.is_json,
            )
        )
        url_company_category_mapper[category.url] = [category.company_name, category.name]

    cc = Crawler(items)
    for k, v in cc.crawl().items():
        if not v:
            continue
        insert_list = []
        company, category = url_company_category_mapper[k]
        for single_url in v:
            single_part = dict(
                url=single_url.url,
                company_name=company,
                category_name=category,

                title=TextMaker.handle(single_url.detail['article_title_rule'])
                if single_url.detail['article_title_rule'] else None,
                author=TextMaker.handle(single_url.detail['article_author_rule'])
                if single_url.detail['article_author_rule'] else None,
                publish_time=TextMaker.handle(single_url.detail['article_publish_time_rule'])
                if single_url.detail['article_publish_time_rule'] else datetime.now(),
                content=TextMaker.handle(single_url.detail['article_content_rule'])
                if single_url.detail['article_content_rule'] else None,
            )
            insert_list.append(single_part)
        with MYSQL_DB.atomic():
            ArticleTable.insert_many(insert_list).execute()


def init_redis():  # 根据第一次抓取去初始化布隆过滤器
    articles = ArticleTable.select(ArticleTable.url, ArticleTable.title)
    for article in articles:
        BloomFilter.insert(''.join([article.url, article.title]))


def test_crawl(item):  # 接受B端过来的数据
    item_class = AjaxItem if item['condition'] else StaticItem
    sample = item_class(
        url=item['url'],
        detail={
            'article_url_rule': item['article_url_rule'],
            'article_middle_url_rule': item['article_middle_url_rule'],
            'article_query_url': item['article_query_url'],
            'article_json_rule': item['article_json_rule'],
            'article_title_rule': item['article_title_rule'],
            'article_author_rule': item['article_author_rule'],
            'article_publish_time_rule': item['article_publish_time_rule'],
            'article_content_rule': item['article_content_rule'],
        },
        is_direct=item['is_direct'],
    )
    cc = Crawler(sample, debug=True)
    return cc.test_crawl()[0]


def daily_crawl():
    first_crawl()


if __name__ == '__main__':
    # first_crawl()
    # init_redis()
    daily_crawl()
    # import json
    # with open('../db/test.json') as rf:
    #     jj = json.load(rf)
    #     ii = jj['category'][0]
    #     test_crawl(ii)
