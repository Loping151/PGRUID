import json
from pathlib import Path
from typing import Dict

from PIL import Image

from gsuid_core.help.model import PluginHelp
from gsuid_core.help.draw_new_plugin_help import get_new_help

from ..pgr_config import PREFIX
from ..version import PGRUID_version

ICON = Path(__file__).parent.parent.parent / "ICON.png"
HELP_DATA = Path(__file__).parent / "help.json"
ICON_PATH = Path(__file__).parent / "icon_path"
BANNER_PATH = Path(__file__).parent / "banner.jpg"
BG_PATH = Path(__file__).parent / "bg.jpg"


def get_help_data() -> Dict[str, PluginHelp]:
    with open(HELP_DATA, "r", encoding="utf-8") as file:
        help_content = json.load(file)
    return help_content


plugin_help = get_help_data()


async def get_help(pm: int):
    icon = Image.open(ICON).convert("RGBA") if ICON.exists() else Image.new("RGBA", (100, 100), (70, 130, 180, 255))

    banner_bg = Image.open(BANNER_PATH).convert("RGBA") if BANNER_PATH.exists() else None
    help_bg = Image.open(BG_PATH).convert("RGBA") if BG_PATH.exists() else None

    return await get_new_help(
        plugin_name="PGRUID",
        plugin_info={f"v{PGRUID_version}": ""},
        plugin_icon=icon,
        plugin_help=plugin_help,
        plugin_prefix=PREFIX,
        help_mode="dark",
        banner_bg=banner_bg,
        help_bg=help_bg,
        banner_sub_text="指挥官，欢迎回来",
        icon_path=ICON_PATH,
        footer=Image.new("RGBA", (1, 1), (0, 0, 0, 0)),
        enable_cache=False,
        pm=pm,
        column=4,
    )
