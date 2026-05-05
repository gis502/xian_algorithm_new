"""
平台检测工具 - 兼容Windows和Linux
"""
import sys
import os
import platform
from pathlib import Path
from typing import Tuple


class PlatformDetector:
    """平台检测器"""
    
    def __init__(self):
        self.os_name = os.name
        self.platform_system = platform.system()
        self.platform_release = platform.release()
        self.platform_version = platform.version()
        self.python_version = sys.version_info
        self.is_windows = self.platform_system == "Windows"
        self.is_linux = self.platform_system == "Linux"
        self.is_macos = self.platform_system == "Darwin"
    
    def get_platform_info(self) -> dict:
        """获取平台信息"""
        return {
            "os_name": self.os_name,
            "platform_system": self.platform_system,
            "platform_release": self.platform_release,
            "platform_version": self.platform_version,
            "python_version": f"{self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}",
            "is_windows": self.is_windows,
            "is_linux": self.is_linux,
            "is_macos": self.is_macos,
        }
    
    def check_python_version(self, min_version: Tuple[int, int] = (3, 13)) -> bool:
        """检查Python版本是否满足要求
        
        Args:
            min_version: 最低版本要求 (major, minor)
            
        Returns:
            是否满足版本要求
        """
        current = (self.python_version.major, self.python_version.minor)
        return current >= min_version
    
    def get_path_separator(self) -> str:
        """获取路径分隔符"""
        return "\\" if self.is_windows else "/"
    
    def normalize_path(self, path: str) -> str:
        """标准化路径"""
        return Path(path).as_posix()
    
    def get_project_root(self) -> Path:
        """获取项目根目录"""
        return Path(__file__).parent.parent.parent
    
    def ensure_directory(self, path: Path, create: bool = True) -> bool:
        """确保目录存在
        
        Args:
            path: 目录路径
            create: 是否自动创建
            
        Returns:
            目录是否存在
        """
        if path.exists():
            return True
        
        if create:
            try:
                path.mkdir(parents=True, exist_ok=True)
                return True
            except Exception as e:
                print(f"创建目录失败 {path}: {e}")
                return False
        
        return False
    
    def get_env_file_path(self) -> Path:
        """获取环境配置文件路径"""
        return self.get_project_root() / ".env"
    
    def format_command_for_platform(self, command: str) -> str:
        """根据平台格式化命令
        
        Args:
            command: 原始命令
            
        Returns:
            适合当前平台的命令
        """
        if self.is_windows:
            # Windows特定命令转换
            if command.startswith("ls "):
                return command.replace("ls ", "dir ")
            elif command.startswith("cat "):
                return command.replace("cat ", "type ")
            elif command.startswith("rm "):
                return command.replace("rm ", "del ")
            elif command.startswith("cp "):
                return command.replace("cp ", "copy ")
            elif command.startswith("mv "):
                return command.replace("mv ", "move ")
        else:
            # Linux/Mac特定命令转换
            if command.startswith("dir "):
                return command.replace("dir ", "ls ")
            elif command.startswith("type "):
                return command.replace("type ", "cat ")
            elif command.startswith("del "):
                return command.replace("del ", "rm ")
            elif command.startswith("copy "):
                return command.replace("copy ", "cp ")
            elif command.startswith("move "):
                return command.replace("move ", "mv ")
        
        return command
    
    def print_platform_banner(self):
        """打印平台信息横幅"""
        info = self.get_platform_info()
        print("=" * 60)
        print("  系统信息")
        print("=" * 60)
        print(f"  操作系统: {info['platform_system']} {info['platform_release']}")
        print(f"  Python版本: {info['python_version']}")
        print(f"  项目根目录: {self.get_project_root()}")
        print("=" * 60)


# 全局平台检测器实例
platform_detector = PlatformDetector()
