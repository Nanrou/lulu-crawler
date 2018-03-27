from datetime import datetime

from html2text import HTML2Text

from lulu.alpha import Crawler, StaticItem, AjaxItem
from lulu.beta import Crawler
from db.orm import CategoryTable, ArticleTable, MYSQL_DB

TextMaker = HTML2Text()
TextMaker.ignore_links = True
TextMaker.ignore_images = True
TextMaker.ignore_tables = True
TextMaker.single_line_break = True


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
    for k, v in cc.first_crawl().items():
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


if __name__ == '__main__':
    first_crawl()
