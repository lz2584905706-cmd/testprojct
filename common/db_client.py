import pymysql
from config.config import get_db_config

class DbClient:
    def __init__(self):
        self.cfg=get_db_config()

    def query_one(self,sql,args=None):
        conn=pymysql.connect(**self.cfg)
        cur=conn.cursor(pymysql.cursors.DictCursor)
        cur.execute(sql,args)
        row=cur.fetchone()
        conn.close()
        return row

    def query_all(self,sql,args=None):
        conn=pymysql.connect(**self.cfg)
        cur=conn.cursor(pymysql.cursors.DictCursor)
        cur.execute(sql,args)
        rows=cur.fetchall()
        conn.close()
        return rows

    def execute(self,sql,args=None):
        conn=pymysql.connect(**self.cfg)
        cur=conn.cursor()
        cur.execute(sql,args)
        conn.commit()
        affected=cur.rowcount
        conn.close()
        return affected