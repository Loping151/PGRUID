"""战双卡片绘制

请求 accountData + baseData + roleIndex，下载角色图标，维护 full_body.json，通过 HTML 模板渲染
"""
import json
import asyncio
from pathlib import Path
from typing import Dict, Union

from gsuid_core.logger import logger
from gsuid_core.models import Event

from ..utils.api.requests import pgr_api
from ..utils.path import ROLE_ICON_PATH
from ..utils.name_convert import update_full_body
from ..pgr_config import PREFIX

# 复用 xwuid 的渲染工具
from XutheringWavesUID.XutheringWavesUID.utils.render_utils import (
    PLAYWRIGHT_AVAILABLE,
    render_html,
    image_to_base64,
)
from jinja2 import Environment, FileSystemLoader

# 本地素材和模板路径
IMGS_PATH = Path(__file__).parent / "imgs"
_TEMPLATE_DIR = Path(__file__).parent
pgr_templates = Environment(loader=FileSystemLoader([str(_TEMPLATE_DIR)]))

def _local_icon_b64(cache_dir: Path, url: str, save_name: str = "") -> str:
    """从本地缓存目录获取图标的 base64（优先按 save_name，再按 URL 文件名）"""
    if not url and not save_name:
        return ""
    if save_name:
        webp = cache_dir / f"{save_name}.webp"
        if webp.exists():
            return image_to_base64(webp)
    if url:
        filename = url.split("/")[-1]
        webp_path = cache_dir / Path(filename).with_suffix(".webp")
        orig_path = cache_dir / filename
        if webp_path.exists():
            return image_to_base64(webp_path)
        if orig_path.exists():
            return image_to_base64(orig_path)
    return ""


QUALITY_COLORS = {
    6: "#e8a642",
    5: "#c266e5",
    4: "#4da6ff",
    3: "#66cc66",
}


def _get_grade_info(grade: str) -> dict:
    """根据品级返回 CSS class、显示文本、是否有加号"""
    is_plus = grade.endswith("+")
    # SSS+ / SSS / SSSx
    if grade.startswith("SSS"):
        if is_plus:
            return {"gradeClass": "grade-sss-plus", "gradeDisplay": "SSS", "isPlus": True}
        return {"gradeClass": "grade-sss", "gradeDisplay": grade, "isPlus": False}
    # SS / SSx / S
    if grade.startswith("SS") or grade == "S":
        return {"gradeClass": "grade-ss", "gradeDisplay": grade, "isPlus": False}
    return {"gradeClass": "grade-ss", "gradeDisplay": grade, "isPlus": False}




