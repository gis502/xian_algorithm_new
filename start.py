"""
项目启动脚本 - 支持多环境和跨平台
使用 Dynaconf 进行环境隔离配置
"""
from pathlib import Path
from app.core.launcher import AppLauncher

# 添加项目根目录到Python路径
project_root = Path(__file__).parent


if __name__ == "__main__":
    # 创建并运行启动器
    launcher = AppLauncher(project_root)
    launcher.run()
