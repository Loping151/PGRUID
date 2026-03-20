from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from ..pgr_config import PREFIX
from .draw_resource import draw_resource_img

from XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesBind

sv_resource = SV("战双资源")


@sv_resource.on_fullmatch(
    ("资源", "资产", "收入", "黑卡"),
    block=True,
)
async def pgr_resource(bot: Bot, ev: Event):
    uid = await WavesBind.get_uid_by_game(ev.user_id, ev.bot_id, game_name="pgr")
    if not uid:
        return await bot.send(
            f"[战双] 您还未绑定战双UID，请使用【{PREFIX}登录】完成绑定！"
        )
    img = await draw_resource_img(ev, uid)
    return await bot.send(img)
