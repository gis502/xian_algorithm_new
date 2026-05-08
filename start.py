"""
项目启动脚本 - 支持多环境和跨平台
使用 Dynaconf 进行环境隔离配置
"""
import sys
import platform
from pathlib import Path
from app.utils.logger import get_logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
logger = get_logger()


def check_environment():
    """检查系统和Python版本"""
    # 识别操作系统
    os_name = platform.system()
    print(f"当前操作系统: {os_name}")

    if os_name not in ['Windows', 'Linux']:
        print(f"警告: 未测试的操作系统 {os_name}，可能存在问题")

    # 检查Python版本
    python_version = platform.python_version()
    print(f"当前Python版本: {python_version}")

    # 解析版本号
    major, minor, *_ = map(int, python_version.split('.'))

    if major == 3 and minor == 13:
        print("✓ Python版本符合要求 (3.13)")
        return True
    else:
        print(f"✗ Python版本不符合要求！")
        print(f"  当前版本: {python_version}")
        print(f"  要求版本: 3.13.x")
        print(f"\n请使用 Python 3.13 版本运行此项目")
        print(f"下载地址: https://www.python.org/downloads/")
        return False


def main():
    check_environment()


if __name__ == "__main__":
    main()
