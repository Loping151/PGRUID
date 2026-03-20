"""PGR 体力背景设置"""
from pathlib import Path

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.logger import logger

from gsuid_core.plugins.XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesBind
from gsuid_core.plugins.XutheringWavesUID.XutheringWavesUID.utils.at_help import ruser_id

from ..pgr_config import PREFIX
from ..utils.database.models import PGRUserSettings

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
        from gsuid_core.plugins.XutheringWavesUID.XutheringWavesUID.utils.image import pic_download_from_url
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
        if not value:
            return await bot.send(f"已重置体力背景为默认!\nUID[{uid}]")
        return await bot.send(f"设置成功!\nUID[{uid}]\n当前体力背景: {Path(value).name}")
    return await bot.send("设置失败!")
