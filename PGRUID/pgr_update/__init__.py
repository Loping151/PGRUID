from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from .draw_update_log import draw_update_log_img

sv_update = SV("PGR更新记录", pm=1, priority=4)


@sv_update.on_fullmatch(("更新记录", "更新日志", "log"), block=True)
async def pgr_update_log(bot: Bot, ev: Event):
    im = await draw_update_log_img()
    await bot.send(im)
