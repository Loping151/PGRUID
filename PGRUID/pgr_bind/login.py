"""PGR 登录指令

直接复用 xwuid 的登录流程，库洛账号通用
"""
import re

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from ..pgr_config import PREFIX

# 直接复用 xwuid 的登录函数
from XutheringWavesUID.XutheringWavesUID.wutheringwaves_login.login import (
    code_login,
    page_login,
)
from XutheringWavesUID.XutheringWavesUID.wutheringwaves_config import (
    PREFIX as XW_PREFIX,
)

sv_pgr_login = SV("战双登录")


@sv_pgr_login.on_command(("登录", "登陆", "登入", "login", "dl"), block=True)
async def pgr_login_msg(bot: Bot, ev: Event):
    at_sender = True if ev.group_id else False

    await bot.send(
        (" " if at_sender else "")
        + f"[战双] 如已使用过【{XW_PREFIX}登录】则无需再次登录！",
        at_sender=at_sender,
    )

    text = re.sub(r'["\n\t ]+', "", ev.text.strip())
    text = text.replace("，", ",")
    if text == "":
        return await page_login(bot, ev)

    elif "," in text:
        return await code_login(bot, ev, text)

    elif text.isdigit():
        return

    msg = f"[战双] 账号登录失败\n请重新输入命令【{PREFIX}登录】进行登录"
    return await bot.send(
        (" " if at_sender else "") + msg,
        at_sender=at_sender,
    )
