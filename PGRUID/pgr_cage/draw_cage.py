"""战双幻痛囚笼

请求 prisonerCage，下载 Boss/角色图标，准备渲染上下文
"""
import asyncio
from pathlib import Path
from typing import Dict, List, Union

from gsuid_core.logger import logger

from ..utils.api.requests import pgr_api
from ..utils.image import pic_download_from_url
from ..utils.path import ROLE_ICON_PATH, FASHION_PATH
from ..pgr_config import PREFIX

from XutheringWavesUID.XutheringWavesUID.utils.render_utils import (
    PLAYWRIGHT_AVAILABLE,
    render_html,
    image_to_base64,
)
from XutheringWavesUID.XutheringWavesUID.utils.image import get_event_avatar, pil_to_b64

IMGS_PATH = Path(__file__).parent / "imgs"

# Boss 图标缓存目录
from ..pgr_roleinfo.draw_roleinfo import _get_grade_info

BOSS_ICON_PATH = FASHION_PATH


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


async def draw_cage_img(ev, uid: str) -> Union[bytes, str]:
    user_id = ev.user_id
    bot_id = ev.bot_id

    ck = await pgr_api.get_self_pgr_ck(uid, user_id, bot_id)
    if not ck:
        return f"[战双] token 已失效，请使用【{PREFIX}登录】重新绑定！"

    cage_data, account = await asyncio.gather(
        pgr_api.get_prisoner_cage(uid, ck),
        pgr_api.get_account_data(uid, ck),
    )

    if not cage_data:
        return "[战双] 获取幻痛囚笼数据失败"
    if not cage_data.prisonerCage or not cage_data.challengeArea:
        return "[战双] 幻痛囚笼暂无数据"

    cage = cage_data.prisonerCage

    # 收集所有需要下载的 URL
    download_tasks = []
    raw = cage_data.model_dump()
    pc = raw.get("prisonerCage", {})
    for boss_fight in pc.get("bossFightInfoList", []):
        boss = boss_fight.get("boss", {})
        if boss.get("iconUrl"):
            download_tasks.append(_download(BOSS_ICON_PATH, boss["iconUrl"]))
        for weakness in boss.get("weaknessList", []):
            if weakness.get("icon"):
                download_tasks.append(_download(FASHION_PATH, weakness["icon"]))
        for stage in (boss_fight.get("stageInfoList") or []):
            for body_item in stage.get("bodyList", []):
                body_info = body_item.get("bodyInfo", {})
                body = body_info.get("body", {})
                if body.get("iconUrl"):
                    download_tasks.append(_download(ROLE_ICON_PATH, body["iconUrl"]))

    if download_tasks:
        await asyncio.gather(*download_tasks)

    # 用户头像
    avatar_img = await get_event_avatar(ev, size=200)
    head_b64 = pil_to_b64(avatar_img, quality=75) if avatar_img else ""

    # 构建 Boss 列表上下文
    bosses = []
    for boss_fight in pc.get("bossFightInfoList", []):
        boss = boss_fight.get("boss", {})
        boss_icon_b64 = _local_b64(BOSS_ICON_PATH, boss.get("iconUrl", ""))

        # 弱点图标
        weaknesses = []
        for w in boss.get("weaknessList", []):
            weaknesses.append({
                "name": w.get("name", ""),
                "iconB64": _local_b64(FASHION_PATH, w.get("icon", "")),
            })

        # 关卡（骑士/勇士/指挥官等）
        stages = []
        for stage in (boss_fight.get("stageInfoList") or []):
            # 编队角色
            team = []
            for body_item in stage.get("bodyList", []):
                body_info = body_item.get("bodyInfo", {})
                body = body_info.get("body", {})
                grade = body_info.get("grade", "")
                gi = _get_grade_info(grade)
                team.append({
                    "bodyName": body.get("bodyName", ""),
                    "roleName": body.get("roleName", ""),
                    "iconB64": _local_b64(ROLE_ICON_PATH, body.get("iconUrl", "")),
                    "grade": grade,
                    "gradeClass": gi["gradeClass"],
                    "gradeDisplay": gi["gradeDisplay"],
                    "isPlus": gi["isPlus"],
                    "element": body.get("element", ""),
                })

            stages.append({
                "stageName": stage.get("stageName", ""),
                "point": stage.get("point", 0),
                "fightTime": stage.get("fightTime", 0),
                "autoFight": stage.get("autoFight", False),
                "team": team,
            })

        bosses.append({
            "name": boss.get("name", ""),
            "iconB64": boss_icon_b64,
            "totalPoint": boss_fight.get("totalPoint", 0),
            "totalNum": boss_fight.get("totalNum", 0),
            "weaknesses": weaknesses,
            "stages": stages,
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
        "areaIconB64": image_to_base64(IMGS_PATH / "area-level4.png") if cage_data.challengeLevel == "80 - 120" else "",
        "challengeArea": cage_data.challengeArea,
        "challengeLevel": cage_data.challengeLevel,
        "totalPoint": cage.totalPoint or 0,
        "totalChallengeTimes": cage.totalChallengeTimes or 0,
        "bosses": bosses,
    }

    if not PLAYWRIGHT_AVAILABLE:
        if not WutheringWavesConfig.get_config("RemoteRenderEnable").data:
            return "[战双] Playwright 未安装且未配置外置渲染"

    from jinja2 import Environment, FileSystemLoader
    _TEMPLATE_DIR = Path(__file__).parent
    pgr_cage_templates = Environment(loader=FileSystemLoader([str(_TEMPLATE_DIR)]))
    img = await render_html(pgr_cage_templates, "pgr_cage.html", context)
    if img:
        return img
    return "[战双] 渲染幻痛囚笼失败"
