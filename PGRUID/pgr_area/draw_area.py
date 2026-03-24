"""战双纷争战区"""
import asyncio
from pathlib import Path
from typing import Union

from gsuid_core.logger import logger
from XutheringWavesUID.XutheringWavesUID.utils.at_help import ruser_id

from ..utils.api.requests import pgr_api
from ..utils.image import pic_download_from_url
from ..utils.path import ROLE_ICON_PATH, GAMEMODE_PATH
from ..pgr_config import PREFIX
from ..pgr_roleinfo.draw_roleinfo import _get_grade_info

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
pgr_area_templates = Environment(loader=FileSystemLoader([str(_TEMPLATE_DIR)]))


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


async def draw_area_img(ev, uid: str) -> Union[bytes, str]:
    user_id = ruser_id(ev)
    bot_id = ev.bot_id

    _is_self, ck = await pgr_api.get_ck_result(uid, user_id, bot_id)
    if not ck:
        return f"[战双] token 已失效，请使用【{PREFIX}登录】重新绑定！"

    area_data, account = await asyncio.gather(
        pgr_api.get_area(uid, ck),
        pgr_api.get_account_data(uid, ck),
    )

    if not area_data:
        return "[战双] 获取纷争战区数据失败"
    if not area_data.areaInfo or not area_data.groupName:
        return "[战双] 纷争战区暂无数据"

    area = area_data.areaInfo
    raw = area_data.model_dump()
    ai = raw.get("areaInfo") or {}

    # 收集下载任务
    download_tasks = []
    for stage in (ai.get("stageFightInfoList") or []):
        if stage.get("stageIconUrl"):
            download_tasks.append(_download(GAMEMODE_PATH, stage["stageIconUrl"]))
        for buff_fight in (stage.get("areaBuffFightInfoList") or []):
            if buff_fight.get("buffIconUrl"):
                download_tasks.append(_download(GAMEMODE_PATH, buff_fight["buffIconUrl"]))
            for sb in (buff_fight.get("supportBuffList") or []):
                if sb.get("iconUrl"):
                    download_tasks.append(_download(GAMEMODE_PATH, sb["iconUrl"]))
            for body_item in (buff_fight.get("bodyList") or []):
                body = (body_item.get("bodyInfo") or {}).get("body", {})
                if body.get("iconUrl"):
                    download_tasks.append(_download(ROLE_ICON_PATH, body["iconUrl"]))
    if download_tasks:
        await asyncio.gather(*download_tasks)

    # 用户头像
    avatar_img = None
    if ev.bot_id == "onebot":
        avatar_img = await get_qq_avatar(user_id, size=640)
    if avatar_img is None:
        avatar_img = await get_event_avatar(ev)
    head_b64 = pil_to_b64(avatar_img, quality=75) if avatar_img else ""

    # 构建战区列表
    zones = []
    for stage in (ai.get("stageFightInfoList") or []):
        stage_icon_b64 = _local_b64(GAMEMODE_PATH, stage.get("stageIconUrl", ""))

        # 每个 buff 关卡
        buff_fights = []
        for bf in (stage.get("areaBuffFightInfoList") or []):
            # support buff
            support_buffs = []
            for sb in (bf.get("supportBuffList") or []):
                support_buffs.append({
                    "name": sb.get("name", ""),
                    "iconB64": _local_b64(GAMEMODE_PATH, sb.get("iconUrl", "")),
                })

            # 编队
            team = []
            for body_item in (bf.get("bodyList") or []):
                body_info = body_item.get("bodyInfo") or {}
                body = (body_info.get("body") or {})
                grade = body_info.get("grade", "")
                gi = _get_grade_info(grade)
                team.append({
                    "bodyName": body.get("bodyName", ""),
                    "iconB64": _local_b64(ROLE_ICON_PATH, body.get("iconUrl", "")),
                    "gradeClass": gi["gradeClass"],
                    "gradeDisplay": gi["gradeDisplay"],
                    "isPlus": gi["isPlus"],
                })

            buff_fights.append({
                "buffName": bf.get("buffName", ""),
                "buffIconB64": _local_b64(GAMEMODE_PATH, bf.get("buffIconUrl", "")),
                "point": bf.get("point", 0),
                "fightTime": bf.get("fightTime", 0),
                "npcGroup": bf.get("npcGroup", 0),
                "supportBuffs": support_buffs,
                "team": team,
            })

        zones.append({
            "stageName": stage.get("stageName", ""),
            "description": stage.get("description", ""),
            "stageIconB64": stage_icon_b64,
            "point": stage.get("point", 0),
            "npcGroup": stage.get("npcGroup", 0),
            "buffFights": buff_fights,
        })

    context = {
        "account": {
            "roleId": account.roleId if account else uid,
            "level": account.level if account else 0,
            "roleName": (account.roleName if account else None) or "暂无",
            "serverName": (account.serverName if account else None) or "暂无",
            "rank": account.rank if account else 0,
            "rank_label": "勋阶" if (account and account.rank) else "等级",
            "rank_val": account.rank if (account and account.rank) else (account.level if account else 0),
            "headB64": head_b64,
        },
        "headerBgB64": image_to_base64(IMGS_PATH / "head.png"),
        "avatarBoxB64": image_to_base64(IMGS_PATH / "avatorBoxIcon.png"),
        "titleBgB64": image_to_base64(IMGS_PATH / "titleBg.png"),
        "contentBgB64": image_to_base64(IMGS_PATH / "contentBg.jpg"),
        "areaIconB64": image_to_base64(IMGS_PATH / "chuanqi.png") if area_data.groupLevel == "80 - 120" else "",
        "groupName": area_data.groupName,
        "groupLevel": area_data.groupLevel,
        "totalPoint": area.totalPoint or 0,
        "totalChallengeTimes": area.totalChallengeTimes or 0,
        "zones": zones,
    }

    if not PLAYWRIGHT_AVAILABLE:
        if not WutheringWavesConfig.get_config("RemoteRenderEnable").data:
            return "[战双] Playwright 未安装且未配置外置渲染"

    img = await render_html(pgr_area_templates, "pgr_area.html", context)
    if img:
        return img
    return "[战双] 渲染纷争战区失败"
