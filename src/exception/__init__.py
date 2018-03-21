from requests import RequestException


class OutTryException(RequestException):
    """超过最大尝试次数的异常"""
