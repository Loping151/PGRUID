from typing import List, Union

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from ..pgr_config import PREFIX
from ..utils.api.requests import pgr_api

# 直接复用 xwuid 的数据库和登录
from XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesBind, WavesUser
from XutheringWavesUID.XutheringWavesUID.utils.constants import PGR_GAME_ID, WAVES_GAME_ID
from XutheringWavesUID.XutheringWavesUID.wutheringwaves_user.deal import add_cookie
from XutheringWavesUID.XutheringWavesUID.wutheringwaves_user.login_succ import login_success_msg
from gsuid_core.sv import get_plugin_available_prefix

pgr_bind_uid = SV("战双绑定UID", priority=10)
pgr_login = SV("战双登录")
pgr_token = SV("战双Token", priority=5)
pgr_get_token = SV("战双获取Token", area="DIRECT")


async def _send_text(bot: Bot, ev: Event, msg: str):
    at_sender = True if ev.group_id else False
    return await bot.send(
        (" " if at_sender else "") + msg,
        at_sender=at_sender,
    )


# ===== 登录 =====

@pgr_login.on_command(("登录", "登陆", "登入", "login", "dl"), block=True)
async def pgr_login_msg(bot: Bot, ev: Event):
    xw_prefix = get_plugin_available_prefix("XutheringWavesUID")
    return await _send_text(
        bot, ev,
        f"[战双] 库洛账号通用，请使用【{xw_prefix}登录】进行登录\n"
        f"登录后战双UID将自动绑定\n"
        f"也可使用【{PREFIX}添加token xxx】直接绑定"
    )


# ===== 绑定/切换/删除/查看 =====

@pgr_bind_uid.on_command(
    (
        "绑定",
        "切换",
        "删除全部UID",
        "删除全部特征码",
        "删除",
        "查看",
    ),
    block=True,
)
async def pgr_bind_msg(bot: Bot, ev: Event):
    uid = ''.join(filter(str.isdigit, ev.text.strip()))
    qid = ev.user_id

    if "绑定" in ev.command:
        if not uid:
            return await _send_text(bot, ev, f"[战双] 请带上正确的UID\n例如：{PREFIX}绑定12345678")

        res = await WavesBind.insert_uid(
            qid, ev.bot_id, uid, ev.group_id,
            lenth_limit=None,
            game_name="pgr",
        )
        if res == 0 or res == -2:
            await WavesBind.switch_uid_by_game(qid, ev.bot_id, uid, game_name="pgr")

        msg_map = {
            0: f"[战双] UID[{uid}]绑定成功！\n使用【{PREFIX}查看】查看已绑定的UID",
            -1: f"[战双] UID[{uid}]格式不正确！",
            -2: f"[战双] UID[{uid}]已经绑定过了！",
            -3: "[战双] 输入了错误的格式!",
        }
        return await _send_text(bot, ev, msg_map.get(res, f"[战双] 绑定失败(code={res})"))

    elif "切换" in ev.command:
        retcode = await WavesBind.switch_uid_by_game(qid, ev.bot_id, uid if uid else None, game_name="pgr")
        if retcode == 0:
            uid_list = await WavesBind.get_uid_list_by_game(qid, ev.bot_id, game_name="pgr")
            if uid_list:
                return await _send_text(bot, ev, f"[战双] 切换UID[{uid_list[0]}]成功！")
            else:
                return await _send_text(bot, ev, "[战双] 尚未绑定任何UID")
        elif retcode == -3:
            return await _send_text(bot, ev, "[战双] 只绑定了一个UID，无需切换")
        else:
            return await _send_text(bot, ev, f"[战双] 尚未绑定该UID[{uid}]")

    elif "查看" in ev.command:
        uid_list = await WavesBind.get_uid_list_by_game(qid, ev.bot_id, game_name="pgr")
        if uid_list:
            lines = ["[战双] 已绑定的UID列表："]
            for idx, u in enumerate(uid_list, 1):
                current = " (当前)" if idx == 1 else ""
                lines.append(f"  {idx}. {u}{current}")
            return await _send_text(bot, ev, "\n".join(lines))
        else:
            return await _send_text(bot, ev, "[战双] 尚未绑定任何UID")

    elif "删除全部" in ev.command:
        await WavesBind.update_data(
            user_id=qid,
            bot_id=ev.bot_id,
            **{WavesBind.get_gameid_name("pgr"): None},
        )
        return await _send_text(bot, ev, "[战双] 已删除全部绑定的UID")

    elif "删除" in ev.command:
        if not uid:
            return await _send_text(bot, ev, f"[战双] 该命令需要带上UID\n例如：{PREFIX}删除12345678")

        res = await WavesBind.delete_uid(qid, ev.bot_id, uid, game_name="pgr")
        if res != 0:
            return await _send_text(bot, ev, f"[战双] 尚未绑定该UID[{uid}]")

        await WavesUser.delete_cookie(uid, qid, ev.bot_id, game_id=PGR_GAME_ID)
        return await _send_text(bot, ev, f"[战双] 删除UID[{uid}]成功")