async def draw_roleinfo_img(
    ev: Event, uid: str
) -> Union[bytes, str]:
    user_id = ev.user_id
    bot_id = ev.bot_id
    ck = await pgr_api.get_self_pgr_ck(uid, user_id, bot_id)
    if not ck:
        return f"[战双] 您的token已失效，请使用【{PREFIX}登录】重新绑定！"

    # 并发请求三个接口
    account, base, role_index = await asyncio.gather(
        pgr_api.get_account_data(uid, ck),
        pgr_api.get_base_data(uid, ck),
        pgr_api.get_role_index(uid, ck),
    )

    if not account:
        return "[战双] 获取账号信息失败，请检查库街区数据是否公开"
    if not base:
        return "[战双] 获取基础信息失败"
    if not role_index:
        return "[战双] 获取角色列表失败"

    # 更新 full_body.json + 下载图标
    await update_full_body(role_index)

    # 用户头像（从 QQ/平台获取，和 xwuid 一致）
    from XutheringWavesUID.XutheringWavesUID.utils.image import get_event_avatar, pil_to_b64
    avatar_img = await get_event_avatar(ev, size=200)
    head_b64 = pil_to_b64(avatar_img, quality=75) if avatar_img else ""

    # 本地素材 b64
    content_bg_b64 = image_to_base64(IMGS_PATH / "contentBg.jpg")
    head_bg_b64 = image_to_base64(IMGS_PATH / "head.png")
    role_bg_b64 = image_to_base64(IMGS_PATH / "roleBg.png")
    avatar_box_b64 = image_to_base64(IMGS_PATH / "avatorBoxIcon.png")
    title_bg_b64 = image_to_base64(IMGS_PATH / "titleBg.png")

    # 1-角色数量 2-涂装 3-总评分 4-剧情 5-补给箱 6-成就数 7-藏品数 8-活跃天数
    stats = [
        {"label": "角色数量", "value": str(base.characterCount), "bgB64": image_to_base64(IMGS_PATH / "profile_bg1.jpg")},
        {"label": "涂装收集", "value": base.fashionProcess, "bgB64": image_to_base64(IMGS_PATH / "profile_bg2.jpg")},
        {"label": "总评分", "value": str(base.roleAllScore), "bgB64": image_to_base64(IMGS_PATH / "profile_bg3.jpg")},
        {"label": "剧情进度", "value": base.storyProcess, "bgB64": image_to_base64(IMGS_PATH / "profile_bg4.jpg")},
        {"label": "补给箱", "value": f"{base.sgTreasureBoxCount}/{base.sgTreasureBoxTotalCount}", "bgB64": image_to_base64(IMGS_PATH / "profile_bg5.jpg")},
        {"label": "成就数", "value": str(base.achievement), "bgB64": image_to_base64(IMGS_PATH / "profile_bg6.png")},
        {"label": "藏品数", "value": str(base.scoreTitleCount), "bgB64": image_to_base64(IMGS_PATH / "profile_bg7.png")},
        {"label": "活跃天数", "value": str(base.grandTotalLoginNum), "bgB64": image_to_base64(IMGS_PATH / "profile_bg8.png")},
    ]

    # 预加载本地元素图标 b64（去重）
    element_b64_cache: Dict[str, str] = {}
    all_elements = set()
    for char in role_index.characterList:
        for e in (char.element or "").split(","):
            e = e.strip()
            if e:
                all_elements.add(e)
        if char.effect:
            all_elements.add(char.effect)
    for elem in all_elements:
        icon_path = IMGS_PATH / f"{elem}.png"
        if icon_path.exists():
            element_b64_cache[elem] = image_to_base64(icon_path)

    # 角色列表（已按 fightAbility 降序排列）
    characters = []
    for char in role_index.characterList:
        icon_b64 = _local_icon_b64(ROLE_ICON_PATH, char.iconUrl, save_name=str(char.bodyId))

        quality = char.quality or 0
        grade_info = _get_grade_info(char.grade or "")

        # 解析元素列表
        elem_list = []
        for e in (char.element or "").split(","):
            e = e.strip()
            if e:
                elem_list.append({"name": e, "iconB64": element_b64_cache.get(e, "")})
        # effect 也作为属性图标
        if char.effect and char.effect not in [e["name"] for e in elem_list]:
            elem_list.append({"name": char.effect, "iconB64": element_b64_cache.get(char.effect, "")})

        characters.append({
            "bodyId": char.bodyId,
            "bodyName": char.bodyName or "",
            "iconB64": icon_b64,
            "elements": elem_list,
            "effect": char.effect or "",
            "quality": quality,
            "qualityColor": QUALITY_COLORS.get(quality, "#888888"),
            "grade": char.grade or "",
            "gradeClass": grade_info["gradeClass"],
            "gradeDisplay": grade_info["gradeDisplay"],
            "isPlus": grade_info["isPlus"],
            "fightAbility": char.fightAbility or 0,
            "level": char.level or 0,
            "roleRank": char.roleRank or "",
        })

    context = {
        "account": {
            "roleId": account.roleId,
            "level": account.level,
            "roleName": account.roleName,
            "serverName": account.serverName,
            "headB64": head_b64,
            "rank": account.rank,
        },
        "stats": stats,
        "characters": characters,
        "char_count": len(characters),
        "contentBgB64": content_bg_b64,
        "headBgB64": head_bg_b64,
        "roleBgB64": role_bg_b64,
        "avatarBoxB64": avatar_box_b64,
        "titleBgB64": title_bg_b64,
    }

    if not PLAYWRIGHT_AVAILABLE:
        if not WutheringWavesConfig.get_config("RemoteRenderEnable").data:
            return "[战双] Playwright 未安装且未配置外置渲染"

    img = await render_html(pgr_templates, "pgr_roleinfo.html", context)
    if img:
        return img
    return "[战双] 渲染卡片失败"
