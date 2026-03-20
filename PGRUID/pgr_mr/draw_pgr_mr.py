"""PGR 体力卡片渲染"""
import io
import time
import base64
import asyncio
from typing import Dict, Optional
from pathlib import Path

from PIL import Image

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img

from ..utils.api.model import PGRDailyData, PGRAccountData
from ..utils.api.requests import pgr_api
from ..utils.database.models import PGRUserSettings
from ..utils.path import BAKE_PATH

from gsuid_core.plugins.XutheringWavesUID.XutheringWavesUID.utils.waves_api import waves_api
from gsuid_core.plugins.XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesBind, WavesUser
from gsuid_core.plugins.XutheringWavesUID.XutheringWavesUID.utils.constants import PGR_GAME_ID
from gsuid_core.plugins.XutheringWavesUID.XutheringWavesUID.utils.image import get_event_avatar, pil_to_b64
from gsuid_core.plugins.XutheringWavesUID.XutheringWavesUID.utils.render_utils import render_html, PLAYWRIGHT_AVAILABLE
from gsuid_core.plugins.XutheringWavesUID.XutheringWavesUID.utils.at_help import ruser_id

from jinja2 import Environment, FileSystemLoader

IMGS_PATH = Path(__file__).parent / "imgs"
TEMPLATE_PATH = Path(__file__).parent
pgr_templates = Environment(loader=FileSystemLoader(str(TEMPLATE_PATH)))

based_w = 800


def _img_to_b64(path: Path, quality: int = 0) -> str:
    """本地图片转 base64 data URL"""
    if not path.exists():
        return ""
    if quality > 0:
        img = Image.open(path).convert("RGBA")
        buf = io.BytesIO()
        img.save(buf, "WEBP", quality=quality)
        return f"data:image/webp;base64,{base64.b64encode(buf.getvalue()).decode()}"
    ext = path.suffix.lstrip(".").lower()
    if ext == "jpg":
        ext = "jpeg"
    with open(path, "rb") as f:
        return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"


def _pil_to_b64(img: Image.Image, quality: int = 75) -> str:
    return pil_to_b64(img, quality=quality)


async def _get_pgr_ck(uid: str, user_id: str, bot_id: str) -> Optional[str]:
    """获取 PGR 用户的 cookie"""
    waves_user = await WavesUser.select_waves_user(uid, user_id, bot_id, game_id=PGR_GAME_ID)
    if not waves_user or not waves_user.cookie:
        logger.debug(f"[战双][体力] UID {uid} 未找到 PGR 用户记录(game_id={PGR_GAME_ID})")
        return ""
    if waves_user.status == "无效":
        logger.debug(f"[战双][体力] UID {uid} cookie 已标记无效")
        return ""

    data = await waves_api.login_log(uid, waves_user.cookie)
    if not data.success:
        await data.mark_cookie_invalid(uid, waves_user.cookie)
        logger.debug(f"[战双][体力] UID {uid} login_log 失败: {data.code} {data.msg}")
        return ""

    # 使用 PGR 自己的 refreshData（/haru/roleBox/refreshData）
    data = await pgr_api.refresh_data(uid, waves_user.cookie)
    if not data.success:
        logger.debug(f"[战双][体力] UID {uid} refreshData 失败: {data.code} {data.msg}")
        await data.mark_cookie_invalid(uid, waves_user.cookie)
        return ""

    await WavesUser.update_last_used_time(uid, user_id, bot_id, game_id=PGR_GAME_ID)
    return waves_user.cookie


