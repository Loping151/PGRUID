from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from ..pgr_config import PREFIX
from .draw_transfinite import draw_transfinite_img

from XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesBind
from XutheringWavesUID.XutheringWavesUID.utils.at_help import ruser_id

sv_trans = SV("战双历战映射")


@sv_trans.on_fullmatch(
    ("历战映射", "历战", "映射"),
    block=True,
)
async def pgr_transfinite(bot: Bot, ev: Event):
    uid = await WavesBind.get_uid_by_game(ruser_id(ev), ev.bot_id, game_name="pgr")
    if not uid:
        return await bot.send(
            f"[战双] 您还未绑定战双UID，请使用【{PREFIX}登录】完成绑定！"
        )
    img = await draw_transfinite_img(ev, uid)
    return await bot.send(img)
