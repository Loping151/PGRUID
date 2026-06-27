import time

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event

from ..pgr_config import PREFIX
from ..utils.name_convert import (
    resolve_char_name,
    get_body_name_by_id,
    add_alias,
    remove_alias,
    get_alias_list,
    update_full_body,
)
from .draw_char_card import draw_char_card
from ..utils.path import PLAYER_PATH
from ..utils.player_store import compress_all

from plugins.XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesBind
from plugins.XutheringWavesUID.XutheringWavesUID.utils.at_help import ruser_id

sv_char = SV("战双角色面板", priority=5)
sv_refresh = SV("战双刷新面板", priority=4)
sv_alias = SV("战双别名管理", priority=10, pm=0)
sv_pgr_admin = SV("战双数据管理", pm=0)

CHAR_NAME_PATTERN = r"[\u4e00-\u9fa5a-zA-Z0-9·\-]{1,15}"

# ===== CD 管理 =====
_refresh_all_cd: dict[str, int] = {}  # key -> expire_timestamp
_refresh_single_cd: dict[str, int] = {}
REFRESH_ALL_CD = 60  # 全量刷新 CD 秒
REFRESH_SINGLE_CD = 10  # 单角色刷新 CD 秒


def _check_cd(cd_map: dict, key: str) -> int:
    """返回剩余 CD 秒数，0 表示可用"""
    expire = cd_map.get(key, 0)
    remain = expire - int(time.time())
    return max(0, remain)


def _set_cd(cd_map: dict, key: str, cd: int):
    cd_map[key] = int(time.time()) + cd


async def _send(bot: Bot, ev: Event, msg: str):
    at_sender = True if ev.group_id else False
    return await bot.send((" " if at_sender else "") + msg, at_sender=at_sender)


# ===== 查看面板 =====

@sv_char.on_regex(
    rf"^(?P<name>{CHAR_NAME_PATTERN})(?:面板|面包|🍞|mb)$",
    block=True,
    to_ai="""查询自己战双 (PGR) 指定角色的面板（属性 / 武器 / 意识等），从缓存读取不实时刷新。

当用户问「<角色名>面板 / pgr <角色>面板 / 看看我的战双某角色练度」时调用。
需绑定战双 UID。

Args:
    raw_text: 必须形如 "<角色名>面板" / "<角色名>mb" / "<角色名>面包" / "<角色名>🍞"。
""",
)
async def pgr_char_panel(bot: Bot, ev: Event):
    name = ev.regex_dict.get("name", "").strip()
    if not name:
        return

    body_id = resolve_char_name(name)
    if body_id is None:
        return

    uid = await WavesBind.get_uid_by_game(ruser_id(ev), ev.bot_id, game_name="pgr")
    if not uid:
        return await _send(bot, ev, f"[战双] 您还未绑定战双UID，请使用【{PREFIX}登录】完成绑定！")

    # 从缓存读取，不实时请求
    img = await draw_char_card(ev, uid, body_id, use_cache=True)
    return await bot.send(img)


# ===== 刷新单角色面板 =====

@sv_refresh.on_regex(
    rf"^(?:刷新|更新)(?P<name>{CHAR_NAME_PATTERN})(?:面板|面包|🍞|mb)$",
    block=True,
    to_ai="""刷新（实时拉接口）自己战双 (PGR) 某个角色的面板缓存。

当用户问「刷新 <角色>面板 / 更新 <角色>面板 / 重新拉一下战双 <角色>」时调用。
需绑定战双 UID，且服务端走单角色 CD。

Args:
    raw_text: 必须形如 "刷新<角色>面板" / "更新<角色>mb" 等。
""",
)
async def pgr_refresh_one(bot: Bot, ev: Event):
    name = ev.regex_dict.get("name", "").strip()
    if not name:
        return

    body_id = resolve_char_name(name)
    if body_id is None:
        return await _send(bot, ev, f"[战双] 未找到角色「{name}」，请检查名称或添加别名")

    uid = await WavesBind.get_uid_by_game(ev.user_id, ev.bot_id, game_name="pgr")
    if not uid:
        return await _send(bot, ev, f"[战双] 您还未绑定战双UID，请使用【{PREFIX}登录】完成绑定！")

    # CD 检查
    cd_key = f"{ev.user_id}_{uid}"
    remain = _check_cd(_refresh_single_cd, cd_key)
    if remain > 0:
        return await _send(bot, ev, f"[战双] 请等待{remain}s后再刷新角色面板！")

    _set_cd(_refresh_single_cd, cd_key, REFRESH_SINGLE_CD)

    # 实时请求
    img = await draw_char_card(ev, uid, body_id, use_cache=False)
    return await bot.send(img)


# ===== 刷新全部面板 =====

