import os
import pymysql
from flask import g

def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD', '123456'),
            db=os.environ.get('DB_NAME', 'netgame'),
            port=int(os.environ.get('DB_PORT', 3306)),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()