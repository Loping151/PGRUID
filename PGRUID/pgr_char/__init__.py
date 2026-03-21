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
    get_name2id,
    update_full_body,
)
from .draw_char_card import draw_char_card

from XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesBind

sv_char = SV("战双角色面板", priority=5)
sv_refresh = SV("战双刷新面板", priority=4)
sv_alias = SV("战双别名管理", priority=10, pm=0)

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


# ===== 查看面板（从缓存读取）=====

@sv_char.on_regex(
    rf"^(?P<name>{CHAR_NAME_PATTERN})(?:面板|面包|🍞|mb)$",
    block=True,
)
async def pgr_char_panel(bot: Bot, ev: Event):
    name = ev.regex_dict.get("name", "").strip()
    if not name:
        return

    body_id = resolve_char_name(name)
    if body_id is None:
        return

    uid = await WavesBind.get_uid_by_game(ev.user_id, ev.bot_id, game_name="pgr")
    if not uid:
        return await _send(bot, ev, f"[战双] 您还未绑定战双UID，请使用【{PREFIX}登录】完成绑定！")

    # 从缓存读取，不实时请求
    img = await draw_char_card(ev, uid, body_id, use_cache=True)
    return await bot.send(img)


# ===== 刷新单角色面板 =====

@sv_refresh.on_regex(
    rf"^(?:刷新|更新)(?P<name>{CHAR_NAME_PATTERN})(?:面板|面包|🍞|mb)$",
    block=True,
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

    ck = await pgr_api.get_self_pgr_ck(uid, ev.user_id, ev.bot_id)
    if not ck:
        return await _send(bot, ev, f"[战双] token 已失效，请使用【{PREFIX}登录】重新绑定！")

    role_index = await pgr_api.get_role_index(uid, ck)
    if not role_index:
        return await _send(bot, ev, "[战双] 获取角色列表失败")

    # 更新 full_body.json + 下载图标
    await update_full_body(role_index)

    # 逐个刷新角色详情（限速：每个间隔 0.3s）
    total = len(role_index.characterList)
    success = 0
    for i, char in enumerate(role_index.characterList):
        try:
            detail = await pgr_api.get_role_detail(uid, ck, char.bodyId)
            if detail and detail.character:
                from .draw_char_card import _download_all_urls, _save_player_data
                raw_data = detail.model_dump()
                await _download_all_urls(raw_data)
                _save_player_data(uid, char.bodyId, raw_data)
                success += 1
        except Exception as e:
            logger.warning(f"[PGR] 刷新 {char.bodyName or ''} 失败: {e}")

        if i < total - 1:
            await asyncio.sleep(0.3)

    return await _send(bot, ev, f"[战双] 面板刷新完成！成功 {success}/{total}")


# ===== 别名管理 =====

@sv_alias.on_regex(
    rf"^添加(?P<name>{CHAR_NAME_PATTERN})别名(?P<alias>{CHAR_NAME_PATTERN})$",
    block=True,
)
async def pgr_add_alias(bot: Bot, ev: Event):
    name = ev.regex_dict.get("name", "").strip()
    alias = ev.regex_dict.get("alias", "").strip()
    if not name or not alias:
        return
    msg = add_alias(name, alias)
    return await _send(bot, ev, f"[战双] {msg}")


@sv_alias.on_regex(
    rf"^删除(?P<name>{CHAR_NAME_PATTERN})别名(?P<alias>{CHAR_NAME_PATTERN})$",
    block=True,
)
async def pgr_remove_alias(bot: Bot, ev: Event):
    name = ev.regex_dict.get("name", "").strip()
    alias = ev.regex_dict.get("alias", "").strip()
    if not name or not alias:
        return
    msg = remove_alias(name, alias)
    return await _send(bot, ev, f"[战双] {msg}")


@sv_alias.on_regex(
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
