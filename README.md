# 西安项目算法服务

## 核心功能

### 1. 暴雨灾害链预测

- **触发因子**：降雨强度、持续时间、累计降雨量
- **环境因子**：高程、坡度、坡向、土壤类型、岩性、土地利用、植被指数等 16 个因子
- **预测目标**：滑坡、泥石流、崩塌、城市内涝
- **数据来源**：自动从气象站获取实时降雨数据

### 2. 地震灾害链预测

- **触发因子**：震级、震中距、地震烈度
- **环境因子**：高程、坡度、坡向、土壤类型、岩性、距离断裂带距离等 14 个因子
- **预测目标**：地震触发的滑坡、泥石流、崩塌
- **空间计算**：自动计算震中距和烈度分布

### 3. 推理结果管理

- **持久化存储**：所有预测结果自动保存到数据库
- **操作类型追踪**：支持实时监测、情景模拟、应急评估等操作分类
- **历史查询**：支持按时间、事件类型、操作类型查询历史预测记录

### 4. 栅格数据生成

- **降雨栅格插值**：基于站点数据生成空间降雨分布栅格（PNG 格式）
- **Redis 缓存**：栅格元数据缓存到 Redis，提升查询性能
- **文件存储**：栅格图片存储到文件系统，支持 CDN 加速

---

## 项目结构

```
xian_algorithm_new/
├── app/                          # 应用主目录
│   ├── api/                      # FastAPI 路由
│   │   ├── rainfall.py           # 暴雨预测接口
│   │   ├── earthquake.py         # 地震预测接口
│   │   └── __init__.py
│   ├── config/                   # 配置模块
│   │   ├── dbn/                  # DBN 模型配置
│   │   │   ├── rainfall_dbn_graph.yaml      # 暴雨图结构
│   │   │   ├── rainfall_cpt_params.yaml     # 暴雨条件概率表
│   │   │   ├── earthquake_dbn_graph.yaml    # 地震图结构
│   │   │   └── earthquake_cpt_params.yaml   # 地震条件概率表
│   │   ├── paths.py              # 路径配置
│   │   └── __init__.py
│   ├── core/                     # 核心模块
│   │   ├── launcher.py           # 应用启动器
│   │   ├── env_checker.py        # 环境检查
│   │   ├── venv_manager.py       # 虚拟环境管理
│   │   ├── dependency_manager.py # 依赖管理
│   │   ├── rainfall_manager.py   # 降雨监测管理器
│   │   ├── server.py             # FastAPI 服务器
│   │   └── __init__.py
│   ├── models/                   # 数据模型
│   │   ├── dbn/                  # DBN 模型
│   │   │   ├── rainfall/         # 暴雨模型
│   │   │   │   ├── rainfall_dbn.py
│   │   │   │   └── discretizer.py
│   │   │   └── earthquake/       # 地震模型
│   │   │       ├── earthquake_dbn.py
│   │   │       └── discretizer.py
│   │   └── __init__.py
│   ├── repositories/             # 数据访问层
│   │   ├── dbn_repository.py     # DBN 数据查询
│   │   └── __init__.py
│   ├── schemas/                  # Pydantic 数据模型
│   │   ├── api_schemas.py        # API 请求/响应模型
│   │   └── __init__.py
│   ├── services/                 # 业务逻辑层
│   │   ├── rainfall_grid_service.py  # 降雨栅格服务
│   │   └── __init__.py
│   └── utils/                    # 工具函数
│       ├── logger.py             # 日志工具
│       ├── api_deps.py           # API 依赖注入
│       ├── thread_pool_manager.py # 线程池管理
│       ├── spatial_utils.py      # 空间计算工具
│       └── __init__.py
├── logs/                         # 日志目录
├── scripts/                      # 脚本目录
├── test/                         # 测试目录
├── .venv/                        # 虚拟环境（自动生成）
├── .gitignore
├── .secrets.toml                 # 敏感配置（不提交到 Git）
├── config.py                     # Dynaconf 配置入口
├── settings.toml                 # 环境配置文件
├── requirements.txt              # Python 依赖
├── start.py                      # 启动脚本
└── README.md                     # 项目文档
```

---

## 环境要求

### 系统要求

- **操作系统**：Windows 10/11、Linux（Ubuntu 20.04+）、macOS 10.15+
- **Python 版本**：3.10
- **内存**：至少 4GB RAM
- **磁盘空间**：至少 2GB 可用空间

### 外部依赖

- **PostgreSQL 12+**：主数据库
- **Redis 6.0+**：缓存服务
- **Git**：版本控制

---

## 快速开始

### 1. 安装依赖

