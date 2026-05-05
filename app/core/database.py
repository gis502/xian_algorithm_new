"""
数据库连接管理 - 使用SQLAlchemy 2.0
"""
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import QueuePool
from typing import List, Dict, Any
from contextlib import contextmanager

from app.config.settings import get_settings
from app.utils.logger import setup_logging

# 初始化日志
logger = setup_logging()

# 关闭SQLAlchemy引擎日志，只保留关键信息
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)

# 获取配置
settings = get_settings()

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=False,  # 关闭SQL语句打印
    connect_args={
        "options": "-c client_encoding=UTF8"
    }
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = DeclarativeBase()


class DatabaseManager:
    """数据库管理器 - 提供通用的CRUD操作"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    @contextmanager
    def get_session(self) -> Session:
        """获取数据库会话的上下文管理器"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            session.close()
    
    def init_db(self):
        """初始化数据库，创建所有表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("数据库表创建成功")
        except Exception as e:
            logger.error(f"数据库表创建失败: {e}")
            raise
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.info("数据库连接测试成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False
    
    def execute_raw_sql(self, sql: str, params: dict = None) -> List[Dict[str, Any]]:
        """执行原生SQL查询
        
        Args:
            sql: SQL语句
            params: 参数字典
            
        Returns:
            查询结果列表
        """
        with self.get_session() as session:
            result = session.execute(text(sql), params or {})
            if result.returns_rows:
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]
            return []
    
    def insert(self, table_name: str, data: Dict[str, Any]) -> int:
        """插入单条记录
        
        Args:
            table_name: 表名
            data: 要插入的数据字典
            
        Returns:
            插入的行数
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join([f":{key}" for key in data.keys()])
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        with self.get_session() as session:
            result = session.execute(text(sql), data)
            return result.rowcount
    
    def insert_many(self, table_name: str, data_list: List[Dict[str, Any]]) -> int:
        """批量插入记录
        
        Args:
            table_name: 表名
            data_list: 数据字典列表
            
        Returns:
            插入的行数
        """
        if not data_list:
            return 0
        
        columns = ", ".join(data_list[0].keys())
        placeholders = ", ".join([f":{key}" for key in data_list[0].keys()])
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        with self.get_session() as session:
            result = session.execute(text(sql), data_list)
            return result.rowcount
    
    def select(
        self, 
        table_name: str, 
        conditions: Dict[str, Any] = None, 
        columns: List[str] = None, 
        limit: int = None, 
        offset: int = None,
        order_by: str = None
    ) -> List[Dict[str, Any]]:
        """查询记录
        
        Args:
            table_name: 表名
            conditions: 查询条件字典
            columns: 要查询的列列表，None表示查询所有列
            limit: 限制返回行数
            offset: 偏移量
            order_by: 排序字段
            
        Returns:
            查询结果列表
        """
        col_str = ", ".join(columns) if columns else "*"
        sql = f"SELECT {col_str} FROM {table_name}"
        
        params = {}
        if conditions:
            where_clauses = []
            for key, value in conditions.items():
                where_clauses.append(f"{key} = :{key}")
                params[key] = value
            sql += " WHERE " + " AND ".join(where_clauses)
        
        if order_by:
            sql += f" ORDER BY {order_by}"
        
        if limit:
            sql += f" LIMIT :limit"
            params["limit"] = limit
        
        if offset:
            sql += f" OFFSET :offset"
            params["offset"] = offset
        
        return self.execute_raw_sql(sql, params)
    
    def update(self, table_name: str, data: Dict[str, Any], 
               conditions: Dict[str, Any]) -> int:
        """更新记录
        
        Args:
            table_name: 表名
            data: 要更新的数据字典
            conditions: 更新条件字典
            
        Returns:
            更新的行数
        """
        set_clauses = [f"{key} = :{key}" for key in data.keys()]
        where_clauses = [f"{key} = :cond_{key}" for key in conditions.keys()]
        
        sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"
        
        # 合并参数，避免键名冲突
        params = {**data, **{f"cond_{key}": value for key, value in conditions.items()}}
        
        with self.get_session() as session:
            result = session.execute(text(sql), params)
            return result.rowcount
    
    def delete(self, table_name: str, conditions: Dict[str, Any]) -> int:
        """删除记录
        
        Args:
            table_name: 表名
            conditions: 删除条件字典
            
        Returns:
            删除的行数
        """
        where_clauses = [f"{key} = :{key}" for key in conditions.keys()]
        sql = f"DELETE FROM {table_name} WHERE {' AND '.join(where_clauses)}"
        
        with self.get_session() as session:
            result = session.execute(text(sql), conditions)
            return result.rowcount
    
    def count(self, table_name: str, conditions: Dict[str, Any] = None) -> int:
        """统计记录数
        
        Args:
            table_name: 表名
            conditions: 统计条件字典
            
        Returns:
            记录数
        """
        sql = f"SELECT COUNT(*) as count FROM {table_name}"
        params = {}
        
        if conditions:
            where_clauses = []
            for key, value in conditions.items():
                where_clauses.append(f"{key} = :{key}")
                params[key] = value
            sql += " WHERE " + " AND ".join(where_clauses)
        
        result = self.execute_raw_sql(sql, params)
        return result[0]["count"] if result else 0


# 创建全局数据库管理器实例
db_manager = DatabaseManager()
