import pymysql
from flask import g
import os

def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(
            host=os.environ.get('MYSQL_HOST', 'db'),
            user=os.environ.get('MYSQL_USER', 'root'),
            password=os.environ.get('MYSQL_PASSWORD', 'netgamepw'),
            db=os.environ.get('MYSQL_DATABASE', 'netgame'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()