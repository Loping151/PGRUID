"""PGR 公告卡片渲染

直接复用 XutheringWavesUID 的渲染函数和模板
"""
import time
from typing import List, Union
from datetime import datetime

from gsuid_core.logger import logger

from ..utils.api.requests import pgr_api
from ..pgr_config import PREFIX
from ..pgr_config.config_default import PGRConfig
from ..utils.path import ANN_CACHE_PATH, BAKE_PATH

# 直接从 xwuid 导入渲染工具和模板
from XutheringWavesUID.XutheringWavesUID.utils.render_utils import (
    PLAYWRIGHT_AVAILABLE,
    get_logo_b64,
    get_footer_b64,
    get_image_b64_with_cache,
    render_html,
)
from XutheringWavesUID.XutheringWavesUID.utils.resource.RESOURCE_PATH import (
    waves_templates,
)
from XutheringWavesUID.XutheringWavesUID.utils.image import pic_download_from_url


def format_date(ts) -> str:
    if not ts:
        return ""
    try:
        if isinstance(ts, str):
            ts = int(ts)
        if ts > 1e12:
            ts = ts / 1000
        return datetime.fromtimestamp(ts).strftime("%m-%d")
    except Exception:
        return ""


def format_post_time(post_time: str) -> int:
    try:
        timestamp = datetime.strptime(post_time, "%Y-%m-%d %H:%M").timestamp()
        return int(timestamp)
    except ValueError:
        pass
    try:
        timestamp = datetime.strptime(post_time, "%Y-%m-%d %H:%M:%S").timestamp()
        return int(timestamp)
    except ValueError:
        pass
    return 0


async def ann_list_card() -> bytes:
    use_html_render = PGRConfig.get_config("UseHtmlRender").data
    if not PLAYWRIGHT_AVAILABLE and not PGRConfig.get_config("RemoteRenderEnable").data:
        raise Exception("[PGRUID] Playwright 未安装且未配置外置渲染")
    if not use_html_render:
        raise Exception("[PGRUID] HTML 渲染已关闭")

    ann_list = await pgr_api.get_ann_list()
    if not ann_list:
        raise Exception("获取战双公告失败，请检查接口是否正常")

    grouped = {}
    for item in ann_list:
        t = item.get("eventType")
        if not t:
            continue
        grouped.setdefault(t, []).append(item)

    for data in grouped.values():
        data.sort(key=lambda x: x.get("publishTime", 0), reverse=True)

    CONFIGS = {
        1: {"name": "活动", "color": "#F97316"},
        2: {"name": "资讯", "color": "#3B82F6"},
        3: {"name": "公告", "color": "#10B981"},
    }

    sections = []
    for t in [1, 2, 3]:
        if t not in grouped:
            continue
        section_items = []
        for item in grouped[t][:6]:
            if not item.get("id") or not item.get("postTitle"):
                continue
            cover_url = item.get("coverUrl", "")
            if not cover_url:
                cover_images = item.get("coverImages", [])
                if cover_images:
                    cover_url = cover_images[0].get("url", "")
            if not cover_url:
                video_content = item.get("videoContent", [])
                if video_content:
                    cover_url = video_content[0].get("coverUrl") or video_content[0].get("videoCoverUrl", "")

            cover_b64 = await get_image_b64_with_cache(
                cover_url, ANN_CACHE_PATH, quality=20, cover_size=(400, 200),
            ) if cover_url else ""

            post_id = item.get("postId", "") or str(item.get("id", ""))
            from .utils.post_id_mapper import get_or_create_short_id
            short_id = get_or_create_short_id(post_id)
            date_str = format_date(item.get("publishTime", 0))

            section_items.append({
                "id": str(item.get("id", "")),
                "short_id": short_id,
                "postTitle": item.get("postTitle", ""),
                "date_str": date_str,
                "coverUrl": cover_url,
                "coverB64": cover_b64,
            })

        if section_items:
            sections.append({
                "name": CONFIGS[t]["name"],
                "color": CONFIGS[t]["color"],
                "ann_list": section_items
            })

    subtitle = f"查看详细内容，使用 {PREFIX}公告#ID 查看详情"

    context = {
        "title": "战双公告",
        "subtitle": subtitle,
        "is_list": True,
        "is_user_list": False,
        "sections": sections,
        "logo_b64": get_logo_b64(),
        "footer_b64": get_footer_b64(),
        "user_avatar": "",
        "user_name": "",
        "user_ip_region": "",
    }

    img_bytes = await render_html(waves_templates, "ann_card.html", context)
    if img_bytes:
        return img_bytes
    raise Exception("[PGRUID] 渲染失败")


