"""战双单角色面板绘制

请求 roleDetail，下载所有 URL 资源并缓存，保存玩家数据（过滤 URL），准备渲染上下文
"""
import json
import asyncio
from pathlib import Path
from typing import Dict, Union, Any

from gsuid_core.logger import logger

from ..utils.api.requests import pgr_api
from ..utils.image import pic_download_from_url
from ..utils.path import (
    ROLE_ICON_PATH,
    ROLE_PILE_PATH,
    FASHION_PATH,
    WEAPON_FASHION_PATH,
    PLAYER_PATH,
)
from jinja2 import Environment, FileSystemLoader
from ..utils.name_convert import get_body_name_by_id
from ..pgr_config import PREFIX

# 复用 xwuid 的渲染工具
from XutheringWavesUID.XutheringWavesUID.utils.render_utils import (
    PLAYWRIGHT_AVAILABLE,
    render_html,
    image_to_base64,
)


# ===== URL 资源下载 =====

async def _download_url(path: Path, url: str, save_name: str = ""):
    """下载 URL 资源到指定目录（带缓存）"""
    if not url:
        return
    try:
        await pic_download_from_url(path, url, save_name=save_name)
    except Exception as e:
        logger.warning(f"[PGR] 下载资源失败: {url}, {e}")


async def _download_all_urls(detail_data: dict):
    """并发下载角色详情中的所有 URL 资源"""
    tasks = []
    char = detail_data.get("character", {})
    if not char:
        return

    # 角色立绘（用 bodyId 命名）
    body = char.get("body", {})
    body_id = str(body.get("bodyId", "")) if body else ""
    if body:
        if body.get("iconUrl"):
            tasks.append(_download_url(ROLE_ICON_PATH, body["iconUrl"], save_name=body_id))
        if body.get("imgUrl"):
            tasks.append(_download_url(ROLE_PILE_PATH, body["imgUrl"], save_name=body_id))

    # 武器
    weapon_info = char.get("weaponInfo", {})
    if weapon_info:
        weapon = weapon_info.get("weapon", {})
        if weapon and weapon.get("iconUrl"):
            tasks.append(_download_url(WEAPON_FASHION_PATH, weapon["iconUrl"]))
        suit = weapon_info.get("suit", {})
        if suit and suit.get("iconUrl"):
            tasks.append(_download_url(WEAPON_FASHION_PATH, suit["iconUrl"]))
        for res in weapon_info.get("resonanceList", []):
            if res.get("iconUrl"):
                tasks.append(_download_url(WEAPON_FASHION_PATH, res["iconUrl"]))

    # 辅助机
    partner = char.get("partner", {})
    if partner:
        p = partner.get("partner", {})
        if p and p.get("iconUrl"):
            tasks.append(_download_url(FASHION_PATH, p["iconUrl"]))
        for skill in partner.get("skillList", []):
            if skill.get("iconUrl"):
                tasks.append(_download_url(FASHION_PATH, skill["iconUrl"]))

    # 芯片套装
    for chip_suit in char.get("chipSuitList", []):
        if chip_suit.get("iconUrl"):
            tasks.append(_download_url(FASHION_PATH, chip_suit["iconUrl"]))

    # 芯片共鸣
    for chip_res in char.get("chipResonanceList", []):
        for key in ("chipIconUrl", "superSlotIconUrl", "subSlotIconUrl"):
            url = chip_res.get(key)
            if url:
                tasks.append(_download_url(FASHION_PATH, url))

    if tasks:
        await asyncio.gather(*tasks)


# ===== 玩家数据保存（过滤 URL）=====

def _filter_urls(obj: Any) -> Any:
    """递归过滤掉所有 URL 字段，只保留非 URL 数据"""
    if isinstance(obj, dict):
        return {
            k: _filter_urls(v)
            for k, v in obj.items()
            if not (isinstance(v, str) and (v.startswith("http://") or v.startswith("https://")))
        }
    elif isinstance(obj, list):
        return [_filter_urls(item) for item in obj]
    return obj


def _save_player_data(uid: str, body_id: int, raw_data: dict):
    """保存角色详情到玩家目录（过滤 URL）"""
    player_dir = PLAYER_PATH / uid
    player_dir.mkdir(parents=True, exist_ok=True)

    filtered = _filter_urls(raw_data)
    path = player_dir / f"{body_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)


def _load_player_data(uid: str, body_id: int) -> dict:
    """加载玩家角色数据"""
    path = PLAYER_PATH / uid / f"{body_id}.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ===== 本地资源 b64 =====