@sv_refresh.on_fullmatch(
    (
        "刷新面板", "刷新面版", "更新面板", "更新面版",
        "面板刷新", "面板更新", "面板", "面版",
    ),
    block=True,
    to_ai="""一次性刷新自己战双 (PGR) 全部角色面板缓存（耗时较长，每个角色之间限速）。

当用户问「战双面板 / 刷新面板 / 更新所有面板 / 我的战双全部刷一下」时调用。
需绑定战双 UID 和有效 token，且服务端走全员 CD。返回成功 / 总数统计。

Args:
    text: 无需参数。
""",
)
async def pgr_refresh_all(bot: Bot, ev: Event):
    uid = await WavesBind.get_uid_by_game(ev.user_id, ev.bot_id, game_name="pgr")
    if not uid:
        return await _send(bot, ev, f"[战双] 您还未绑定战双UID，请使用【{PREFIX}登录】完成绑定！")

    # CD 检查
    cd_key = f"{ev.user_id}_{uid}"
    remain = _check_cd(_refresh_all_cd, cd_key)
    if remain > 0:
        return await _send(bot, ev, f"[战双] 请等待{remain}s后再刷新面板！")

    _set_cd(_refresh_all_cd, cd_key, REFRESH_ALL_CD)

    from ..utils.api.requests import pgr_api
    import asyncio

    _is_self, ck = await pgr_api.get_ck_result(uid, ev.user_id, ev.bot_id)
    if not ck:
        return await _send(bot, ev, f"[战双] token 已失效，请使用【{PREFIX}登录】重新绑定！")

    role_index = await pgr_api.get_role_index(uid, ck)
    if not role_index:
        return await _send(bot, ev, "[战双] 获取角色列表失败")

    # 更新 full_body.json + 下载图标
    await update_full_body(role_index)

    # 逐个刷新角色详情，限速每个间隔 0.3s
    total = len(role_index.characterList or [])
    success = 0
    for i, char in enumerate(role_index.characterList or []):
        try:
            detail = await pgr_api.get_role_detail(uid, ck, char.bodyId)
            if detail and detail.character:
                from .draw_char_card import _download_all_urls, _save_player_data
                raw_data = detail.model_dump()
                await _download_all_urls(raw_data)
                _save_player_data(uid, char.bodyId, raw_data)
                success += 1
        except Exception as e:
            logger.warning(f"[战双·角色] 刷新 {char.bodyName or ''} 失败: {e}")

        if i < total - 1:
            await asyncio.sleep(0.3)

    return await _send(bot, ev, f"[战双] 面板刷新完成！成功 {success}/{total}")


# ===== 别名管理 =====

@sv_alias.on_regex(
    rf"^添加(?P<name>{CHAR_NAME_PATTERN})别名(?P<aliases>.+)$",
    block=True,
)
async def pgr_add_alias(bot: Bot, ev: Event):
    import re
    name = ev.regex_dict.get("name", "").strip()
    raw = ev.regex_dict.get("aliases", "").strip()
    if not name or not raw:
        return
    alias_list = [a.strip() for a in re.split(r'[,，\s]+', raw) if a.strip()]
    if not alias_list:
        return
    msgs = [add_alias(name, a) for a in alias_list]
    return await _send(bot, ev, "[战双] " + "\n".join(msgs))


@sv_alias.on_regex(
    rf"^删除(?P<name>{CHAR_NAME_PATTERN})别名(?P<aliases>.+)$",
    block=True,
)
async def pgr_remove_alias(bot: Bot, ev: Event):
    import re
    name = ev.regex_dict.get("name", "").strip()
    raw = ev.regex_dict.get("aliases", "").strip()
    if not name or not raw:
        return
    alias_list = [a.strip() for a in re.split(r'[,，\s]+', raw) if a.strip()]
    if not alias_list:
        return
    msgs = [remove_alias(name, a) for a in alias_list]
    return await _send(bot, ev, "[战双] " + "\n".join(msgs))


@sv_char.on_regex(
    rf"^(?P<name>{CHAR_NAME_PATTERN})别名(?:列表)?$",
    block=True,
)
async def pgr_alias_list(bot: Bot, ev: Event):
    name = ev.regex_dict.get("name", "").strip()
    if not name:
        return

    body_id = resolve_char_name(name)
    if body_id is None:
        return await _send(bot, ev, f"[战双] 未找到角色「{name}」")

    real_name = get_body_name_by_id(body_id)
    aliases = get_alias_list(real_name)

    if not aliases:
        return await _send(bot, ev, f"[战双]「{real_name}」暂无自定义别名")

    lines = [f"[战双]「{real_name}」的别名列表："]
    for a in aliases:
        lines.append(f"  · {a}")
    return await _send(bot, ev, "\n".join(lines))


def _fmt_size(n: float) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}TB"


@sv_pgr_admin.on_fullmatch(("压缩数据",), block=True)
async def pgr_compress_data(bot: Bot, ev: Event):
    import asyncio

    done, fail, before, after = await asyncio.to_thread(compress_all, PLAYER_PATH)
    if not done:
        return await _send(bot, ev, f"[战双] 无需压缩（失败 {fail}）")
    ratio = after / before * 100 if before else 0
    msg = (
        "[战双] 压缩完成\n"
        f"压缩前 {_fmt_size(before)} → 压缩后 {_fmt_size(after)}\n"
        f"压缩率 {ratio:.1f}%（省 {100 - ratio:.1f}%）"
    )
    if fail:
        msg += f"\n失败 {fail}"
    return await _send(bot, ev, msg)
