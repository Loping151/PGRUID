import inspect
from typing import Optional

from gsuid_core.logger import logger


def is_from_plugin(plugin_name: str = "PGRUID") -> bool:
    """检查当前调用是否来自指定插件"""
    return get_current_plugin() == plugin_name


def get_current_plugin() -> Optional[str]:
    """获取当前执行的插件名称，不在插件中返回 None"""
    frame = inspect.currentframe()
    skip_files = ["plugin_checker.py", "bot_send_hook.py"]
    all_plugins = []

    try:
        frame = frame.f_back
        while frame:
            file_path = inspect.getframeinfo(frame).filename
            sep = "/plugins/" if "/plugins/" in file_path else (
                "\\plugins\\" if "\\plugins\\" in file_path else None
            )
            if sep:
                plugin_name = file_path.split(sep)[1].split(sep[0])[0]
                if not any(s in file_path for s in skip_files):
                    all_plugins.append(plugin_name)
            frame = frame.f_back

        if all_plugins:
            return all_plugins[-1]
    finally:
        del frame

    return None


def is_from_pgr_plugin() -> bool:
    return is_from_plugin("PGRUID")
