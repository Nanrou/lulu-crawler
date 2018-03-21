from datetime import datetime
from peewee import MySQLDatabase, Model, CharField, SmallIntegerField, IntegerField, BooleanField, TimeField, TextField, \
    ForeignKeyField

mysql_db = MySQLDatabase('shuiwujia', user='root', password='nanrou',
                         host='127.0.0.1', port=3306)


class BaseModel(Model):
    class Meta:
        database = mysql_db


# 这三个表是储存数据的

class CompanyTable(BaseModel):
    # gid = CharField(max_length=32, null=True, unique=True)
    domain = CharField(max_length=255, null=False, unique=True, index=True)
    name = CharField(max_length=32, null=False, unique=False)
    status = SmallIntegerField(default=0)
    create_time = TimeField(default=datetime.now())
    is_deleted = BooleanField(default=False)
    remark = CharField()


class CategoryTable(BaseModel):
    # gid = CharField(max_length=32, null=True, unique=True)
    name = CharField(max_length=32, null=False)
    url = CharField(max_length=255, null=False, unique=True, index=True)

    condition = SmallIntegerField(default=0, null=False)
    direct = BooleanField(default=False)  # 是否可以直接在分类页拿到内容
    is_json = BooleanField(default=False)  # 内容是否为json格式

    # 内容的解析规则
    article_url_rule = CharField(max_length=255, null=True)
    article_title_rule = CharField(max_length=255, null=False)
    article_author_rule = CharField(max_length=255, null=False)
    article_publish_time_rule = CharField(max_length=255, null=False)
    article_content_rule = CharField(max_length=255, null=False)

    company_name = ForeignKeyField(CompanyTable, on_delete=True, related_name='name', backref='category')

    is_deleted = BooleanField(default=False)
    remark = CharField()


class ArticleTable(BaseModel):
    # gid = CharField(max_length=64, null=True, unique=True)
    url = CharField(max_length=255, unique=True)
    title = CharField(max_length=128, null=True, unique=True)
    author = CharField(max_length=32, null=True, unique=True)
    publish_time = TimeField(default=datetime.now())
    collected_time = TimeField(default=datetime.now())
    content = TextField(null=True)

    company_name = ForeignKeyField(CompanyTable, on_delete=True, related_name='name', backref='article')
    category_name = ForeignKeyField(CategoryTable, on_delete=True, related_name='category_name', backref='article')

    is_deleted = BooleanField(default=False)
    remark = CharField()
