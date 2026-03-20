from typing import Dict

from gsuid_core.utils.plugins_config.models import (
    GSC,
    GsIntConfig,
    GsBoolConfig,
)
from gsuid_core.utils.plugins_config.gs_config import StringConfig
from ..utils.path import CONFIG_PATH

CONFIG_DEFAULT: Dict[str, GSC] = {
    # ==================== 公告配置 ====================
    "PGRAnnOpen": GsBoolConfig(
        "公告推送总开关",
        "公告推送总开关",
        True,
    ),
    "AnnMinuteCheck": GsIntConfig(
        "公告推送时间检测（单位min）",
        "公告推送时间检测（单位min）",
        10,
        60,
    ),
    "CacheDaysToKeep": GsIntConfig(
        "保留缓存公告资源天数",
        "自动删除创建时间早于此天数的公告图片缓存，每次启动和每天定时执行",
        42,
        3650,
    ),
}


PGRConfig = StringConfig(
    "PGRUID",
    CONFIG_PATH,
    CONFIG_DEFAULT,
)
