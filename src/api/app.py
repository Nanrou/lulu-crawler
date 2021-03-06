from datetime import datetime
import random

from redis import Redis

from apistar import Include, Route, Response, http, Component, annotate
from apistar.frameworks.wsgi import WSGIApp as App
from apistar.handlers import docs_urls, static_urls
from apistar.interfaces import SessionStore
from peewee import DoesNotExist
from werkzeug.http import dump_cookie

import sys
import os

PROJECT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_DIR)

from db.orm import UserTable, CompanyTable, CategoryTable, ArticleTable, SwordFishTable
from lulu.core_logic import test_crawl

REDIS_DB = Redis(host='redis')


################
# TODO 使用auth验证
#
################

# 仿写内置的store
class RedisSessionStore(SessionStore):
    cookie_name = 'session_id'

    def new(self) -> http.Session:
        session_id = self._generate_key()
        return http.Session(session_id=session_id)

    def load(self, session_id: str) -> http.Session:
        if REDIS_DB.exists(session_id):
            return http.Session(session_id=session_id, data=REDIS_DB.hgetall(session_id))
        else:
            return self.new()

    def save(self, session: http.Session):
        headers = {}
        if session.is_new:
            cookie = dump_cookie(self.cookie_name, session.session_id, max_age=3600)
            headers['set-cookie'] = cookie
        if session.is_new or session.is_modified:
            if session.data:
                REDIS_DB.hmset(session.session_id, session.data)
                REDIS_DB.expire(session.session_id, 3600)
        return headers

    @staticmethod
    def _generate_key() -> str:
        length = 30
        allowed_chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        urandom = random.SystemRandom()
        return ''.join(urandom.choice(allowed_chars) for _ in range(length))


# 仿写的session，因为不知道为什么模块的前端没有自动将bytes转换成unicode
class MySession(http.Session):
    def __getitem__(self, key: str):
        try:
            return self.data[key]
        except KeyError:
            return self.data[bytes(key)]

    def __contains__(self, key: str):
        return key in self.data or bytes(key) in self.data


# 权限验证
class IsLogIn:
    @staticmethod
    def has_permission(session: http.Session):
        if ('user' in session or b'user' in session) and REDIS_DB.exists(session.session_id):
            return True
        else:
            return False


def login(data: http.RequestData, session: http.Session):
    try:
        username, password = data.get('username'), data.get('password')
        user = UserTable.get(UserTable.username == username)
        if user.verify_password(password):
            session['user'] = username
            return {'status': 'success'}
        else:
            return {'status': 'fail'}
    except DoesNotExist:
        return {'status': 'fail'}


def logout(session: http.Session):
    if 'user' in session:
        del session['user']
    if b'user' in session:
        del session[b'user']
    if REDIS_DB.exists(session.session_id):
        REDIS_DB.delete(session.session_id)
    return {'status': 'success'}


# TODO: delete
def console(request: http.Request, session: http.Session):
    if session.get('user'):
        return {
            'say': 'hi'
        }
    else:
        return Response(status=302, headers={'location': '/login'})


def check_log_in(session: http.Session):
    if ('user' in session or b'user' in session) and REDIS_DB.exists(session.session_id):
        return {'status': 'success'}
    else:
        return {'status': 'fail'}


@annotate(permissions=[IsLogIn()])
def get_all_company():
    res = []
    for company in CompanyTable.select(CompanyTable.name):
        res.append({'name': company.name})
    return res


@annotate(permissions=[IsLogIn()])
def get_company(company):
    try:
        _company = CompanyTable.get(CompanyTable.name == company)
        categories = CategoryTable.select().where(CategoryTable.company_name == _company.name)
        cate_list = []
        for category in categories:
            cate_list.append({
                'name': category.name,
                'url': category.url
            })
        res = {
            'company': _company.name,
            'domain': _company.domain,
            'category': cate_list,
            'condition': categories[0].condition,
            'is_direct': categories[0].is_direct,
            'article_url_rule': categories[0].article_url_rule,
            'article_middle_url_rule': categories[0].article_middle_url_rule,
            'article_query_url': categories[0].article_query_url,
            'article_json_rule': categories[0].article_json_rule,
            'article_title_rule': categories[0].article_title_rule,
            'article_author_rule': categories[0].article_author_rule,
            'article_publish_time_rule': categories[0].article_publish_time_rule,
            'article_content_rule': categories[0].article_content_rule,
        }
        return {'status': 'success', 'form': res}
    except DoesNotExist:
        return {'status': 'fail'}


@annotate(permissions=[IsLogIn()])
def test_form(data: http.RequestData):
    data['url'] = data.get('category')[random.randrange(len(data.get('category')))]['url']  # 随意取一个栏目去爬取
    try:
        return {'status': 'success', 'res': test_crawl(data)}
    except IndexError:
        return {'status': 'fail'}


