"""PGRUID - 战双帕弥什插件"""

from gsuid_core.sv import Plugins
from gsuid_core.logger import logger


Plugins(
    name="PGRUID",
    force_prefix=["pgr", "zs", "zz"],
    allow_empty_prefix=False
)

logger.success("[PGRUID] 插件加载完成")
