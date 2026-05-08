
from dynaconf import Dynaconf

settings = Dynaconf(
    # 配置文件
    settings_files=['settings.toml', '.secrets.toml'],
    # 环境变量
    environments=True,
    # 环境切换变量
    env_switcher="ENV_FOR_DYNACONF",
)
