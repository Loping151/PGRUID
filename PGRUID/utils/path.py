import sys
from pathlib import Path

from gsuid_core.data_store import get_res_path

MAIN_PATH = get_res_path() / "PGRUID"
sys.path.append(str(MAIN_PATH))

# 配置文件
CONFIG_PATH = MAIN_PATH / "config.json"
ANN_DATA_PATH = MAIN_PATH / "ann_data.json"

# 用户数据
PLAYER_PATH = MAIN_PATH / "players"

# 资源缓存
CACHE_BASE = MAIN_PATH / "cache"
ANN_CACHE_PATH = CACHE_BASE / "ann"
BAKE_PATH = CACHE_BASE / "bake"

# 角色资源
RESOURCE_PATH = MAIN_PATH / "resource"
ROLE_ICON_PATH = RESOURCE_PATH / "role_icon"
ROLE_PILE_PATH = RESOURCE_PATH / "role_pile"
FASHION_PATH = RESOURCE_PATH / "fashion"
WEAPON_FASHION_PATH = RESOURCE_PATH / "weapon_fashion"
WEAPON_PATH = RESOURCE_PATH / "weapon"
PARTNER_PATH = RESOURCE_PATH / "partner"
CHIP_PATH = RESOURCE_PATH / "chip"
GAMEMODE_PATH = RESOURCE_PATH / "gamemode"

# 数据映射
FULL_BODY_PATH = MAIN_PATH / "full_body.json"

# 别名
ALIAS_PATH = MAIN_PATH / "alias"
CHAR_ALIAS_PATH = ALIAS_PATH / "char_alias.json"

# 其他
OTHER_PATH = MAIN_PATH / "other"

# 模板（各模块就地放置 HTML，不再用全局 templates 目录）


def init_dir():
    for p in [
        MAIN_PATH,
        PLAYER_PATH,
        CACHE_BASE,
        ANN_CACHE_PATH,
        BAKE_PATH,
        RESOURCE_PATH,
        ROLE_ICON_PATH,
        ROLE_PILE_PATH,
        FASHION_PATH,
        WEAPON_FASHION_PATH,
        WEAPON_PATH,
        PARTNER_PATH,
        CHIP_PATH,
        GAMEMODE_PATH,
        ALIAS_PATH,
        OTHER_PATH,
    ]:
        p.mkdir(parents=True, exist_ok=True)


init_dir()