# ===== 添加/获取 Token =====

def _get_ck_and_devcode(text: str, split_str: str = ",") -> tuple:
    ck, devcode = "", ""
    try:
        parts = text.split(split_str, maxsplit=1)
        ck = parts[0].strip()
        devcode = parts[1].strip() if len(parts) > 1 else ""
    except ValueError:
        pass
    return ck, devcode


@pgr_token.on_prefix(("添加CK", "添加ck", "添加Token", "添加token", "添加TOKEN"), block=True)
async def pgr_add_token(bot: Bot, ev: Event):
    at_sender = True if ev.group_id else False
    text = ev.text.strip()

    ck, did = "", ""
    for i in ["，", ","]:
        if i in text:
            ck, did = _get_ck_and_devcode(text, split_str=i)
            break
    if not ck:
        ck = text.strip()

    if did and len(did) not in (32, 36, 40):
        return await _send_text(bot, ev, f"[战双] 格式错误！\n例如【{PREFIX}添加token token】或【{PREFIX}添加token token,did】")

    if not ck:
        return await _send_text(bot, ev, f"[战双] 格式错误！\n例如【{PREFIX}添加token token】")

    ck_msg = await add_cookie(ev, ck, did, is_login=False)
    if "成功" in ck_msg:
        await bot.send((" " if at_sender else "") + ck_msg.rstrip("\n"), at_sender)

        user = await WavesUser.get_user_by_attr(ev.user_id, ev.bot_id, "cookie", ck, game_id=WAVES_GAME_ID)
        if user:
            return await login_success_msg(bot, ev, user)
        return

    ck_msg = ck_msg.rstrip("\n") if isinstance(ck_msg, str) else ck_msg
    await bot.send((" " if at_sender and isinstance(ck_msg, str) else "") + ck_msg if isinstance(ck_msg, str) else ck_msg, at_sender)


@pgr_get_token.on_fullmatch(("获取ck", "获取CK", "获取Token", "获取token", "获取TOKEN"), block=True)
async def pgr_get_token_msg(bot: Bot, ev: Event):
    uid_list = await WavesBind.get_uid_list_by_game(ev.user_id, ev.bot_id, game_name="pgr")
    if uid_list is None:
        return await bot.send("[战双] 尚未绑定任何UID\n")

    msg: List[str] = []
    for uid in uid_list:
        if not (uid and uid.isdigit()):
            continue
        waves_user = await WavesUser.select_waves_user(
            uid, ev.user_id, ev.bot_id, game_id=PGR_GAME_ID
        )
        if not waves_user:
            continue

        ck = await pgr_api.get_self_pgr_ck(uid, ev.user_id, ev.bot_id)
        if not ck:
            continue
        msg.append(f"战双uid: {uid} 的 token 和 did")
        msg.append(f"添加token {waves_user.cookie}, {waves_user.did}")
        msg.append("--------------------------------")

    if not msg:
        return await bot.send("您当前未绑定token或者token已全部失效\n")

    msg.append("直接复制并加上前缀即可用于token登录")
    await bot.send(msg)