def _local_b64(cache_dir: Path, url: str, save_name: str = "") -> str:
    """从本地缓存获取资源的 base64，优先按 save_name 查找"""
    if not url and not save_name:
        return ""
    # 优先按 save_name 查找
    if save_name:
        webp = cache_dir / f"{save_name}.webp"
        if webp.exists():
            return image_to_base64(webp)
    # 回退按 URL 文件名查找
    if url:
        filename = url.split("/")[-1]
        webp_path = cache_dir / Path(filename).with_suffix(".webp")
        orig_path = cache_dir / filename
        if webp_path.exists():
            return image_to_base64(webp_path)
        if orig_path.exists():
            return image_to_base64(orig_path)
    return ""


# ===== 主函数 =====

async def draw_char_card(
    ev, uid: str, body_id: int, use_cache: bool = True
) -> Union[bytes, str]:
    from gsuid_core.models import Event
    user_id = ev.user_id
    bot_id = ev.bot_id

    body_name = get_body_name_by_id(body_id)
    raw_data = None

    if use_cache:
        # 优先从本地缓存读取
        raw_data = _load_player_data(uid, body_id)
        if not raw_data:
            return f"[战双] 未找到「{body_name}」的面板数据，请先使用【{PREFIX}刷新{body_name}面板】"

    if not raw_data:
        # 实时请求
        ck = await pgr_api.get_self_pgr_ck(uid, user_id, bot_id)
        if not ck:
            return f"[战双] token 已失效，请使用【{PREFIX}登录】重新绑定！"

        import asyncio
        detail, account_data = await asyncio.gather(
            pgr_api.get_role_detail(uid, ck, body_id),
            pgr_api.get_account_data(uid, ck),
        )

        if not detail or not detail.character:
            return f"[战双] 获取「{body_name}」面板失败，请检查库街区数据是否公开"

        raw_data = detail.model_dump()
        await _download_all_urls(raw_data)
        _save_player_data(uid, body_id, raw_data)

        # 把 account 也缓存一份
        if account_data:
            account_path = PLAYER_PATH / uid / "_account.json"
            account_path.parent.mkdir(parents=True, exist_ok=True)
            with open(account_path, "w", encoding="utf-8") as f:
                json.dump(_filter_urls(account_data.model_dump()), f, ensure_ascii=False, indent=2)

    # 从 raw_data 重建 model
    from ..utils.api.model import PGRRoleDetailData, PGRAccountData
    detail = PGRRoleDetailData.model_validate(raw_data)
    if not detail.character:
        return f"[战双] 「{body_name}」面板数据异常"

    char = detail.character
    body = char.body

    # 账号信息（优先从刚请求的，否则从缓存读）
    account = None
    if not use_cache:
        account = account_data  # noqa: F821
    if not account:
        account_cache = PLAYER_PATH / uid / "_account.json"
        if account_cache.exists():
            try:
                with open(account_cache, "r", encoding="utf-8") as f:
                    account = PGRAccountData.model_validate(json.load(f))
            except Exception:
                pass

    # 用户头像
    from XutheringWavesUID.XutheringWavesUID.utils.image import get_event_avatar, pil_to_b64
    avatar_img = await get_event_avatar(ev, size=200)
    head_b64 = pil_to_b64(avatar_img, quality=75) if avatar_img else ""

    # 准备渲染上下文
    bid = str(body.bodyId) if body else ""
    body_b64 = _local_b64(ROLE_PILE_PATH, body.imgUrl, save_name=bid) if body else ""
    icon_b64 = _local_b64(ROLE_ICON_PATH, body.iconUrl, save_name=bid) if body else ""

    # 武器
    weapon_b64 = ""
    suit_b64 = ""
    resonance_b64s = []
    if char.weaponInfo:
        if char.weaponInfo.weapon:
            weapon_b64 = _local_b64(WEAPON_FASHION_PATH, char.weaponInfo.weapon.iconUrl)
        if char.weaponInfo.suit:
            suit_b64 = _local_b64(WEAPON_FASHION_PATH, char.weaponInfo.suit.iconUrl)
        for res in char.weaponInfo.resonanceList:
            resonance_b64s.append({
                "name": res.name,
                "iconB64": _local_b64(WEAPON_FASHION_PATH, res.iconUrl),
                "description": res.skillDescription,
            })

    # 辅助机
    partner_b64 = ""
    partner_skills = []
    if char.partner:
        if char.partner.partner:
            partner_b64 = _local_b64(FASHION_PATH, char.partner.partner.iconUrl)
        for skill in char.partner.skillList:
            partner_skills.append({
                "name": skill.name,
                "iconB64": _local_b64(FASHION_PATH, skill.iconUrl),
                "level": skill.level,
                "description": skill.description,
            })

    # 芯片套装
    chip_suits = []
    for cs in char.chipSuitList:
        chip_suits.append({
            "name": cs.name,
            "iconB64": _local_b64(FASHION_PATH, cs.iconUrl),
            "num": cs.num,
            "desc2": cs.descriptionTwo,
            "desc4": cs.descriptionFour,
            "desc6": cs.descriptionSix or "",
        })

    # 芯片共鸣
    chip_resonances = []
    for cr in char.chipResonanceList:
        chip_resonances.append({
            "site": cr.site,
            "chipName": cr.chipName,
            "chipIconB64": _local_b64(FASHION_PATH, cr.chipIconUrl),
            "defend": cr.defend,
            "superIconB64": _local_b64(FASHION_PATH, cr.superSlotIconUrl),
            "superAwake": cr.superAwake,
            "superDesc": cr.superDescription,
            "subIconB64": _local_b64(FASHION_PATH, cr.subSlotIconUrl),
            "subAwake": cr.subAwake,
            "subDesc": cr.subDescription,
        })

    context = {
        "body": {
            "bodyId": body.bodyId if body else 0,
            "roleName": body.roleName if body else "",
            "bodyName": body.bodyName if body else "",
            "career": body.career if body else "",
            "element": body.element if body else "",
            "elementDetail": body.elementDetail if body else "",
            "effect": body.effect if body else "",
            "roleRank": body.roleRank if body else "",
            "iconB64": icon_b64,
            "imgB64": body_b64,
        },
        "quality": char.quality or 0,
        "grade": char.grade or "",
        "fightAbility": char.fightAbility or 0,
        "chipExDamage": char.chipExDamage or "",
        "weapon": {
            "name": char.weaponInfo.weapon.name if char.weaponInfo and char.weaponInfo.weapon else "",
            "iconB64": weapon_b64,
            "overRunLevel": char.weaponInfo.overRunLevel if char.weaponInfo else 0,
            "quality": char.weaponInfo.quality if char.weaponInfo else 0,
            "skillName": char.weaponInfo.weapon.skillName if char.weaponInfo and char.weaponInfo.weapon else "",
            "skillDesc": char.weaponInfo.weapon.skillDescription if char.weaponInfo and char.weaponInfo.weapon else "",
            "suitName": char.weaponInfo.suit.name if char.weaponInfo and char.weaponInfo.suit else "",
            "suitIconB64": suit_b64,
            "suitDesc2": char.weaponInfo.suit.skillDescriptionTwo if char.weaponInfo and char.weaponInfo.suit else "",
            "suitDesc4": char.weaponInfo.suit.skillDescriptionFour if char.weaponInfo and char.weaponInfo.suit else "",
            "resonances": resonance_b64s,
        },
        "partner": {
            "name": char.partner.partner.name if char.partner and char.partner.partner else "",
            "iconB64": partner_b64,
            "level": char.partner.level if char.partner else 0,
            "grade": char.partner.grade if char.partner else "",
            "quality": char.partner.quality if char.partner else 0,
            "skills": partner_skills,
        },
        "chipSuits": chip_suits,
        "chipResonances": chip_resonances,
        "uid": uid,
    }

    # 账号信息 + 头像
    context["account"] = {
        "roleId": account.roleId if account else uid,
        "level": account.level if account else 0,
        "roleName": account.roleName if account else uid,
        "serverName": account.serverName if account else "",
        "rank": account.rank if account else 0,
        "headB64": head_b64,
    }

    # 加载本地素材
    CHAR_IMGS = Path(__file__).parent / "imgs"
    context["contentBgB64"] = image_to_base64(CHAR_IMGS / "contentBg.jpg")
    context["titleBgB64"] = image_to_base64(CHAR_IMGS / "titleBg.png")
    context["headerBgB64"] = image_to_base64(CHAR_IMGS / "head.png")
    context["avatarBoxB64"] = image_to_base64(CHAR_IMGS / "avatorBoxIcon.png")

    # 元素图标
    elem_icons = {}
    for e in (body.element or "").split(","):
        e = e.strip()
        if e:
            p = CHAR_IMGS / f"{e}.png"
            if p.exists():
                elem_icons[e] = image_to_base64(p)
    if body and body.effect:
        p = CHAR_IMGS / f"{body.effect}.png"
        if p.exists():
            elem_icons[body.effect] = image_to_base64(p)
    context["elemIcons"] = elem_icons

    # 品级渐变 class
    from ..pgr_roleinfo.draw_roleinfo import _get_grade_info
    context["gradeInfo"] = _get_grade_info(char.grade or "")

    # 星级
    context["stars"] = "★" * (char.quality or 0)

    if not PLAYWRIGHT_AVAILABLE:
        if not WutheringWavesConfig.get_config("RemoteRenderEnable").data:
            return "[战双] Playwright 未安装且未配置外置渲染"

    _TEMPLATE_DIR = Path(__file__).parent
    pgr_char_templates = Environment(loader=FileSystemLoader([str(_TEMPLATE_DIR)]))
    img = await render_html(pgr_char_templates, "pgr_char_card.html", context)
    if img:
        return img
    return f"[战双] 「{body.bodyName if body else ''}」渲染失败"
