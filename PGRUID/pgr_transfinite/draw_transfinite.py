"""战双历战映射"""
import asyncio
from pathlib import Path
from typing import Union

from gsuid_core.logger import logger

from ..utils.api.requests import pgr_api
from ..utils.image import pic_download_from_url
from ..utils.path import ROLE_ICON_PATH, FASHION_PATH
from ..pgr_config import PREFIX
from ..pgr_roleinfo.draw_roleinfo import _get_grade_info

from XutheringWavesUID.XutheringWavesUID.utils.render_utils import (
    PLAYWRIGHT_AVAILABLE,
    render_html,
    image_to_base64,
)
from XutheringWavesUID.XutheringWavesUID.utils.image import get_event_avatar, pil_to_b64
from jinja2 import Environment, FileSystemLoader

IMGS_PATH = Path(__file__).parent / "imgs"
_TEMPLATE_DIR = Path(__file__).parent
pgr_trans_templates = Environment(loader=FileSystemLoader([str(_TEMPLATE_DIR)]))


def _local_b64(cache_dir: Path, url: str) -> str:
    if not url:
        return ""
    filename = url.split("/")[-1]
    webp_path = cache_dir / Path(filename).with_suffix(".webp")
    orig_path = cache_dir / filename
    if webp_path.exists():
        return image_to_base64(webp_path)
    if orig_path.exists():
        return image_to_base64(orig_path)
    return ""


async def draw_transfinite_img(ev, uid: str) -> Union[bytes, str]:
    user_id = ev.user_id
    bot_id = ev.bot_id

    ck = await pgr_api.get_self_pgr_ck(uid, user_id, bot_id)
    if not ck:
        return f"[战双] token 已失效，请使用【{PREFIX}登录】重新绑定！"

    trans_data, account = await asyncio.gather(
        pgr_api.get_transfinite(uid, ck),
        pgr_api.get_account_data(uid, ck),
    )

    if not trans_data:
        return "[战双] 获取历战映射数据失败"
    if not trans_data.isUnlock:
        return "[战双] 历战映射未解锁"

    # 下载 boss 图标 + 角色图标
    download_tasks = []
    if trans_data.bossIconUrl:
        download_tasks.append(pic_download_from_url(FASHION_PATH, trans_data.bossIconUrl))
    for char in trans_data.characterList:
        if char.iconUrl:
            download_tasks.append(pic_download_from_url(ROLE_ICON_PATH, char.iconUrl))
    if download_tasks:
        await asyncio.gather(*download_tasks, return_exceptions=True)

    # 用户头像
    avatar_img = await get_event_avatar(ev, size=200)
    head_b64 = pil_to_b64(avatar_img, quality=75) if avatar_img else ""

    # Boss 图标
    boss_icon_b64 = _local_b64(FASHION_PATH, trans_data.bossIconUrl)

    # 角色列表
    characters = []
    for char in trans_data.characterList:
        gi = _get_grade_info(char.grade)
        characters.append({
            "bodyName": char.bodyName,
            "iconB64": _local_b64(ROLE_ICON_PATH, char.iconUrl),
            "gradeClass": gi["gradeClass"],
            "gradeDisplay": gi["gradeDisplay"],
            "isPlus": gi["isPlus"],
        })

    context = {
        "account": {
            "roleId": account.roleId if account else uid,
            "level": account.level if account else 0,
            "roleName": account.roleName if account else uid,
            "serverName": account.serverName if account else "",
            "rank": account.rank if account else 0,
            "headB64": head_b64,
        },
        "headerBgB64": image_to_base64(IMGS_PATH / "head.png"),
        "avatarBoxB64": image_to_base64(IMGS_PATH / "avatorBoxIcon.png"),
        "titleBgB64": image_to_base64(IMGS_PATH / "titleBg.png"),
        "contentBgB64": image_to_base64(IMGS_PATH / "contentBg.jpg"),
        "bossIconB64": boss_icon_b64,
        "operatorArea": trans_data.operatorArea,
        "challengeArea": trans_data.challengeArea,
        "challengeLevel": trans_data.challengeLevel,
        "operatorCount": trans_data.operatorCount,
        "process": trans_data.process,
        "fightTime": trans_data.fightTime,
        "characters": characters,
    }

    if not PLAYWRIGHT_AVAILABLE:
        from ..pgr_config.config_default import PGRConfig
        if not PGRConfig.get_config("RemoteRenderEnable").data:
            return "[战双] Playwright 未安装且未配置外置渲染"

    img = await render_html(pgr_trans_templates, "pgr_transfinite.html", context)
    if img:
        return img
    return "[战双] 渲染历战映射失败"
