from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event

from ..pgr_config import PREFIX
from .draw_roleinfo import draw_roleinfo_img

from XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesBind

sv_roleinfo = SV("战双卡片")


@sv_roleinfo.on_fullmatch(
    ("卡片", "card", "信息", "kp"),
    block=True,
)
async def pgr_roleinfo(bot: Bot, ev: Event):
    uid = await WavesBind.get_uid_by_game(ev.user_id, ev.bot_id, game_name="pgr")
    if not uid:
        return await bot.send(
            f"[战双] 您还未绑定战双UID，请使用【{PREFIX}绑定UID】或【{PREFIX}登录】完成绑定！"
        )
    img = await draw_roleinfo_img(ev, uid)
    return await bot.send(img)