async def ann_detail_card(
    ann_id: Union[int, str], is_check_time=False
) -> Union[bytes, str, List[bytes]]:
    use_html_render = PGRConfig.get_config("UseHtmlRender").data
    if not PLAYWRIGHT_AVAILABLE and not PGRConfig.get_config("RemoteRenderEnable").data:
        return "Playwright 未安装且未配置外置渲染"
    if not use_html_render:
        return "HTML 渲染已关闭"

    try:
        ann_list = await pgr_api.get_ann_list(True)
        if not ann_list:
            return "获取战双公告失败，请检查接口是否正常"

        if isinstance(ann_id, int):
            content = [x for x in ann_list if x["id"] == ann_id]
        else:
            content = [
                x for x in ann_list
                if str(x.get("postId", "")) == str(ann_id)
                or str(x.get("id", "")) == str(ann_id)
            ]

        if content:
            postId = content[0]["postId"]
        else:
            return "未找到该公告"

        res = await pgr_api.get_ann_detail(postId)
        if not res:
            return "未找到该公告"

        if is_check_time:
            post_time = format_post_time(res["postTime"])
            now_time = int(time.time())
            if post_time < now_time - 86400:
                return "该公告已过期"

        post_content = res["postContent"]

        content_type2_first = [x for x in post_content if x["contentType"] == 2]
        if not content_type2_first and "coverImages" in res:
            _node = res["coverImages"][0]
            _node["contentType"] = 2
            post_content.insert(0, _node)

        if not post_content:
            return "未找到该公告"

        long_image_urls = []
        for item in post_content:
            if item.get("contentType") == 2 and "url" in item:
                img_width = item.get("imgWidth", 0)
                img_height = item.get("imgHeight", 0)
                if img_width > 0 and img_height / img_width > 5:
                    long_image_urls.append(item["url"])

        result_images = []
        if long_image_urls:
            from gsuid_core.utils.image.convert import convert_img
            for img_url in long_image_urls:
                try:
                    img = await pic_download_from_url(ANN_CACHE_PATH, img_url)
                    img_bytes = await convert_img(img)
                    result_images.append(img_bytes)
                except Exception as e:
                    logger.warning(f"[PGRUID] 下载超长图片失败: {img_url}, {e}")

            post_content = [
                item for item in post_content
                if not (item.get("contentType") == 2 and item.get("url") in long_image_urls)
            ]

        processed_content = []
        for item in post_content:
            ctype = item.get("contentType")
            if ctype == 1:
                processed_content.append({
                    "contentType": 1,
                    "content": item.get("content", "")
                })
            elif ctype == 2 and "url" in item:
                img_url = item["url"]
                img_b64 = await get_image_b64_with_cache(img_url, ANN_CACHE_PATH, quality=60)
                processed_content.append({
                    "contentType": 2,
                    "url": img_url,
                    "urlB64": img_b64,
                })
            else:
                cover_url = item.get("coverUrl") or item.get("videoCoverUrl")
                if cover_url:
                    cover_b64 = await get_image_b64_with_cache(cover_url, ANN_CACHE_PATH, quality=60)
                    processed_content.append({
                        "contentType": "video",
                        "coverUrl": cover_url,
                        "coverB64": cover_b64,
                    })

        user_name = res.get("userName", "战双帕弥什")
        head_code_url = res.get("headCodeUrl", "")
        user_avatar = ""
        if head_code_url:
            user_avatar = await get_image_b64_with_cache(head_code_url, ANN_CACHE_PATH, quality=60)

        context = {
            "title": res.get("postTitle", "公告详情"),
            "subtitle": f"发布时间: {res.get('postTime', '未知')}",
            "post_time": res.get('postTime', '未知'),
            "user_name": user_name,
            "user_avatar": user_avatar,
            "is_list": False,
            "content": processed_content,
            "logo_b64": get_logo_b64(),
            "footer_b64": get_footer_b64(),
        }

        img_bytes = await render_html(waves_templates, "ann_card.html", context)
        if img_bytes:
            if result_images:
                result_images = [img_bytes] + result_images
                return result_images
            return img_bytes
        return "渲染失败"

    except Exception as e:
        logger.exception(f"[PGRUID] HTML渲染失败: {e}")
        return f"渲染失败: {e}"