async def _process_uid(uid: str, ev: Event) -> Optional[Dict]:
    """处理单个 UID 的数据获取"""
    ck = await _get_pgr_ck(uid, ruser_id(ev), ev.bot_id)
    if not ck:
        logger.info(f"[战双][体力] UID {uid} 获取cookie失败，跳过")
        return None

    results = await asyncio.gather(
        pgr_api.get_daily_data(uid, ck),
        pgr_api.get_account_data(uid, ck),
        return_exceptions=True,
    )

    daily_data, account_data = results

    if isinstance(daily_data, Exception):
        logger.warning(f"[战双][体力] UID {uid} get_daily_data 异常: {daily_data}")
        return None
    if isinstance(account_data, Exception):
        logger.warning(f"[战双][体力] UID {uid} get_account_data 异常: {account_data}")
        return None
    if not isinstance(daily_data, PGRDailyData):
        logger.info(f"[战双][体力] UID {uid} daily_data 无效: {type(daily_data)}")
        return None
    if not isinstance(account_data, PGRAccountData):
        logger.info(f"[战双][体力] UID {uid} account_data 无效: {type(account_data)}")
        return None

    logger.info(f"[战双][体力] UID {uid} 数据获取成功: {account_data.roleName} Lv.{account_data.level}")
    return {
        "daily_data": daily_data,
        "account_data": account_data,
        "uid": uid,
    }


def _seconds_to_hm(seconds: int) -> str:
    m, _ = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}时{m:02d}分"


def _format_time_remaining(ts: int) -> tuple[str, bool]:
    """返回 (时间文本, 是否紧急)"""
    now = int(time.time())
    if ts <= now:
        return "已结束", False

    diff = ts - now
    days = diff // 86400
    hours = (diff % 86400) // 3600

    if days > 0:
        return f"{days}天{hours:02d}小时", days <= 1
    return f"{hours}小时", True


async def draw_mr_img(bot: Bot, ev: Event):
    """主入口: 绘制 PGR 体力卡片"""
    try:
        uid_list = await WavesBind.get_uid_list_by_game(ruser_id(ev), ev.bot_id, game_name="pgr")
        if not uid_list:
            return "尚未绑定战双UID，请使用 绑定 命令"

        tasks = [_process_uid(uid, ev) for uid in uid_list]
        results = await asyncio.gather(*tasks)
        valid_list = [r for r in results if r is not None]

        if not valid_list:
            return "未获取到有效数据，请检查登录状态"

        images = []
        for valid in valid_list:
            img = await _draw_single_mr(ev, valid)
            if img:
                images.append(img)

        if not images:
            return "体力卡片渲染失败"

        if len(images) == 1:
            return await convert_img(images[0])

        total_h = sum(img.height for img in images)
        combined = Image.new("RGBA", (based_w, total_h), (0, 0, 0, 0))
        y = 0
        for img in images:
            combined.paste(img, (0, y), img)
            y += img.height
        return await convert_img(combined)

    except Exception:
        logger.exception("[战双][体力]绘图失败")
        return "体力卡片生成失败，请稍后再试"


