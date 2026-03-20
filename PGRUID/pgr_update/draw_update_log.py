import subprocess
import unicodedata
from typing import List, Tuple, Union
from pathlib import Path

from gsuid_core.logger import logger

from XutheringWavesUID.XutheringWavesUID.utils.render_utils import render_html, image_to_base64
from jinja2 import Environment, FileSystemLoader

IMGS_PATH = Path(__file__).parent / "imgs"
ICON_PATH = Path(__file__).parents[2] / "ICON.png"
_TEMPLATE_DIR = Path(__file__).parent
pgr_update_templates = Environment(loader=FileSystemLoader([str(_TEMPLATE_DIR)]))


def _get_git_logs() -> List[str]:
    try:
        process = subprocess.Popen(
            ["git", "log", "--pretty=format:%s", "-100"],
            cwd=str(Path(__file__).parents[2]),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            return []
        commits = stdout.decode("utf-8", errors="ignore").split("\n")

        filtered_commits = []
        for commit in commits:
            if commit:
                emojis, _ = _extract_leading_emojis(commit)
                if emojis:
                    filtered_commits.append(commit)
                    if len(filtered_commits) >= 18:
                        break
        return filtered_commits
    except Exception as e:
        logger.warning(f"Get logs failed: {e}")
        return []


def _is_regional_indicator(ch: str) -> bool:
    return 0x1F1E6 <= ord(ch) <= 0x1F1FF


def _is_skin_tone(ch: str) -> bool:
    return 0x1F3FB <= ord(ch) <= 0x1F3FF


def _try_consume_emoji(message: str, i: int) -> Tuple[str, int]:
    n = len(message)
    ch = message[i]

    if _is_regional_indicator(ch) and i + 1 < n and _is_regional_indicator(message[i + 1]):
        return message[i : i + 2], i + 2

    if ch in "0123456789#*":
        j = i + 1
        if j < n and message[j] == "\ufe0f":
            j += 1
        if j < n and message[j] == "\u20e3":
            j += 1
            return message[i:j], j
        return "", i

    cat = unicodedata.category(ch)
    if cat not in ("So", "Sk"):
        return "", i

    j = i + 1
    if j < n and message[j] == "\ufe0f":
        j += 1
    if j < n and _is_skin_tone(message[j]):
        j += 1
    while j < n and message[j] == "\u200d":
        if j + 1 >= n:
            break
        nxt = message[j + 1]
        nxt_cat = unicodedata.category(nxt)
        if nxt_cat not in ("So", "Sk"):
            break
        j += 2
        if j < n and message[j] == "\ufe0f":
            j += 1
        if j < n and _is_skin_tone(message[j]):
            j += 1

    return message[i:j], j


def _extract_leading_emojis(message: str) -> Tuple[List[str], str]:
    emojis = []
    i = 0
    while i < len(message):
        if message[i] == "\ufe0f":
            i += 1
            continue
        emoji_str, new_i = _try_consume_emoji(message, i)
        if not emoji_str:
            break
        emojis.append(emoji_str)
        i = new_i
    return emojis, message[i:].lstrip()


_CACHED_LOGS = _get_git_logs()


async def draw_update_log_img() -> Union[bytes, str]:
    if not _CACHED_LOGS:
        return "获取失败"

    icon_b64 = image_to_base64(ICON_PATH)
    bg_b64 = image_to_base64(IMGS_PATH / "bg.png")
    shadow_b64 = image_to_base64(IMGS_PATH / "halfyearShadow.png")

    logs = []
    for index, raw_log in enumerate(_CACHED_LOGS):
        emojis, text = _extract_leading_emojis(raw_log)
        if not emojis:
            continue
        if ")" in text:
            text = text.split(")")[0] + ")"
        text = text.replace("`", "")
        logs.append({
            "emoji": "".join(emojis[:4]),
            "text": text,
            "index": index + 1,
        })

    context = {
        "icon_b64": icon_b64,
        "bg_b64": bg_b64,
        "shadow_b64": shadow_b64,
        "logs": logs,
    }

    img_bytes = await render_html(pgr_update_templates, "pgr_update_log.html", context)
    if img_bytes:
        return img_bytes
    return "渲染更新记录失败"
