from gsuid_core.sv import SV, get_plugin_available_prefix
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from .config_default import PGRConfig

sv_self_config = SV("PGR配置")


PREFIX = get_plugin_available_prefix("PGRUID")
