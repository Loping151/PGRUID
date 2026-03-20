"""战双诺曼复兴战"""
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
pgr_stronghold_templates = Environment(loader=FileSystemLoader([str(_TEMPLATE_DIR)]))


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


async def _download(path: Path, url: str):
    if url:
        try:
            await pic_download_from_url(path, url)
        except Exception:
            pass


async def draw_stronghold_img(ev, uid: str) -> Union[bytes, str]:
    user_id = ev.user_id
    bot_id = ev.bot_id

    ck = await pgr_api.get_self_pgr_ck(uid, user_id, bot_id)
    if not ck:
        return f"[战双] token 已失效，请使用【{PREFIX}登录】重新绑定！"

    stronghold_data, account = await asyncio.gather(
        pgr_api.get_stronghold(uid, ck),
        pgr_api.get_account_data(uid, ck),
    )

    if not stronghold_data:
        return "[战双] 获取诺曼复兴战数据失败"
    if not stronghold_data.isUnlock:
        return "[战双] 诺曼复兴战未解锁"

    raw = stronghold_data.model_dump()

    # 收集下载任务
    download_tasks = []
    for team in raw.get("teamList", []):
        elem = team.get("element") or {}
        if elem.get("iconUrl"):
            download_tasks.append(_download(FASHION_PATH, elem["iconUrl"]))
        rune = team.get("rune") or {}
        if rune.get("iconUrl"):
            download_tasks.append(_download(FASHION_PATH, rune["iconUrl"]))
        sub_rune = team.get("subRune") or {}
        if sub_rune.get("iconUrl"):
            download_tasks.append(_download(FASHION_PATH, sub_rune["iconUrl"]))
        for char in (team.get("characterList") or []):
            if char.get("iconUrl"):
                download_tasks.append(_download(ROLE_ICON_PATH, char["iconUrl"]))
    # buff icons
    for group in raw.get("groupList", []):
        for bl in (group.get("buffList") or []):
            buff = bl.get("buff") or {}
            if buff.get("iconUrl"):
                download_tasks.append(_download(FASHION_PATH, buff["iconUrl"]))

    if download_tasks:
        await asyncio.gather(*download_tasks, return_exceptions=True)

    # 用户头像
    avatar_img = await get_event_avatar(ev, size=200)
    head_b64 = pil_to_b64(avatar_img, quality=75) if avatar_img else ""

    # 矿区列表
    groups = []
    for g in raw.get("groupList", []):
        buffs = []
        for bl in (g.get("buffList") or []):
            buff = bl.get("buff") or {}
            buffs.append({
                "name": buff.get("name", ""),
                "iconB64": _local_b64(FASHION_PATH, buff.get("iconUrl", "")),
                "isComplete": bl.get("isComplete", False),
            })
        groups.append({
            "groupName": g.get("groupName", ""),
            "pass": g.get("pass", False),
            "completeBuffNum": g.get("completeBuffNum", 0),
            "buffs": buffs,
        })

    # 预设队伍
    teams = []
    for team in raw.get("teamList", []):
        elem = team.get("element") or {}
        rune = team.get("rune") or {}
        sub_rune = team.get("subRune") or {}

        chars = []
        for char in (team.get("characterList") or []):
            grade = char.get("grade", "")
            gi = _get_grade_info(grade)
            chars.append({
                "bodyName": char.get("bodyName", ""),
                "iconB64": _local_b64(ROLE_ICON_PATH, char.get("iconUrl", "")),
                "grade": grade,
                "gradeClass": gi["gradeClass"],
                "gradeDisplay": gi["gradeDisplay"],
                "isPlus": gi["isPlus"],
                "fightAbility": char.get("fightAbility", 0),
            })

        teams.append({
            "elementName": elem.get("name", ""),
            "elementIconB64": _local_b64(FASHION_PATH, elem.get("iconUrl", "")),
            "electricNum": team.get("electricNum", 0),
            "runeName": rune.get("name", ""),
            "runeIconB64": _local_b64(FASHION_PATH, rune.get("iconUrl", "")),
            "subRuneName": sub_rune.get("name", ""),
            "subRuneIconB64": _local_b64(FASHION_PATH, sub_rune.get("iconUrl", "")),
            "characters": chars,
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
        "levelIconB64": image_to_base64(IMGS_PATH / "revive-icon2.png"),
        "batteryIconB64": image_to_base64(IMGS_PATH / "batteryIcon.png"),
        "challengeArea": stronghold_data.challengeArea,
        "challengeLevel": stronghold_data.challengeLevel,
        "groups": groups,
        "teams": teams,
    }

    if not PLAYWRIGHT_AVAILABLE:
        from ..pgr_config.config_default import PGRConfig
        if not PGRConfig.get_config("RemoteRenderEnable").data:
            return "[战双] Playwright 未安装且未配置外置渲染"

    img = await render_html(pgr_stronghold_templates, "pgr_stronghold.html", context)
    if img:
        return img
    return "[战双] 渲染诺曼复兴战失败"
