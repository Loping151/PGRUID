from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from plugins.XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesBind
from plugins.XutheringWavesUID.XutheringWavesUID.utils.at_help import ruser_id

from ..pgr_config import PREFIX
from .draw_pgr_mr import draw_mr_img

sv_pgr_mr = SV("战双查询体力")


@sv_pgr_mr.on_fullmatch(
    (
        "每日",
        "mr",
        "体力",
        "血清",
        "便笺",
        "日程",
    ),
    to_ai="""查询自己战双 (PGR) 账号当前的体力（血清）、便笺与日程信息。

当用户问「战双体力 / pgr 血清 / 战双每日 / 战双便笺 / 我的战双日程」时调用。
需绑定战双 UID。

Args:
    text: 无需参数。
""",
)
async def send_pgr_mr(bot: Bot, ev: Event):
    await bot.logger.info(f"[战双]开始执行[体力信息]: {ruser_id(ev)}")
    uid = await WavesBind.get_uid_by_game(ruser_id(ev), ev.bot_id, game_name="pgr")
    if not uid:
        return await bot.send(f"尚未绑定战双UID，请使用【{PREFIX}绑定 UID】进行绑定")
    return await bot.send(await draw_mr_img(bot, ev))
