from datetime import datetime
from peewee import MySQLDatabase, Model, CharField, SmallIntegerField, IntegerField, BooleanField, TimeField, TextField, ForeignKeyField

mysql_db = MySQLDatabase('shuiwujia', user='root', password='nanrou',
                         host='127.0.0.1', port=3306)


class BaseModel(Model):
    class Meta:
        database = mysql_db


class CompanyTable(BaseModel):
    gid = CharField(max_length=32, null=True, unique=True)
    domain = CharField(max_length=255, null=False, unique=True, index=True)
    name = CharField(max_length=32, null=False, unique=False)
    status = SmallIntegerField(default=0)
    create_time = TimeField(default=datetime.now())
    is_deleted = BooleanField(default=False)
    remark = CharField()


class CategoryTable(BaseModel):
    gid = CharField(max_length=32, null=True, unique=True)
    category_name = CharField(max_length=32, null=False)
    category_url = CharField(max_length=255, null=False, unique=True, index=True)

    company_name = ForeignKeyField(CompanyTable, on_delete=True, related_name='name', backref='category')

    is_deleted = BooleanField(default=False)
    remark = CharField()


class ArticleTable(BaseModel):
    gid = CharField(max_length=64, null=True, unique=True)

    article_url = CharField(max_length=255, unique=True)
    article_title = CharField(max_length=128, null=True, unique=True)
    article_author = CharField(max_length=32, null=True, unique=True)
    article_publish_time = TimeField(default=datetime.now())
    article_collected_time = TimeField(default=datetime.now())
    article_content = TextField(null=True)

    company_name = ForeignKeyField(CompanyTable, on_delete=True, related_name='name', backref='article')
    category_name = ForeignKeyField(CategoryTable, on_delete=True, related_name='category_name', backref='article')

    is_deleted = BooleanField(default=False)
    remark = CharField()
