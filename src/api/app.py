from apistar import Include, Route, Response, http
from apistar.frameworks.wsgi import WSGIApp as App
from apistar.handlers import docs_urls, static_urls
from apistar.interfaces import SessionStore
from apistar.authentication import Authenticated

from db.orm import UserTable

def welcome(name=None):
    if name is None:
        return {'message': 'Welcome to API Star!'}
    return {'message': 'Welcome to API Star, %s!' % name}

def login(username, password, session):
    try:




routes = [
    Route('/', 'GET', welcome),
    Include('/docs', docs_urls),
    Include('/static', static_urls)
]

app = App(routes=routes)


if __name__ == '__main__':
    app.main()