```bash
# 直接运行启动脚本，会自动安装依赖
python start.py

# 或者手动安装
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `settings.toml` 文件，修改数据库、Redis 等配置：

```toml
[development]
DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASSWORD = "your_password"
DB_NAME = "xian_new"

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_PASSWORD = ""
```

### 3. 启动服务

```bash
python start.py
```

启动成功后会看到类似输出：

```
==================================================
步骤 1: 系统和 Python 版本检查
==================================================
✓ Python 版本: 3.10.x

==================================================
步骤 2: 虚拟环境检查
==================================================
✓ 虚拟环境已存在

==================================================
步骤 3: 依赖检查
==================================================
✓ 所有依赖已安装

==================================================
✓ 所有检查通过，准备启动应用...
==================================================
INFO:     Started server process [xxxxx]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8082 (Press CTRL+C to quit)
```

### 4. 访问 API 文档

浏览器打开：http://127.0.0.1:8082/docs

---

## 配置说明

### 多环境配置

项目使用 **Dynaconf** 管理多环境配置，支持以下环境：

- `development`：开发环境
- `production`：生产环境

通过环境变量切换：

```bash
# Windows
set ENV_FOR_DYNACONF=production

# Linux/Mac
export ENV_FOR_DYNACONF=production
```

### 主要配置项

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `DB_HOST` | PostgreSQL 主机地址 | `localhost` |
| `DB_PORT` | PostgreSQL 端口 | `5432` |
| `DB_USER` | 数据库用户名 | `postgres` |
| `DB_PASSWORD` | 数据库密码 | `password` |
| `DB_NAME` | 数据库名称 | `xian_new` |
| `API_HOST` | FastAPI 监听地址 | `127.0.0.1` |
| `API_PORT` | FastAPI 监听端口 | `8082` |
| `REDIS_HOST` | Redis 主机地址 | `localhost` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `LOG_LEVEL` | 日志级别 | `DEBUG` / `INFO` / `WARNING` |
| `FILE_STORE_DIR` | 文件存储根目录 | `G:/files` |

### 敏感配置

敏感信息（如密码、密钥）应放在 `.secrets.toml` 文件中，该文件已被 `.gitignore` 忽略：

```toml
[development]
DB_PASSWORD = "secret_password"
REDIS_PASSWORD = "redis_secret"

[production]
DB_PASSWORD = "prod_secret"
```

---

## API 接口

### 基础信息

- **Base URL**: `http://127.0.0.1:8082`
- **API 文档**: `http://127.0.0.1:8082/docs` (Swagger UI)
- **备用文档**: `http://127.0.0.1:8082/redoc` (ReDoc)

### 1. 暴雨灾害链预测

**接口**: `POST /rainfall/predict`

**请求参数**:

```json
{
  "point_ids": [1, 2, 3],          // 可选，点位ID列表
  "region_code": "610104",          // 可选，行政区划代码
  "rainfall": 50.5,                 // 可选，累计降雨量(mm)
  "duration": 2.0,                  // 可选，持续时间(h)
  "operation_type": "实时监测"      // 操作类型
}
```

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1001,
      "type": "隐患点",
      "probability": 0.7523,
      "level": "高"
    },
    {
      "id": 1002,
      "type": "风险点",
      "probability": 0.4215,
      "level": "中"
    }
  ],
  "record_id": 12345
}
```

**说明**:
- `point_ids` 和 `region_code` 二选一，都不传则查询所有点
- `rainfall` 和 `duration` 不传时，系统自动从气象表获取最新数据
- `record_id` 是保存的推理记录 ID，可用于后续查询

### 2. 地震灾害链预测

**接口**: `POST /earthquake/predict`

**请求参数**:

```json
{
  "point_ids": [1, 2, 3],           // 可选，点位ID列表
  "region_code": "610104",          // 可选，行政区划代码
  "magnitude": 6.5,                 // 必填，震级(Richter)
  "depth": 10.0,                    // 可选，震源深度(km)，默认10
  "epicenter_lon": 108.95,          // 必填，震中经度
  "epicenter_lat": 34.27,           // 必填，震中纬度
  "occurred_time": "2024-01-01T12:00:00",  // 必填，地震发生时间
  "operation_type": "应急评估"      // 操作类型
}
```

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 2001,
      "type": "隐患点",
      "probability": 0.8234,
      "level": "高"
    }
  ],
  "record_id": 12346
}
```

### 3. 模型状态查询

**接口**: `GET /models/status`

**响应示例**:

```json
{
  "rainfall_model_loaded": true,
  "earthquake_model_loaded": true
}
```

---

## 数据库设计

