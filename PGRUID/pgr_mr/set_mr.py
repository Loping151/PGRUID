"""PGR 体力背景设置"""
from pathlib import Path

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.logger import logger

from plugins.XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesBind, WavesUser
from plugins.XutheringWavesUID.XutheringWavesUID.utils.at_help import ruser_id

from ..pgr_config import PREFIX
from ..utils.constants import PGR_GAME_ID
from ..utils.database.models import PGRUserSettings
from ..utils.util import get_hide_uid_pref, hide_uid

sv_pgr_set = SV("战双设置")


@sv_pgr_set.on_command(("设置体力背景", "体力背景"), block=True)
async def set_stamina_bg(bot: Bot, ev: Event):
    """设置体力卡片背景图

    用法:
      pgr设置体力背景 <图片路径>  - 设置自定义背景
      pgr设置体力背景             - 重置为默认背景
    """
    user_id = ruser_id(ev)
    uid_list = await WavesBind.get_uid_list_by_game(user_id, ev.bot_id, game_name="pgr")
    if not uid_list:
        return await bot.send(f"尚未绑定战双UID，请使用【{PREFIX}绑定 UID】进行绑定")

    uid = uid_list[0]
    value = ev.text.strip()

    # 如果传了图片
    if ev.image:
        from plugins.XutheringWavesUID.XutheringWavesUID.utils.image import pic_download_from_url
        from ..utils.path import MAIN_PATH

        save_dir = MAIN_PATH / "custom_bg" / uid
        save_dir.mkdir(parents=True, exist_ok=True)

        try:
            img_url = ev.image
            if isinstance(img_url, list):
                img_url = img_url[0]
            await pic_download_from_url(save_dir, img_url)
            name = img_url.split("/")[-1]
            saved_path = save_dir / name
            # webp 转存后可能后缀变了
            webp_path = saved_path.with_suffix(".webp")
            final_path = webp_path if webp_path.exists() else saved_path
            value = str(final_path)
        except Exception as e:
            logger.warning(f"[战双] 下载体力背景图失败: {e}")
            return await bot.send("背景图下载失败，请稍后再试")

    if value and not Path(value).exists():
        return await bot.send(f"路径不存在: {value}")

    res = await PGRUserSettings.set_stamina_bg(user_id, ev.bot_id, uid, value)
    if res == 0:
        masked_uid = hide_uid(
            uid,
            user_pref=await get_hide_uid_pref(uid, user_id, ev.bot_id),
        )
        if not value:
            return await bot.send(f"已重置体力背景为默认!\nUID[{masked_uid}]")
        return await bot.send(f"设置成功!\nUID[{masked_uid}]\n当前体力背景: {Path(value).name}")
    return await bot.send("设置失败!")


@sv_pgr_set.on_prefix("设置")
async def set_hide_uid_pgr(bot: Bot, ev: Event):
    """战双 设置(取消)隐藏UID. 仅登录的本人 WavesUser(game_id=PGR) 行可写, uid 大小写无关.

    不带 block, 让 ev.text 不含 "隐藏uid" 时静默放行其它"设置..."处理器。
    """
    if "隐藏uid" not in ev.text.lower():
        return
    user_id = ruser_id(ev)

    uid_list = await WavesBind.get_uid_list_by_game(user_id, ev.bot_id, game_name="pgr")
    if not uid_list:
        return await bot.send(f"尚未绑定战双UID，请使用【{PREFIX}绑定 UID】进行绑定")
    uid = uid_list[0]

    waves_user = await WavesUser.select_waves_user(
        uid, user_id, ev.bot_id, game_id=PGR_GAME_ID
    )
    if not waves_user:
        return await bot.send(
            f"当前UID[{hide_uid(uid)}]未登录战双账号, 请先使用【{PREFIX}登录】完成绑定"
        )

    value = "off" if "取消" in ev.text else "on"
    await WavesUser.update_data_by_data(
        select_data={
            "user_id": user_id,
            "bot_id": ev.bot_id,
            "uid": uid,
            "game_id": PGR_GAME_ID,
        },
        update_data={"hide_uid_self_value": value},
    )

    action = "已开启" if value == "on" else "已关闭"
    await bot.send(f"{action}隐藏UID!\nUID[{hide_uid(uid, user_pref=value)}]")
