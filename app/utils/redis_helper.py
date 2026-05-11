"""
Redis 数据库工具类
提供常用的 Redis 操作方法
"""
import redis
from typing import Any, Optional, List, Dict, Union
from config import settings


class RedisHelper:
    """Redis 数据库帮助类"""
    
    def __init__(self):
        """初始化 Redis 连接配置"""
        self.redis_config = {
            'host': settings.REDIS_HOST,
            'port': settings.REDIS_PORT,
            'password': settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            'db': settings.REDIS_DB,
            'decode_responses': True,  # 自动解码响应为字符串
            'socket_connect_timeout': 5,  # 连接超时时间（秒）
            'socket_timeout': 5,  # 读写超时时间（秒）
        }
        self._client: Optional[redis.Redis] = None
    
    @property
    def client(self) -> redis.Redis:
        """获取 Redis 客户端实例（单例模式）"""
        if self._client is None:
            try:
                self._client = redis.Redis(**self.redis_config)
                # 测试连接
                self._client.ping()
            except redis.ConnectionError as e:
                raise ConnectionError(f"无法连接到 Redis 服务器: {e}")
        return self._client
    
    def close(self):
        """关闭 Redis 连接"""
        if self._client:
            self._client.close()
            self._client = None
    
    # ==================== String 操作 ====================
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        设置键值对
        
        Args:
            key: 键名
            value: 值
            ex: 过期时间（秒），None 表示不过期
            
        Returns:
            是否设置成功
        """
        return self.client.set(key, value, ex=ex)
    
    def get(self, key: str) -> Optional[str]:
        """
        获取键对应的值
        
        Args:
            key: 键名
            
        Returns:
            键对应的值，如果键不存在则返回 None
        """
        return self.client.get(key)
    
    def delete(self, *keys: str) -> int:
        """
        删除一个或多个键
        
        Args:
            keys: 要删除的键名列表
            
        Returns:
            成功删除的键数量
        """
        return self.client.delete(*keys)
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 键名
            
        Returns:
            键是否存在
        """
        return self.client.exists(key) > 0
    
    def expire(self, key: str, seconds: int) -> bool:
        """
        设置键的过期时间
        
        Args:
            key: 键名
            seconds: 过期时间（秒）
            
        Returns:
            是否设置成功
        """
        return self.client.expire(key, seconds)
    
    def ttl(self, key: str) -> int:
        """
        获取键的剩余生存时间
        
        Args:
            key: 键名
            
        Returns:
            剩余生存时间（秒），-1 表示永久有效，-2 表示键不存在
        """
        return self.client.ttl(key)
    
    def incr(self, key: str, amount: int = 1) -> int:
        """
        递增键的值
        
        Args:
            key: 键名
            amount: 增量
            
        Returns:
            递增后的值
        """
        return self.client.incr(key, amount)
    
    def decr(self, key: str, amount: int = 1) -> int:
        """
        递减键的值
        
        Args:
            key: 键名
            amount: 减量
            
        Returns:
            递减后的值
        """
        return self.client.decr(key, amount)
    
    # ==================== Hash 操作 ====================
    
    def hset(self, name: str, key: str, value: Any) -> int:
        """
        设置哈希表字段的值
        
        Args:
            name: 哈希表名
            key: 字段名
            value: 字段值
            
        Returns:
            1 表示新增字段，0 表示更新字段
        """
        return self.client.hset(name, key, value)
    
    def hget(self, name: str, key: str) -> Optional[str]:
        """
        获取哈希表字段的值
        
        Args:
            name: 哈希表名
            key: 字段名
            
        Returns:
            字段值，如果字段不存在则返回 None
        """
        return self.client.hget(name, key)
    
    def hgetall(self, name: str) -> Dict[str, str]:
        """
        获取哈希表所有字段和值
        
        Args:
            name: 哈希表名
            
        Returns:
            包含所有字段和值的字典
        """
        return self.client.hgetall(name)
    
    def hdel(self, name: str, *keys: str) -> int:
        """
        删除哈希表中的一个或多个字段
        
        Args:
            name: 哈希表名
            keys: 要删除的字段名列表
            
        Returns:
            成功删除的字段数量
        """
        return self.client.hdel(name, *keys)
    
    def hexists(self, name: str, key: str) -> bool:
        """
        检查哈希表中字段是否存在
        
        Args:
            name: 哈希表名
            key: 字段名
            
        Returns:
            字段是否存在
        """
        return self.client.hexists(name, key)
    
    def hkeys(self, name: str) -> List[str]:
        """
        获取哈希表所有字段名
        
        Args:
            name: 哈希表名
            
        Returns:
            字段名列表
        """
        return self.client.hkeys(name)
    
    def hvals(self, name: str) -> List[str]:
        """
        获取哈希表所有字段值
        
        Args:
            name: 哈希表名
            
        Returns:
            字段值列表
        """
        return self.client.hvals(name)
    
    def hlen(self, name: str) -> int:
        """
        获取哈希表字段数量
        
        Args:
            name: 哈希表名
            
        Returns:
            字段数量
        """
        return self.client.hlen(name)
    
    # ==================== List 操作 ====================
    
    def lpush(self, name: str, *values: Any) -> int:
        """
        从列表左侧插入元素
        
        Args:
            name: 列表名
            values: 要插入的值
            
        Returns:
            列表的长度
        """
        return self.client.lpush(name, *values)
    
    def rpush(self, name: str, *values: Any) -> int:
        """
        从列表右侧插入元素
        
        Args:
            name: 列表名
            values: 要插入的值
            
        Returns:
            列表的长度
        """
        return self.client.rpush(name, *values)
    
    def lpop(self, name: str) -> Optional[str]:
        """
        从列表左侧弹出元素
        
        Args:
            name: 列表名
            
        Returns:
            弹出的元素，如果列表为空则返回 None
        """
        return self.client.lpop(name)
    
    def rpop(self, name: str) -> Optional[str]:
        """
        从列表右侧弹出元素
        
        Args:
            name: 列表名
            
        Returns:
            弹出的元素，如果列表为空则返回 None
        """
        return self.client.rpop(name)
    
    def llen(self, name: str) -> int:
        """
        获取列表长度
        
        Args:
            name: 列表名
            
        Returns:
            列表长度
        """
        return self.client.llen(name)
    
    def lrange(self, name: str, start: int, end: int) -> List[str]:
        """
        获取列表指定范围内的元素
        
        Args:
            name: 列表名
            start: 起始索引
            end: 结束索引
            
        Returns:
            元素列表
        """
        return self.client.lrange(name, start, end)
    
    # ==================== Set 操作 ====================
    
    def sadd(self, name: str, *values: Any) -> int:
        """
        向集合添加元素
        
        Args:
            name: 集合名
            values: 要添加的值
            
        Returns:
            成功添加的元素数量
        """
        return self.client.sadd(name, *values)
    
    def srem(self, name: str, *values: Any) -> int:
        """
        从集合移除元素
        
        Args:
            name: 集合名
            values: 要移除的值
            
        Returns:
            成功移除的元素数量
        """
        return self.client.srem(name, *values)
    
    def smembers(self, name: str) -> set:
        """
        获取集合所有成员
        
        Args:
            name: 集合名
            
        Returns:
            集合成员
        """
        return self.client.smembers(name)
    
    def scard(self, name: str) -> int:
        """
        获取集合成员数量
        
        Args:
            name: 集合名
            
        Returns:
            成员数量
        """
        return self.client.scard(name)
    
    def sismember(self, name: str, value: Any) -> bool:
        """
        检查值是否是集合的成员
        
        Args:
            name: 集合名
            value: 要检查的值
            
        Returns:
            是否是集合成员
        """
        return self.client.sismember(name, value)
    
    # ==================== Sorted Set 操作 ====================
    
    def zadd(self, name: str, mapping: Dict[str, float]) -> int:
        """
        向有序集合添加成员
        
        Args:
            name: 有序集合名
            mapping: 成员和分数的映射字典
            
        Returns:
            成功添加的成员数量
        """
        return self.client.zadd(name, mapping)
    
    def zrange(self, name: str, start: int, end: int, withscores: bool = False) -> List:
        """
        获取有序集合指定排名范围内的成员
        
        Args:
            name: 有序集合名
            start: 起始排名
            end: 结束排名
            withscores: 是否返回分数
            
        Returns:
            成员列表
        """
        return self.client.zrange(name, start, end, withscores=withscores)
    
    def zrem(self, name: str, *values: Any) -> int:
        """
        从有序集合移除成员
        
        Args:
            name: 有序集合名
            values: 要移除的成员
            
        Returns:
            成功移除的成员数量
        """
        return self.client.zrem(name, *values)
    
    def zcard(self, name: str) -> int:
        """
        获取有序集合成员数量
        
        Args:
            name: 有序集合名
            
        Returns:
            成员数量
        """
        return self.client.zcard(name)
    
    def zscore(self, name: str, value: Any) -> Optional[float]:
        """
        获取有序集合成员的分数
        
        Args:
            name: 有序集合名
            value: 成员值
            
        Returns:
            成员的分数，如果成员不存在则返回 None
        """
        return self.client.zscore(name, value)
    
    # ==================== 通用操作 ====================
    
    def keys(self, pattern: str = "*") -> List[str]:
        """
        查找所有符合模式的键
        
        Args:
            pattern: 匹配模式
            
        Returns:
            匹配的键列表
        """
        return self.client.keys(pattern)
    
    def flushdb(self):
        """清空当前数据库的所有键"""
        return self.client.flushdb()
    
    def ping(self) -> bool:
        """
        测试 Redis 连接
        
        Returns:
            连接是否正常
        """
        try:
            return self.client.ping()
        except Exception:
            return False


# 创建全局实例
redis_helper = RedisHelper()
