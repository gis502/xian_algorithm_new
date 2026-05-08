"""
虚拟环境管理模块
"""
import sys
import platform
import subprocess
from pathlib import Path


def check_virtualenv(project_root: Path) -> bool:
    """
    检查并创建虚拟环境
    
    Args:
        project_root: 项目根目录路径
        
    Returns:
        bool: 如果虚拟环境已存在返回True，新创建则返回False
    """
    print("\n" + "=" * 50)
    print("步骤 2: 虚拟环境检查")
    print("=" * 50)
    
    venv_path = project_root / ".venv"
    os_name = platform.system()
    
    # 根据系统确定Python可执行文件路径
    if os_name == 'Windows':
        python_exe = venv_path / "Scripts" / "python.exe"
    else:  # Linux
        python_exe = venv_path / "bin" / "python3"
    
    if not venv_path.exists():
        print(f"\n⚠ 虚拟环境不存在，正在创建...")
        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            print("✓ 虚拟环境创建成功")
            return True  # 继续执行后续步骤
        except subprocess.CalledProcessError as e:
            print(f"✗ 虚拟环境创建失败: {e}")
            sys.exit(1)
    else:
        print(f"✓ 虚拟环境已存在: {venv_path}")
        return True
