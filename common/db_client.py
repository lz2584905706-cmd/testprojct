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

    def delete(self, table, **conditions):
        """精准删除满足条件的记录，防止污染数据库"""
        if not conditions:
            raise ValueError("为了数据安全，delete 操作必须指定过滤条件！")
        where_clause = " AND ".join([f"{k} = %s" for k in conditions.keys()])
        sql = f"DELETE FROM {table} WHERE {where_clause}"
        return self.execute(sql, tuple(conditions.values()))

    def exists(self, table, **conditions):
        """检查记录是否真实存在于数据库中（用于双重断言）"""
        if not conditions:
            raise ValueError("exists 必须指定查询条件！")
        where_clause = " AND ".join([f"{k} = %s" for k in conditions.keys()])
        sql = f"SELECT 1 FROM {table} WHERE {where_clause} LIMIT 1"
        row = self.query_one(sql, tuple(conditions.values()))
        return row is not None
