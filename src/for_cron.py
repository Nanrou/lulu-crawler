from datetime import datetime, timedelta, timezone
import sys
import os

FILE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_china_time():
    utc_time = datetime.utcnow()
    # return '%Y-%m-%d %H:%M:%S'.format(utc_time.astimezone(timezone(timedelta(hours=8))))
    return utc_time.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')


def append_log(tt):
    with open(os.path.join(FILE_DIR, '{}.log'.format(tt)), 'a') as af:
        af.write('{}: {} start'.format(get_china_time(), tt))


if __name__ == '__main__':
    t = sys.argv[1]
    append_log(t)
