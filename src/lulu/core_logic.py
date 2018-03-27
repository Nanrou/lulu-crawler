import json

from lulu.alpha import Crawler, StaticItem, AjaxItem
from lulu.beta import Crawler
from db.orm import CategoryTable, ArticleTable


def main():
    items = []
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
                is_json=category.is_json,
            )
        )
    cc = Crawler(items)
    for k, v in cc.first_crawl().items():
        print(k, v)


if __name__ == '__main__':
    main()
