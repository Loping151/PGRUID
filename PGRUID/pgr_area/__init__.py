from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from ..pgr_config import PREFIX
from .draw_area import draw_area_img

from plugins.XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesBind
from plugins.XutheringWavesUID.XutheringWavesUID.utils.at_help import ruser_id

sv_area = SV("战双纷争战区")


@sv_area.on_fullmatch(
    ("纷争战区", "战区", "纷争"),
    block=True,
    to_ai="""查询自己战双 (PGR) 账号纷争战区的赛季积分与位次。

当用户问「战双战区 / pgr 纷争 / 纷争战区排名 / 我的战双战区」时调用。
需绑定战双 UID。

Args:
    text: 无需参数。
""",
)
async def pgr_area(bot: Bot, ev: Event):
    uid = await WavesBind.get_uid_by_game(ruser_id(ev), ev.bot_id, game_name="pgr")
    if not uid:
        return await bot.send(
            f"[战双] 您还未绑定战双UID，请使用【{PREFIX}登录】完成绑定！"
        )
    img = await draw_area_img(ev, uid)
    return await bot.send(img)
