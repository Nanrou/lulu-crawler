__all__ = ['MyLogger']

import logging
from logging import StreamHandler, Logger, Formatter
from logging.handlers import RotatingFileHandler


class MyLogger(Logger):
    def __init__(self, name='logger'):
        super().__init__(name)
        self.setLevel(logging.DEBUG)

        data_fmt = '%Y-%m-%d %H:%M:%S'
        formatter = Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s', data_fmt)

        sh = StreamHandler()

        fh1 = RotatingFileHandler('info.log', maxBytes=1024 * 5, backupCount=5, encoding='utf-8')
        fh1.setLevel(logging.INFO)

        fh2 = RotatingFileHandler('warning.log', maxBytes=1024 * 5, backupCount=5, encoding='utf-8')
        fh2.setLevel(logging.WARNING)

        for h in [sh, fh1, fh2]:
            h.setFormatter(formatter)
            self.addHandler(h)
