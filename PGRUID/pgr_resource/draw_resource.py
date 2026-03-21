"""战双资源看板

请求 halfOfYear，渲染半年资源收入看板
"""
from pathlib import Path
from typing import Union

from gsuid_core.logger import logger
from XutheringWavesUID.XutheringWavesUID.utils.at_help import ruser_id

from ..utils.api.requests import pgr_api
from ..pgr_config import PREFIX

from XutheringWavesUID.XutheringWavesUID.utils.render_utils import (
    PLAYWRIGHT_AVAILABLE,
    render_html,
    image_to_base64,
)
from XutheringWavesUID.XutheringWavesUID.utils.image import get_event_avatar, get_qq_avatar, pil_to_b64
from jinja2 import Environment, FileSystemLoader

IMGS_PATH = Path(__file__).parent / "imgs"
_TEMPLATE_DIR = Path(__file__).parent
pgr_resource_templates = Environment(loader=FileSystemLoader([str(_TEMPLATE_DIR)]))


async def draw_resource_img(ev, uid: str) -> Union[bytes, str]:
    user_id = ruser_id(ev)
    bot_id = ev.bot_id

    ck = await pgr_api.get_self_pgr_ck(uid, user_id, bot_id)
    if not ck:
        return f"[战双] token 已失效，请使用【{PREFIX}登录】重新绑定！"

    import asyncio
    half_year, account = await asyncio.gather(
        pgr_api.get_half_year_data(uid, ck),
        pgr_api.get_account_data(uid, ck),
    )

    if not half_year:
        return "[战双] 获取资源数据失败"

    # 用户头像
    avatar_img = None
    if ev.bot_id == "onebot":
        avatar_img = await get_qq_avatar(user_id, size=640)
    if avatar_img is None:
        avatar_img = await get_event_avatar(ev)
    head_b64 = pil_to_b64(avatar_img, quality=75) if avatar_img else ""

    # 本地素材
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
        "topBannerB64": image_to_base64(IMGS_PATH / "halfyearIcons.png"),
        "bgB64": image_to_base64(IMGS_PATH / "bg.png"),
        "shadowB64": image_to_base64(IMGS_PATH / "halfyearShadow.png"),
        "card1B64": image_to_base64(IMGS_PATH / "smallIcon1.png"),
        "card2B64": image_to_base64(IMGS_PATH / "smallIcon2.png"),
        "card3B64": image_to_base64(IMGS_PATH / "smallIcon3.png"),
        "totalBlackCard": half_year.totalBlackCard,
        "totalDevelopResource": half_year.totalDevelopResource,
        "totalTradeCredit": half_year.totalTradeCredit,
        "months": [],
    }

    for m in (half_year.perMonthList or []):
        context["months"].append({
            "month": m.month,
            "blackCard": m.monthBlackCard,
            "developResource": m.monthDevelopResource,
            "tradeCredit": m.monthTradeCredit,
            "isHighest": m.isHighest,
        })

    if not PLAYWRIGHT_AVAILABLE:
        if not WutheringWavesConfig.get_config("RemoteRenderEnable").data:
            return "[战双] Playwright 未安装且未配置外置渲染"

    img = await render_html(pgr_resource_templates, "pgr_resource.html", context)
    if img:
        return img
    return "[战双] 渲染资源看板失败"
