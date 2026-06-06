"""
依赖管理模块
负责检查和管理项目依赖
"""
import sys
import json
import subprocess
import platform
from pathlib import Path


def check_dependencies(project_root: Path):
    """
    检查并安装项目依赖（使用虚拟环境）
    
    Args:
        project_root: 项目根目录路径
    """
    print("\n" + "=" * 50)
    print("步骤 3: 依赖检查")
    print("=" * 50)
    
    requirements_file = project_root / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"警告: 未找到 {requirements_file}")
        return
    
    # 获取虚拟环境中的 Python 可执行文件路径
    venv_path = project_root / ".venv"
    os_name = platform.system()
    
    if os_name == 'Windows':
        venv_python = venv_path / "Scripts" / "python.exe"
    else:  # Linux/Mac
        venv_python = venv_path / "bin" / "python3"
    
    if not venv_python.exists():
        print(f"错误: 虚拟环境Python不存在: {venv_python}")
        print("请先运行虚拟环境检查")
        sys.exit(1)
    
    try:
        # 使用虚拟环境中的 pip 检查已安装的包
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            check=True
        )
        
        installed_packages = {pkg['name'].lower() for pkg in json.loads(result.stdout)}
        
        # 读取 requirements.txt
        with open(requirements_file, 'r', encoding='utf-8') as f:
            required_packages = []
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # 提取包名（去掉版本信息）
                    pkg_name = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                    if pkg_name:
                        required_packages.append((pkg_name.lower(), line))
        
        # 检查缺失的依赖
        missing_packages = [
            req_line for pkg_name, req_line in required_packages 
            if pkg_name not in installed_packages
        ]
        
        if missing_packages:
            print(f"发现 {len(missing_packages)} 个未安装的依赖，正在使用虚拟环境安装...")
            subprocess.run(
                [
                    str(venv_python), "-m", "pip", "install",
                    "--trusted-host", "mirrors.aliyun.com",
                    "-r", str(requirements_file)
                ],
                check=True
            )
            print("✓ 依赖安装完成（虚拟环境）")
        else:
            print("✓ 所有依赖已安装（虚拟环境）")
            
    except subprocess.CalledProcessError as e:
        print(f"✗ 依赖检查/安装失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 依赖检查出错: {e}")
        sys.exit(1)