async def _draw_single_mr(ev: Event, valid: Dict) -> Optional[Image.Image]:
    """绘制单个 UID 的体力卡片"""
    daily: PGRDailyData = valid["daily_data"]
    account: PGRAccountData = valid["account_data"]
    uid: str = valid["uid"]

    # 用户头像（和卡片一致，QQ头像 size=200）
    avatar = await get_event_avatar(ev, size=200)
    head_b64 = _pil_to_b64(avatar, quality=75)

    # 准备图标 b64（和卡片指令一致的素材）
    serum_icon_b64 = _img_to_b64(IMGS_PATH / "serum.png")
    title_bar_b64 = _img_to_b64(IMGS_PATH / "titleBg.png")
    avatar_frame_b64 = _img_to_b64(IMGS_PATH / "avatorBoxIcon.png")
    header_bg_b64 = _img_to_b64(IMGS_PATH / "head.png")
    content_bg_b64 = _img_to_b64(IMGS_PATH / "contentBg.jpg", quality=75)

    # 角色立绘
    import random
    from ..utils.name_convert import resolve_char_name
    from ..utils.path import ROLE_PILE_PATH

    portrait_b64 = ""
    settings = await PGRUserSettings.get_user_settings(ruser_id(ev), ev.bot_id, uid)
    if settings and settings.stamina_bg_value:
        body_id = resolve_char_name(settings.stamina_bg_value)
        if body_id:
            for ext in (".webp", ".png"):
                p = ROLE_PILE_PATH / f"{body_id}{ext}"
                if p.exists():
                    portrait_b64 = _img_to_b64(p, quality=80)
                    break

    # 没设置或找不到 → 从已有立绘中随机
    if not portrait_b64 and ROLE_PILE_PATH.exists():
        candidates = [f for f in ROLE_PILE_PATH.iterdir() if f.suffix in (".webp", ".png")]
        if candidates:
            portrait_b64 = _img_to_b64(random.choice(candidates), quality=80)

    # 血清数据
    action = daily.actionData
    serum_cur = action.cur
    serum_total = action.total if action.total else 240
    serum_percent = min(100, (serum_cur / serum_total * 100)) if serum_total else 0
    serum_urgent = serum_percent > 80

    serum_color = "#ff4d4f" if serum_urgent else "#1c78c8"
    if action.refreshTimeStamp and action.refreshTimeStamp > int(time.time()):
        remain_sec = action.refreshTimeStamp - int(time.time())
        recovery_text = f"恢复时间: {_seconds_to_hm(remain_sec)}"
    elif serum_cur >= serum_total:
        recovery_text = "血清已满！"
        serum_urgent = True
    else:
        recovery_text = "恢复时间: 计算中..."

    # 委托 (dormData)
    dorm = daily.dormData
    comm_done = dorm.cur if dorm else 0
    comm_pending = 0
    if dorm and dorm.status == 1:
        comm_pending = dorm.total - dorm.cur if dorm.total > dorm.cur else 0

    # 活跃度
    active_data = daily.activeData
    active_cur = active_data.cur if active_data else 0
    active_total = active_data.total if active_data else 100
    active_percent = min(100, (active_cur / active_total * 100)) if active_total else 0

    # Boss 任务卡片
    tasks = []
    for boss in daily.bossData:
        if not boss.name:
            continue
        time_text = ""
        urgent = False
        if boss.refreshTimeStamp and boss.refreshTimeStamp > int(time.time()):
            time_text, urgent = _format_time_remaining(boss.refreshTimeStamp)
        elif boss.expireTimeStamp and boss.expireTimeStamp > int(time.time()):
            time_text, urgent = _format_time_remaining(boss.expireTimeStamp)

        done = False
        cur_text = boss.value
        max_text = ""

        if boss.total > 0:
            done = boss.cur >= boss.total
            cur_text = str(boss.cur)
            max_text = f"/{boss.total}"
        elif boss.value:
            cur_text = boss.value
            done = boss.status == 2

        tasks.append({
            "name": boss.name,
            "time_text": time_text,
            "urgent": urgent,
            "cur_text": cur_text,
            "max_text": max_text,
            "done": done,
        })

    context = {
        "user_name": account.roleName or "指挥官",
        "uid": uid,
        "level": account.level,
        "rank": account.rank,
        "server_name": account.serverName or "",
        "avatar_url": head_b64,
        "avatar_frame_url": avatar_frame_b64,
        "header_bg_url": header_bg_b64,
        "content_bg_url": content_bg_b64,
        "title_bar_url": title_bar_b64,
        "portrait_url": portrait_b64,
        "serum_icon_url": serum_icon_b64,
        "serum": {
            "cur": serum_cur,
            "total": serum_total,
            "percent": serum_percent,
            "color": serum_color,
            "recovery_text": recovery_text,
            "urgent": serum_urgent,
        },
        "commission": {
            "done": comm_done,
            "pending": comm_pending,
        },
        "active": {
            "cur": active_cur,
            "total": active_total,
            "percent": active_percent,
        },
        "tasks": tasks,
    }

    if not PLAYWRIGHT_AVAILABLE:
        logger.warning("[战双][体力]Playwright 不可用，无法渲染")
        return None

    try:
        img_bytes = await render_html(pgr_templates, "mr_card.html", context)
        if img_bytes:
            return Image.open(io.BytesIO(img_bytes))
    except Exception:
        logger.exception("[战双][体力]HTML渲染失败")

    return None
