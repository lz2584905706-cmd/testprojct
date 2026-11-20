import pymysql
from config.config import get_db_config

class DbClient:
    def __init__(self):
        self.cfg = get_db_config()

    def query_one(self, sql, args=None):
        conn = pymysql.connect(**self.cfg)
        try:
            cur = conn.cursor(pymysql.cursors.DictCursor)
            cur.execute(sql, args)
            return cur.fetchone()
        finally:
            conn.close()

    def query_all(self, sql, args=None):
        conn = pymysql.connect(**self.cfg)
        try:
            cur = conn.cursor(pymysql.cursors.DictCursor)
            cur.execute(sql, args)
            return cur.fetchall()
        finally:
            conn.close()

    def execute(self, sql, args=None):
        conn = pymysql.connect(**self.cfg)
        try:
            cur = conn.cursor()
            cur.execute(sql, args)
            conn.commit()
            return cur.rowcount
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
