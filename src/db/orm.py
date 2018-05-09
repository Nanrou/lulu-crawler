from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash
from peewee import MySQLDatabase, Model, CharField, SmallIntegerField, BooleanField, DateTimeField, \
    TextField
from playhouse.pool import PooledMySQLDatabase

"""
TODO: 添加 最后编辑人
"""

MYSQL_DB = MySQLDatabase('shuiwujia', user='root', password='123456',
                         host='mysql', port=3306)

MYSQL_DB_POOL = PooledMySQLDatabase('shuiwujia', user='root', password='123456',
                                    host='mysql',
                                    max_connections=5,
                                    stale_timeout=60 * 5,
                                    timeout=3)


class BaseModel(Model):
    class Meta:
        database = MYSQL_DB_POOL


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
    # is_json = BooleanField(default=False)  # 内容是否为json格式
    # publish_time_in_outside = BooleanField(default=False)  # 发布时间是否只能在外部拿到

    # 内容的解析规则
    article_url_rule = CharField(max_length=255, null=True, default=None)
    article_middle_url_rule = CharField(max_length=255, null=True, default=None)
    article_query_url = CharField(max_length=255, null=True, default=None)  # 构造查询文章的url
    article_json_rule = CharField(max_length=255, null=True, default=None)  # 解析json的规则

    article_title_rule = CharField(max_length=255, null=False)
    article_author_rule = CharField(max_length=255, null=True)
    article_publish_time_rule = CharField(max_length=255, null=True)
    article_content_rule = CharField(max_length=255, null=False)

    # company_name = ForeignKeyField(CompanyTable, backref='category')
    company_name = CharField(max_length=255, null=False, index=True)

    # is_deleted = BooleanField(default=False)
    # remark = CharField(null=True)

    class Meta:
        table_name = 'CategoryTable'


class ArticleTable(BaseModel):
    # gid = CharField(max_length=64, null=True, unique=True)
    url = CharField(max_length=255)
    title = CharField(max_length=64, null=True)
    author = CharField(max_length=64, null=True)
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


class UserTable(BaseModel):
    username = CharField(max_length=16, unique=True)
    password_hash = CharField(max_length=255)

    @property
    def password(self):
        raise RuntimeError('You cant get password directly')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    class Meta:
        table_name = 'UserTable'


class SwordFishTable(BaseModel):
    article_id = CharField(max_length=128)
    title = CharField()
    origin_url = CharField(max_length=2048)
    collected_time = DateTimeField(default=datetime.now())

    class Meta:
        table_name = 'SwordFishTable'


ALL_TABLES = [CompanyTable, CategoryTable, ArticleTable, UserTable, SwordFishTable]

if __name__ == '__main__':
    MYSQL_DB_POOL.connect()
    MYSQL_DB.connect()
