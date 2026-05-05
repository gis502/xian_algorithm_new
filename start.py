"""
项目启动脚本 - 支持多环境和跨平台
"""
import sys
import subprocess
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_platform():
    """检测平台信息"""
    print("=" * 60)
    print("  系统信息检测")
    print("=" * 60)
    
    from app.utils.platform_utils import platform_detector
    platform_detector.print_platform_banner()
    
    return platform_detector


def check_python_version():
    """检查Python版本是否为3.13或更高"""
    print("\n" + "=" * 60)
    print("  Python版本检查")
    print("=" * 60)
    
    from app.utils.platform_utils import platform_detector
    
    current_version = sys.version_info
    print(f"当前Python版本: {current_version.major}.{current_version.minor}.{current_version.micro}")
    
    if not platform_detector.check_python_version((3, 13)):
        print("\n❌ 错误: Python版本过低!")
        print(f"   当前版本: {current_version.major}.{current_version.minor}.{current_version.micro}")
        print("   要求版本: 3.13 或更高")
        print("\n请升级到Python 3.13或更高版本:")
        print("   下载地址: https://www.python.org/downloads/")
        print("=" * 60)
        sys.exit(1)
    
    print(f"✅ Python版本检查通过: {current_version.major}.{current_version.minor}.{current_version.micro}")
    print("=" * 60)
    return True


def get_environment():
    """获取运行环境"""
    print("\n" + "=" * 60)
    print("  环境配置")
    print("=" * 60)
    
    environment = os.getenv("ENVIRONMENT", "development")
    print(f"当前环境: {environment}")
    
    if environment not in ["development", "production"]:
        print(f"⚠️  警告: 未知环境 '{environment}'，使用默认开发环境")
        environment = "development"
    
    print("=" * 60)
    return environment


def install_dependencies():
    """检查并安装依赖包"""
    print("\n" + "=" * 60)
    print("  依赖包检查")
    print("=" * 60)
    
    requirements_file = "requirements.txt"
    
    if not os.path.exists(requirements_file):
        print(f"\n❌ 错误: 找不到依赖文件 {requirements_file}")
        sys.exit(1)
    
    # 读取已安装的包
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=freeze"],
            capture_output=True,
            text=True,
            check=True
        )
        installed_packages = {line.split("==")[0].lower() for line in result.stdout.strip().split("\n") if line}
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 检查已安装包失败: {e}")
        sys.exit(1)
    
    # 读取requirements.txt中的包
    with open(requirements_file, "r", encoding="utf-8") as f:
        required_packages = []
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                package_name = line.split("==")[0].lower()
                required_packages.append(line)
    
    # 检查缺失的包
    missing_packages = []
    for package_line in required_packages:
        package_name = package_line.split("==")[0].lower()
        if package_name not in installed_packages:
            missing_packages.append(package_line)
    
    if not missing_packages:
        print("\n✅ 所有依赖包已安装，无需重复安装")
        print("=" * 60)
        return True
    
    print(f"\n发现 {len(missing_packages)} 个未安装的依赖包:")
    for package in missing_packages:
        print(f"   - {package}")
    
    print("\n正在安装依赖包...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", requirements_file],
            check=True
        )
        print("\n✅ 依赖包安装成功")
        print("=" * 60)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 依赖包安装失败: {e}")
        print("=" * 60)
        sys.exit(1)


def initialize_database():
    """初始化数据库连接"""
    print("\n" + "=" * 60)
    print("  数据库初始化")
    print("=" * 60)
    
    try:
        from app.core.database import db_manager
        from app.config.settings import get_settings
        
        settings = get_settings()
        
        print(f"数据库地址: {settings.DB_HOST}:{settings.DB_PORT}")
        print(f"数据库名称: {settings.DB_NAME}")
        print(f"连接池大小: {settings.DB_POOL_SIZE}")
        
        # 测试数据库连接
        if db_manager.test_connection():
            print("✅ 数据库连接成功")
        else:
            print("⚠️  数据库连接失败，请检查配置")
            return False
        
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n⚠️  数据库初始化警告: {e}")
        print("   应用将继续启动，但数据库功能可能不可用")
        print("=" * 60)
        return False


def start_application(environment: str):
    """启动FastAPI应用"""
    print("\n" + "=" * 60)
    print("  启动FastAPI应用")
    print("=" * 60)
    
    try:
        from app.config.settings import get_settings
        import uvicorn
        
        settings = get_settings()
        
        print(f"应用名称: {settings.APP_NAME}")
        print(f"应用版本: {settings.APP_VERSION}")
        print(f"运行环境: {settings.ENVIRONMENT.value}")
        print(f"监听地址: {settings.API_HOST}:{settings.API_PORT}")
        print(f"调试模式: {'开启' if settings.DEBUG else '关闭'}")
        print(f"自动重载: {'开启' if hasattr(settings, 'RELOAD') and settings.RELOAD else '关闭'}")
        print("\n🚀 应用启动中...\n")
        print("=" * 60)
        
        # 启动uvicorn服务器
        uvicorn.run(
            "app.main:app",
            host=settings.API_HOST,
            port=settings.API_PORT,
            reload=settings.RELOAD if hasattr(settings, 'RELOAD') else settings.DEBUG,
            log_level=settings.LOG_LEVEL.lower()
        )
        
    except KeyboardInterrupt:
        print("\n\n应用已停止")
    except Exception as e:
        print(f"\n❌ 应用启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  Xian Algorithm New - 应用启动程序")
    print("=" * 60)
    
    # 检测平台信息
    check_platform()
    
    # 检查Python版本
    check_python_version()
    
    # 获取环境配置
    environment = get_environment()
    
    # 检查并安装依赖
    install_dependencies()
    
    # 初始化数据库
    initialize_database()
    
    # 启动应用
    start_application(environment)


if __name__ == "__main__":
    main()
