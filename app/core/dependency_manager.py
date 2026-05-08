"""
依赖管理模块
负责检查和管理项目依赖
"""
import sys
import json
import subprocess
from pathlib import Path


def check_dependencies(project_root: Path):
    """
    检查并安装项目依赖
    
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
    
    try:
        # 使用 pip list 检查已安装的包
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
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
            print(f"发现 {len(missing_packages)} 个未安装的依赖，正在安装...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                check=True
            )
            print("✓ 依赖安装完成")
        else:
            print("✓ 所有依赖已安装")
            
    except subprocess.CalledProcessError as e:
        print(f"✗ 依赖检查/安装失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 依赖检查出错: {e}")
        sys.exit(1)
