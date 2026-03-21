from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from ..pgr_config import PREFIX
from .draw_stronghold import draw_stronghold_img

from XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesBind
from XutheringWavesUID.XutheringWavesUID.utils.at_help import ruser_id

sv_stronghold = SV("战双诺曼复兴战")


@sv_stronghold.on_fullmatch(
    ("诺曼复兴战", "诺曼", "复兴战", "矿区"),
    block=True,
)
async def pgr_stronghold(bot: Bot, ev: Event):
    uid = await WavesBind.get_uid_by_game(ruser_id(ev), ev.bot_id, game_name="pgr")
    if not uid:
        return await bot.send(
            f"[战双] 您还未绑定战双UID，请使用【{PREFIX}登录】完成绑定！"
        )
    img = await draw_stronghold_img(ev, uid)
    return await bot.send(img)
