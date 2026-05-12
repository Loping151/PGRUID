from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event

from ..pgr_config import PREFIX
from .draw_roleinfo import draw_roleinfo_img

from plugins.XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesBind
from plugins.XutheringWavesUID.XutheringWavesUID.utils.at_help import ruser_id

sv_roleinfo = SV("战双卡片")


@sv_roleinfo.on_fullmatch(
    ("卡片", "card", "信息", "kp"),
    block=True,
    to_ai="""查询自己战双 (PGR) 账号的综合信息卡片（指挥使等级、伊甸资历、装备等）。

当用户问「我的战双信息 / pgr 卡片 / 战双个人面板 / 战双指挥使」时调用。
需绑定战双 UID。

Args:
    text: 无需参数。
""",
)
async def pgr_roleinfo(bot: Bot, ev: Event):
    uid = await WavesBind.get_uid_by_game(ruser_id(ev), ev.bot_id, game_name="pgr")
    if not uid:
        return await bot.send(
            f"[战双] 您还未绑定战双UID，请使用【{PREFIX}绑定UID】或【{PREFIX}登录】完成绑定！"
        )
    img = await draw_roleinfo_img(ev, uid)
    return await bot.send(img)
