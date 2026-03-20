from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from gsuid_core.plugins.XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesBind
from gsuid_core.plugins.XutheringWavesUID.XutheringWavesUID.utils.at_help import ruser_id

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
    )
)
async def send_pgr_mr(bot: Bot, ev: Event):
    await bot.logger.info(f"[战双]开始执行[体力信息]: {ruser_id(ev)}")
    uid = await WavesBind.get_uid_by_game(ruser_id(ev), ev.bot_id, game_name="pgr")
    if not uid:
        return await bot.send(f"尚未绑定战双UID，请使用【{PREFIX}绑定 UID】进行绑定")
    return await bot.send(await draw_mr_img(bot, ev))
