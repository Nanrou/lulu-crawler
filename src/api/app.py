import random

from redis import Redis

from apistar import Include, Route, Response, http, Component
from apistar.frameworks.wsgi import WSGIApp as App
from apistar.handlers import docs_urls, static_urls
from apistar.interfaces import SessionStore
from peewee import DoesNotExist
from werkzeug.http import dump_cookie

import sys
import os

PROJECT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_DIR)

from db.orm import UserTable

REDIS_DB = Redis()


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


def welcome(name=None):
    if name is None:
        return {'message': 'Welcome to API Star!'}
    return {'message': 'Welcome to API Star, %s!' % name}


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
    if 'username' in session:
        del session['username']
    return Response(status=302, headers={'location': '/login'})


def console(request: http.Request, session: http.Session):
    if session.get('user'):
        return {
            'say': 'hi'
        }
    else:
        return Response(status=302, headers={'location': '/login'})


def check_log_in(session: http.Session):
    if REDIS_DB.exists(session.session_id):
        return {'status': 'success'}
    else:
        return {'status': 'fail'}


routes = [
    Route('/', 'GET', welcome),
    Route('/api/checkLogIn', 'GET', check_log_in),
    Route('/api/login', 'POST', login),
    Route('/api/console', 'POST', console),
    Include('/docs', docs_urls),
    Include('/statics', static_urls)
]

app = App(
    routes=routes,
    components=[Component(SessionStore, init=RedisSessionStore)],
)

if __name__ == '__main__':
    app.main()
