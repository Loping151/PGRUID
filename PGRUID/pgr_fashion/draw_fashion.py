"""战双涂装列表

请求 characterFashion + weaponFashion，下载涂装图标，渲染列表
"""
import asyncio
from pathlib import Path
from typing import Union

from gsuid_core.logger import logger
from XutheringWavesUID.XutheringWavesUID.utils.at_help import ruser_id

from ..utils.api.requests import pgr_api
from ..utils.image import pic_download_from_url
from ..utils.path import FASHION_PATH, WEAPON_FASHION_PATH
from ..pgr_config import PREFIX

from XutheringWavesUID.XutheringWavesUID.utils.render_utils import (
    PLAYWRIGHT_AVAILABLE,
    render_html,
    image_to_base64,
)
from XutheringWavesUID.XutheringWavesUID.wutheringwaves_config import WutheringWavesConfig
from XutheringWavesUID.XutheringWavesUID.utils.image import get_event_avatar, get_qq_avatar, pil_to_b64
from jinja2 import Environment, FileSystemLoader

IMGS_PATH = Path(__file__).parent / "imgs"
_TEMPLATE_DIR = Path(__file__).parent
pgr_fashion_templates = Environment(loader=FileSystemLoader([str(_TEMPLATE_DIR)]))


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


async def draw_fashion_img(ev, uid: str) -> Union[bytes, str]:
    user_id = ruser_id(ev)
    bot_id = ev.bot_id

    _is_self, ck = await pgr_api.get_ck_result(uid, user_id, bot_id)
    if not ck:
        return f"[战双] token 已失效，请使用【{PREFIX}登录】重新绑定！"

    char_fashion, weapon_fashion, account = await asyncio.gather(
        pgr_api.get_character_fashion(uid, ck),
        pgr_api.get_weapon_fashion(uid, ck),
        pgr_api.get_account_data(uid, ck),
    )

    if not char_fashion and not weapon_fashion:
        return "[战双] 获取涂装数据失败"

    # 下载所有涂装图标
    tasks = []
    if char_fashion:
        for f in (char_fashion.fashionList or []):
            if f.skinIcon:
                tasks.append(pic_download_from_url(FASHION_PATH, f.skinIcon))
    if weapon_fashion:
        for f in (weapon_fashion.fashionList or []):
            if f.skinIcon:
                tasks.append(pic_download_from_url(WEAPON_FASHION_PATH, f.skinIcon))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    # 用户头像
    avatar_img = None
    if ev.bot_id == "onebot":
        avatar_img = await get_qq_avatar(user_id, size=640)
    if avatar_img is None:
        avatar_img = await get_event_avatar(ev)
    head_b64 = pil_to_b64(avatar_img, quality=75) if avatar_img else ""

    # 构建涂装列表
    char_fashions = []
    if char_fashion:
        for f in (char_fashion.fashionList or []):
            char_fashions.append({
                "name": f.skinName,
                "iconB64": _local_b64(FASHION_PATH, f.skinIcon),
            })

    weapon_fashions = []
    if weapon_fashion:
        for f in (weapon_fashion.fashionList or []):
            weapon_fashions.append({
                "name": f.skinName,
                "iconB64": _local_b64(WEAPON_FASHION_PATH, f.skinIcon),
            })

    context = {
        "account": {
            "roleId": account.roleId if account else uid,
            "level": account.level if account else 0,
            "roleName": account.roleName if account else uid,
            "serverName": account.serverName if account else "",
            "rank": account.rank if account else 0,
            "rank_label": "勋阶" if (account and account.rank) else "等级",
            "rank_val": account.rank if (account and account.rank) else (account.level if account else 0),
            "headB64": head_b64,
        },
        "headerBgB64": image_to_base64(IMGS_PATH / "head.png"),
        "avatarBoxB64": image_to_base64(IMGS_PATH / "avatorBoxIcon.png"),
        "titleBgB64": image_to_base64(IMGS_PATH / "titleBg.png"),
        "contentBgB64": image_to_base64(IMGS_PATH / "contentBg.jpg"),
        "roleBgB64": image_to_base64(IMGS_PATH / "roleBg.png"),
        "charFashions": char_fashions,
        "charRate": char_fashion.rate if char_fashion else "0",
        "weaponFashions": weapon_fashions,
        "weaponRate": weapon_fashion.rate if weapon_fashion else "0",
    }

    if not PLAYWRIGHT_AVAILABLE:
        if not WutheringWavesConfig.get_config("RemoteRenderEnable").data:
            return "[战双] Playwright 未安装且未配置外置渲染"

    img = await render_html(pgr_fashion_templates, "pgr_fashion.html", context)
    if img:
        return img
    return "[战双] 渲染涂装列表失败"
