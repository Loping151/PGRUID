from PIL import Image

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.help.utils import register_help

from .get_help import ICON, get_help
from ..pgr_config import PREFIX

sv_pgr_help = SV("PGR帮助")


@sv_pgr_help.on_fullmatch(("帮助", "help", "bz"), block=True)
async def pgr_send_help_img(bot: Bot, ev: Event):
    await bot.send(await get_help(ev.user_pm))


if ICON.exists():
    register_help("PGRUID", f"{PREFIX}帮助", Image.open(ICON))