# 暴力实现，全删了再新增进去
@annotate(permissions=[IsLogIn()])
def submit_edit(data: http.RequestData):
    try:
        _company = data.get('company')
        CategoryTable.delete().where(CategoryTable.company_name == _company).execute()
        bulk_cate = []
        for cate in data.get('category'):
            bulk_cate.append({
                'name': cate['name'],
                'url': cate['url'],
                'condition': cate['condition'],
                'is_direct': cate['is_direct'],
                'article_url_rule': cate['article_url_rule'],
                'article_middle_url_rule': cate['article_middle_url_rule'],
                'article_query_url': cate['article_query_url'],
                'article_title_rule': cate['article_title_rule'],
                'article_author_rule': cate['article_author_rule'],
                'article_publish_time_rule': cate['article_publish_time_rule'],
                'article_content_rule': cate['article_content_rule'],
                'company_name': _company,
            })
        CategoryTable.insert_many(bulk_cate)
        return {'status': 'success'}
    except KeyError:
        return {'status': 'fail'}


@annotate(permissions=[IsLogIn()])
def submit_append(data: http.RequestData):
    try:
        CompanyTable.get(CompanyTable.domain == data['domain'])
        return {'status': 'duplication'}
    except DoesNotExist:
        CompanyTable.create(name=data['domain'], domain=data['domain'])  # 新建公司
    try:
        _company = data.get('company')
        bulk_cate = []
        for cate in data.get('category'):
            bulk_cate.append({
                'name': cate['name'],
                'url': cate['url'],
                'condition': cate['condition'],
                'is_direct': cate['is_direct'],
                'article_url_rule': cate['article_url_rule'],
                'article_middle_url_rule': cate['article_middle_url_rule'],
                'article_query_url': cate['article_query_url'],
                'article_title_rule': cate['article_title_rule'],
                'article_author_rule': cate['article_author_rule'],
                'article_publish_time_rule': cate['article_publish_time_rule'],
                'article_content_rule': cate['article_content_rule'],
                'company_name': _company,
            })
        CategoryTable.insert_many(bulk_cate)
        return {'status': 'success'}
    except KeyError:
        return {'status': 'fail'}


def get_data_of_day(table, time_attribute, limit, today, date):
    if date:
        year, month, day = date.split('-')
    elif today:
        now_ = datetime.now()
        year, month, day = now_.year, now_.month, now_.day
    else:
        return {'status': 'error time args'}

    try:
        d1 = datetime(year=year, month=month, day=day)
        d2 = datetime(year=year, month=month, day=day, hour=23, minute=59, second=59)
        return table.select().where(getattr(table, time_attribute).between(d1, d2)).limit(limit)
    except TypeError:
        return {'status': 'error time args'}


# @annotate(permissions=[IsLogIn()])
def get_article(company: str, limit: int=50, first_time: bool=False, today: bool=False):
    try:  # TODO 倒序出去
        if limit is None:
            limit = 50
        if today:
            articles = get_data_of_day(ArticleTable, 'collected_time', limit, True, None)
        elif first_time:
            articles = ArticleTable.select()
        else:
            articles = ArticleTable.select().where(ArticleTable.company_name == company).limit(int(limit))
        res = []
        for article in articles:
            res.append({
                'url': article.url,
                'title': article.title,
                'author': article.author,
                'publish_time': article.publish_time.strftime('%Y/%m/%d %H:%M:%S'),
                'collected_time': article.collected_time.strftime('%Y/%m/%d %H:%M:%S'),
                'content': article.content,
                'company_name': article.company_name,
                'category_name': article.category_name,
            })
        return res

    except ValueError:
        return {'status': 'limit 参数错误'}

    except DoesNotExist:
        return {'status': 'error'}


# @annotate(permissions=[IsLogIn()])
def get_swordfish(limit: int=None, today: bool=True, date: str=None, first_time: bool=False):  # 要求date的格式为 yyyy-mm-dd
    if first_time:
        res = []
        for item in SwordFishTable.select():
            res.append({
                'article_id': item.article_id,
                'title': item.title,
                'origin_url': item.origin_url,
                'collected_time': item.collected_time.strftime('%Y/%m/%d %H:%M:%S'),
            })
        return res

    if today is None:
        today = True
    res = []
    for item in get_data_of_day(SwordFishTable, 'collected_time', limit, today, date):
        res.append({
            'article_id': item.article_id,
            'title': item.title,
            'origin_url': item.origin_url,
            'collected_time': item.collected_time.strftime('%Y/%m/%d %H:%M:%S'),
        })
    return res


# post到login，然后就可以拿数据了

routes = [
    Route('/api/checkLogIn', 'GET', check_log_in),
    Route('/api/login', 'POST', login),
    Route('/api/logout', 'GET', logout),
    Route('/api/get_all_company', 'GET', get_all_company),
    Route('/api/get_company', 'GET', get_company),
    Route('/api/test', 'POST', test_form),
    Route('/api/submit', 'POST', submit_edit),
    Route('/api/append', 'POST', submit_append),
    Route('/api/get_article', 'GET', get_article),
    Route('/api/get_swordfish', 'GET', get_swordfish),
    Include('/docs', docs_urls),
    Include('/statics', static_urls)
]

app = App(
    routes=routes,
    components=[Component(SessionStore, init=RedisSessionStore)],
)

if __name__ == '__main__':
    app.main()
