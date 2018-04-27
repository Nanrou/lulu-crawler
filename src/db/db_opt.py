import json
from db.orm import MYSQL_DB, ALL_TABLES, CompanyTable, CategoryTable, UserTable


def create_tables():
    for table in ALL_TABLES[::-1]:
        if MYSQL_DB.table_exists(table):
            MYSQL_DB.drop_tables(table)
    MYSQL_DB.create_tables(ALL_TABLES)
    UserTable.create(username='root', password='123')


def input_json2db(file):
    with open(file) as rf:
        json_data = json.load(rf)
    for item in json_data:
        CompanyTable.create(domain=item['domain'], name=item['company'])
        bulk_cate = []
        for cate in item['category']:
            try:
                bulk_cate.append({
                    'name': cate['name'],
                    'url': cate['url'],
                    'condition': cate['condition'],
                    'is_direct': cate['is_direct'],
                    'article_url_rule': cate['article_url_rule'],
                    'article_middle_url_rule': cate['article_middle_url_rule'],
                    'article_query_url': cate['article_query_url'],
                    'article_json_rule': cate['article_json_rule'],
                    'article_title_rule': cate['article_title_rule'],
                    'article_author_rule': cate['article_author_rule'],
                    'article_publish_time_rule': cate['article_publish_time_rule'],
                    'article_content_rule': cate['article_content_rule'],
                    # 'company_name': CompanyTable.get(CompanyTable.name == item['company'])
                    'company_name': item['company'],
                })
            except KeyError:
                print('{} {} error'.format(item['company'], cate['name']))
                raise RuntimeError
        with MYSQL_DB.atomic():  # 包在事务里
            CategoryTable.insert_many(bulk_cate).execute()


if __name__ == '__main__':
    create_tables()
    input_json2db('website2.json')
    # MYSQL_DB.create_tables([UserTable], safe=True)
    pass