### 核心表结构

#### 1. xian_risk_factors（风险因子表）

存储隐患点和风险点的静态因子数据。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键（内部关联ID） |
| source_id | INTEGER | 源表ID（隐患点或风险点真实ID） |
| source_type | SMALLINT | 源类型（1=隐患点，2=风险点） |
| lon | DECIMAL | 经度 |
| lat | DECIMAL | 纬度 |
| static_factors | JSONB | 静态因子数据 |
| is_delete | SMALLINT | 删除标记（0=正常，1=删除） |

**static_factors 字段示例**:

```json
{
  "dem_value": 1250.5,
  "slope_value": 25.3,
  "aspect_value": 180.0,
  "soil_type": "brown_soil",
  "lithology": "acid_rock",
  "landuse": "forest",
  "landform": "mountain",
  "vegetation_index": 0.65,
  "river_distance": 500.0,
  "fault_distance": 2000.0
}
```

#### 2. xian_inference_result（推理结果表）

存储预测结果记录。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| event_type | VARCHAR | 事件类型（rainfall/earthquake） |
| occurred_time | TIMESTAMP | 事件发生时间 |
| operation_type | VARCHAR | 操作类型 |
| condition | JSONB | 输入条件 |
| result | JSONB | 预测结果 |
| created_at | TIMESTAMP | 创建时间 |

**result 字段示例**:

```json
[
  {
    "point_id": 1001,
    "source_type": 1,
    "lon": 108.95,
    "lat": 34.27,
    "disaster_probabilities": {
      "landslide": 0.7523,
      "debris_flow": 0.4215,
      "collapse": 0.3102
    },
    "disaster_levels": {
      "landslide": "高",
      "debris_flow": "中",
      "collapse": "低"
    }
  }
]
```

#### 3. xian_hidden_danger_spots（隐患点表）

存储隐患点基础信息。

#### 4. xian_risk_spots（风险点表）

存储风险点基础信息。

---

## 开发指南

### 添加新的 DBN 模型

1. **创建模型目录**: `app/models/dbn/<model_name>/`
2. **定义图结构**: 创建 `<model_name>_dbn_graph.yaml`
3. **定义条件概率表**: 创建 `<model_name>_cpt_params.yaml`
4. **实现模型类**: 继承基础 DBN 类，实现推理逻辑
5. **注册模型**: 在 `app/utils/api_deps.py` 中添加模型加载函数
6. **创建 API 接口**: 在 `app/api/` 下创建路由文件

### 日志规范

项目使用 Loguru 作为日志库：

```python
from app.utils.logger import get_logger

logger = get_logger()

logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
```

**日志特性**:
- 按大小轮转（50 MB）
- 保留 7 天
- 自动压缩旧日志
- 异步写入，避免文件锁定

### 数据库查询规范

所有 DBN 相关的数据库查询统一放在 `app/repositories/dbn_repository.py`：

```python
from app.repositories.dbn_repository import dbn_repository

# 获取所有点
points = dbn_repository.get_all_points(region_code="610104")

# 根据ID获取点
point = dbn_repository.get_point_by_id(1001)
```

### 线程池使用

对于耗时操作，使用线程池管理器：

```python
from app.utils.thread_pool_manager import thread_pool_manager

def heavy_task():
    # 耗时操作
    pass

future = thread_pool_manager.submit(heavy_task)
result = future.result()
```

---

## 常见问题

### 1. 启动时提示 `ModuleNotFoundError`

**问题**: 缺少依赖包

**解决**: 
```bash
pip install -r requirements.txt
```

### 2. 日志文件锁定错误（Windows）

**问题**: `PermissionError: [WinError 32] 另一个程序正在使用此文件`

**原因**: 多个进程同时写入日志文件

**解决**: 
- 项目已配置 `enqueue=True` 和 `delay=True` 避免此问题
- 如果仍出现，删除 `logs/` 目录下的日志文件后重启

### 3. 数据库连接失败

**问题**: `could not connect to server`

**检查**:
1. PostgreSQL 服务是否启动
2. `settings.toml` 中的数据库配置是否正确
3. 网络连接是否正常
4. 防火墙是否阻止端口

### 4. 虚拟环境未激活

**问题**: 依赖安装到系统 Python 而非虚拟环境

**解决**: 
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

或者直接运行 `python start.py`，项目会自动切换到虚拟环境。

### 5. 模型加载缓慢

**原因**: DBN 模型首次加载需要初始化条件概率表

**优化**: 
- 模型采用单例模式，只加载一次
- 使用 `get_rainfall_model()` 和 `get_earthquake_model()` 获取模型实例

---

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

