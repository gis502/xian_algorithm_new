"""
环境检查模块
负责检查操作系统和Python版本
"""
import platform


def check_environment():
    """
    检查系统和Python版本
    
    Returns:
        bool: 如果环境符合要求返回True，否则返回False
    """

    print("\n" + "=" * 50)
    print("步骤 1: 环境检查")
    print("=" * 50)
    
    # 识别操作系统
    os_name = platform.system()
    
    if os_name not in ['Windows', 'Linux']:
        print(f"警告: 未测试的操作系统 {os_name}，可能存在问题")
    
    # 检查Python版本
    python_version = platform.python_version()
    
    # 解析版本号
    major, minor, *_ = map(int, python_version.split('.'))
    
    if major == 3 and minor == 13:
        return True
    else:
        print(f"✗ Python版本不符合要求！")
        print(f"  当前版本: {python_version}")
        print(f"  要求版本: 3.13.x")
        print(f"\n请使用 Python 3.13 版本运行此项目")
        print(f"下载地址: https://www.python.org/downloads/")
        return False
