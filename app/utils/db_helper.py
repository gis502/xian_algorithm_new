"""
PostgreSQL 数据库工具类
提供增删改查方法，内置连接池
"""
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from config import settings


class PostgresSQLHelper:
    """PostgreSQL 数据库帮助类（连接池版）"""

    def __init__(self):
        """初始化数据库连接池"""
        self.db_config = {
            'host': settings.DB_HOST,
            'port': settings.DB_PORT,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'database': settings.DB_NAME,
        }
        self._pool = None

    def _ensure_pool(self):
        """延迟初始化连接池"""
        if self._pool is None:
            self._pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=20,
                **self.db_config
            )

    @contextmanager
    def get_connection(self):
        """
        从连接池获取连接（复用TCP连接，省去握手开销）
        """
        self._ensure_pool()
        conn = self._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self._pool.putconn(conn)

    @contextmanager
    def get_cursor(self, dict_cursor=False):
        """
        获取数据库游标的上下文管理器

        Args:
            dict_cursor: 是否使用字典游标（返回字典格式结果）
        """
        with self.get_connection() as conn:
            cursor = None
            try:
                if dict_cursor:
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                else:
                    cursor = conn.cursor()
                yield cursor
            finally:
                if cursor:
                    cursor.close()
    
    def execute_query(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        执行查询语句，返回字典列表
        
        Args:
            sql: SQL 查询语句
            params: 参数元组
            
        Returns:
            查询结果列表，每个元素为字典
        """
        with self.get_cursor(dict_cursor=True) as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()
            # 将 RealDictRow 转换为普通字典
            return [dict(row) for row in results]
    
    def execute_query_one(self, sql: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """
        执行查询语句，返回单条记录
        
        Args:
            sql: SQL 查询语句
            params: 参数元组
            
        Returns:
            单条记录的字典，如果没有结果则返回 None
        """
        with self.get_cursor(dict_cursor=True) as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def execute_update(self, sql: str, params: tuple = None) -> int:
        """
        执行更新/插入/删除语句
        
        Args:
            sql: SQL 语句
            params: 参数元组
            
        Returns:
            影响的行数
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount
    
    def execute_insert(self, sql: str, params: tuple = None, returning: str = None) -> Any:
        """
        执行插入语句并返回新生成的 ID 或指定字段
        
        Args:
            sql: INSERT SQL 语句
            params: 参数元组
            returning: RETURNING 子句指定的字段名，默认为 'id'
            
        Returns:
            新生成的 ID 或指定字段的值
        """
        if returning and not sql.upper().endswith(f'RETURNING {returning}'.upper()):
            sql = f"{sql} RETURNING {returning}"
        
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchone()
            return result[0] if result else None
    
    def execute_many(self, sql: str, params_list: List[tuple]) -> int:
        """
        批量执行 SQL 语句
        
        Args:
            sql: SQL 语句
            params_list: 参数列表，每个元素为参数元组
            
        Returns:
            影响的总行数
        """
        with self.get_cursor() as cursor:
            cursor.executemany(sql, params_list)
            return cursor.rowcount


# 创建全局实例
db_helper = PostgresSQLHelper()

