from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from ..pgr_config import PREFIX
from .draw_fashion import draw_fashion_img

from XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesBind
from XutheringWavesUID.XutheringWavesUID.utils.at_help import ruser_id

sv_fashion = SV("战双涂装")


@sv_fashion.on_fullmatch(
    ("涂装", "涂装列表", "皮肤", "皮肤列表"),
    block=True,
)
async def pgr_fashion(bot: Bot, ev: Event):
    uid = await WavesBind.get_uid_by_game(ruser_id(ev), ev.bot_id, game_name="pgr")
    if not uid:
        return await bot.send(
            f"[战双] 您还未绑定战双UID，请使用【{PREFIX}登录】完成绑定！"
        )
    img = await draw_fashion_img(ev, uid)
    return await bot.send(img)
