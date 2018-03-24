from datetime import datetime
from peewee import MySQLDatabase, SqliteDatabase, Model, CharField, SmallIntegerField, BooleanField, DateTimeField, \
    TextField, ForeignKeyField

MYSQL_DB = MySQLDatabase('shuiwujia', user='root', password='nanrou',
                         host='127.0.0.1', port=3306)


class BaseModel(Model):
    class Meta:
        database = MYSQL_DB


# 这三个表是储存数据的


class CompanyTable(BaseModel):
    # gid = CharField(max_length=32, null=True, unique=True)
    domain = CharField(max_length=255, unique=True, index=True)
    name = CharField(max_length=128, unique=False)
    status = SmallIntegerField(default=0)
    create_time = DateTimeField(default=datetime.now())

    # is_deleted = BooleanField(default=False)
    # remark = CharField(null=True)
    class Meta:
        table_name = 'CompanyTable'


class CategoryTable(BaseModel):
    # gid = CharField(max_length=32, null=True, unique=True)
    name = CharField(max_length=32, null=False)
    url = CharField(max_length=255, null=False, unique=True)

    condition = SmallIntegerField(default=0, null=False)
    is_direct = BooleanField(default=False)  # 是否可以直接在分类页拿到内容
    is_json = BooleanField(default=False)  # 内容是否为json格式

    # 内容的解析规则
    article_url_rule = CharField(max_length=255, null=True)
    article_middle_url_rule = CharField(max_length=255, null=True)
    article_query_url = CharField(max_length=255, null=True)  # 构造查询文章的url

    article_title_rule = CharField(max_length=255, null=False)
    article_author_rule = CharField(max_length=255, null=False)
    article_publish_time_rule = CharField(max_length=255, null=False)
    article_content_rule = CharField(max_length=255, null=False)

    # company_name = ForeignKeyField(CompanyTable, backref='category')
    company_name = CharField(max_length=255, null=False)

    # is_deleted = BooleanField(default=False)
    # remark = CharField(null=True)

    class Meta:
        table_name = 'CategoryTable'


class ArticleTable(BaseModel):
    # gid = CharField(max_length=64, null=True, unique=True)
    url = CharField(max_length=255, unique=True)
    title = CharField(max_length=128, null=True, unique=True)
    author = CharField(max_length=32, null=True, unique=True)
    publish_time = DateTimeField(default=datetime.now())
    collected_time = DateTimeField(default=datetime.now())
    content = TextField(null=True)

    company_name = CharField(max_length=255, null=False)
    category_name = CharField(max_length=255, null=False)
    # company_name = ForeignKeyField(CompanyTable, backref='articles')
    # category_name = ForeignKeyField(CategoryTable, backref='articles')

    # is_deleted = BooleanField(default=False)
    # remark = CharField(null=True)
    class Meta:
        table_name = 'ArticleTable'


ALL_TABLES = [CompanyTable, CategoryTable, ArticleTable]
