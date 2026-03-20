from typing import Dict

from gsuid_core.utils.plugins_config.models import (
    GSC,
    GsIntConfig,
    GsStrConfig,
    GsBoolConfig,
    GsListStrConfig,
)
from gsuid_core.utils.plugins_config.gs_config import StringConfig
from ..utils.path import CONFIG_PATH

CONFIG_DEFAULT: Dict[str, GSC] = {
    # ==================== 公告配置 ====================
    "PGRAnnOpen": GsBoolConfig(
        "公告推送总开关",
        "公告推送总开关",
        True,
    ),
    "AnnMinuteCheck": GsIntConfig(
        "公告推送时间检测（单位min）",
        "公告推送时间检测（单位min）",
        10,
        60,
    ),
    "CacheDaysToKeep": GsIntConfig(
        "保留缓存公告资源天数",
        "自动删除创建时间早于此天数的公告图片缓存，每次启动和每天定时执行",
        42,
        3650,
    ),

    # ==================== 渲染配置 ====================
    "UseHtmlRender": GsBoolConfig(
        "使用HTML渲染",
        "开启后将使用HTML渲染公告卡片",
        True,
    ),
    "RemoteRenderEnable": GsBoolConfig(
        "外置渲染开关",
        "开启后将使用外置渲染服务进行HTML渲染，失败时自动回退到本地渲染",
        False,
    ),
    "RemoteRenderUrl": GsStrConfig(
        "外置渲染地址",
        "外置渲染服务的API地址，例如：http://127.0.0.1:3000/render",
        "http://127.0.0.1:3000/render",
    ),
    "FontCssUrl": GsStrConfig(
        "外置渲染字体CSS地址",
        "用于HTML渲染的字体CSS URL",
        "https://fonts.loli.net/css2?family=JetBrains+Mono:wght@500;700&family=Oswald:wght@500;700&family=Noto+Sans+SC:wght@400;700&family=Noto+Color+Emoji&display=swap",
    ),

    # ==================== 代理配置 ====================
    "LocalProxyUrl": GsStrConfig(
        "本地代理地址",
        "本地代理地址",
        "",
    ),
}


PGRConfig = StringConfig(
    "PGRUID",
    CONFIG_PATH,
    CONFIG_DEFAULT,
)
