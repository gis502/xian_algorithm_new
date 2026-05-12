"""
应用启动器
"""
import sys
from pathlib import Path

from app.core.env_checker import check_environment
from app.core.venv_manager import check_virtualenv
from app.core.dependency_manager import check_dependencies
from app.utils.logger import get_logger
from app.utils.thread_pool_manager import block_main_thread, thread_pool_manager
from app.core.rainfall_manager import rainfall_manager


class AppLauncher:
    """应用启动器"""

    def __init__(self, project_root: Path):
        """
        初始化启动器
        
        Args:
            project_root: 项目根目录路径
        """
        self.project_root = project_root
        self.logger = get_logger()

    def run(self):
        """执行完整的启动流程"""
        try:
            # 检查系统和Python版本
            if not check_environment():
                sys.exit(1)

            # 检查虚拟环境
            check_virtualenv(self.project_root)

            # 检查安装依赖
            check_dependencies(self.project_root)

            # 启动应用
            print("\n" + "=" * 50)
            print("✓ 所有检查通过，准备启动应用...")
            print("=" * 50)
            self.logger.info("系统环境检查通过，开始执行主程序...")
            start()

        except Exception as e:
            self.logger.error(f"启动失败: {e}")
            sys.exit(1)


def start():
    """启动应用服务"""
    logger = get_logger()
    
    # 启动降雨站点监测
    logger.info("启动降雨站点监测服务...")
    rainfall_manager.monitoring_rainfall_station_id('2025-08-20 12:00:00')
    
    # 阻塞主线程，防止程序立即退出
    block_main_thread()
