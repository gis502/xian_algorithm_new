# Xian Algorithm New

基于 FastAPI + PostgreSQL 的现代化 Python Web 应用框架。

## 特性

- ✅ 模块化架构（API/Config/Core/Utils）
- ✅ 多环境配置（开发/生产）
- ✅ 跨平台支持（Windows/Linux/Mac）
- ✅ 完整的数据库 CRUD 封装
- ✅ 自动依赖管理
- ✅ 自动生成 API 文档
- ✅ 降雨栅格插值服务（IDW算法）

## 快速开始

### 1. 环境要求

- Python 3.13+
- PostgreSQL

### 2. 配置

根据环境选择配置文件（无需复制，直接使用）：

- **开发环境**：`.env.development`
- **生产环境**：`.env.production`

编辑对应的配置文件，修改数据库信息：

```env
# .env.development 或 .env.production
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=test_db
API_HOST=127.0.0.1  # 仅监听本地请求
```

### 3. 启动

**后台运行（推荐）：**

```bash
# Windows - 开发环境
scripts\start_dev.bat

# Windows - 生产环境
scripts\start_prod.bat

# Linux/Mac - 开发环境
bash scripts/start_dev.sh

# Linux/Mac - 生产环境
bash scripts/start_prod.sh
```

**前台运行（调试用）：**

```bash
python start.py
```

### 4. 停止

```bash
# Windows
scripts\stop.bat

# Linux/Mac
bash scripts/stop.sh
```

### 5. 访问

- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 项目结构

```
xian_algorithm_new/
├── app/
│   ├── api/          # API 路由
│   ├── config/       # 配置管理
│   ├── core/         # 核心功能
│   ├── models/       # 数据模型
│   ├── services/     # 业务逻辑
│   └── utils/        # 工具函数
├── scripts/          # 启动脚本
├── logs/             # 日志目录
├── tests/            # 测试目录
├── start.py          # 启动入口
└── requirements.txt  # 依赖包
```

## 配置说明

配置采用三层结构（优先级从高到低）：

1. **.env 文件** - 用户自定义配置（数据库地址、密码等）
2. **环境配置类** - 开发/生产环境的差异化配置（日志级别、连接池等）
3. **基础配置类** - 通用默认值

只需修改 `.env` 文件即可覆盖大部分配置。

## 常用操作

### API接口

#### 1. 获取降雨栅格数据

```bash
curl -X POST "http://localhost:8000/rainfall/grid" \
     -H "Content-Type: application/json" \
     -d '{
           "start_time": "2024-01-01T00:00:00",
           "end_time": "2024-01-01T12:00:00",
           "district_id": 1,
           "resolution": 0.01
         }'
```

#### 2. 获取雨量站点数据

```bash
curl "http://localhost:8000/rainfall/stations?start_time=2024-01-01T00:00:00&end_time=2024-01-01T12:00:00"
```

### 切换环境

通过启动脚本自动选择对应的配置文件：

```bash
# Windows - 开发环境（后台）
scripts\start_dev.bat

# Windows - 生产环境（后台）
scripts\start_prod.bat

# Linux/Mac - 开发环境（后台）
bash scripts/start_dev.sh

# Linux/Mac - 生产环境（后台）
bash scripts/start_prod.sh
```

**停止应用：**

```bash
# Windows
scripts\stop.bat

# Linux/Mac
bash scripts/stop.sh
```

或者手动设置环境变量：

```bash
# Windows PowerShell
$env:ENVIRONMENT="production"
python start.py

# Windows CMD
set ENVIRONMENT=production
python start.py

# Linux/Mac
export ENVIRONMENT=production
python start.py
```

### 数据库操作

```python
from app.core.database import db_manager

# 插入
db_manager.insert("users", {"name": "张三", "email": "test@example.com"})

# 查询
users = db_manager.select("users", conditions={"age": 25})

# 更新
db_manager.update("users", {"name": "李四"}, {"id": 1})

# 删除
db_manager.delete("users", {"id": 1})
```

### 添加新 API

1. 在 `app/api/` 创建路由文件
2. 在 `app/main.py` 注册路由

```python
from app.api import new_module
app.include_router(new_module.router)
```

## 技术栈

- FastAPI 0.109.0
- SQLAlchemy 2.0.25
- PostgreSQL (psycopg2-binary)
- Pydantic 2.5.3
- Uvicorn 0.27.0

## 注意事项

- ⚠️ 不要将 `.env.development` 和 `.env.production` 文件提交到 Git
- ⚠️ 生产环境务必修改默认密码
- ⚠️ 定期清理 `logs/` 目录下的日志文件
- ⚠️ Linux/Mac 下首次运行需给脚本添加执行权限：`chmod +x scripts/*.sh`

## 许可证

MIT
