"""角色名称转换工具

维护 full_body.json / name2id / 自定义别名，提供名称到 bodyId 的转换
"""
import json
from typing import Dict, List, Optional

from gsuid_core.logger import logger

from .path import FULL_BODY_PATH, CHAR_ALIAS_PATH
from .image import pic_download_from_url
from .path import ROLE_ICON_PATH


# ===== full_body.json =====

def load_full_body() -> Dict[str, dict]:
    if not FULL_BODY_PATH.exists():
        return {}
    try:
        with open(FULL_BODY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_full_body(data: Dict[str, dict]):
    with open(FULL_BODY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def update_full_body(role_index) -> Dict[str, dict]:
    """更新 full_body.json 并下载角色图标，只在角色数量增加时写入

    同时更新 name2id 缓存
    """
    full_body = load_full_body()
    old_count = len(full_body)

    for char in role_index.characterList:
        body_id = str(char.bodyId)
        full_body[body_id] = {
            "bodyId": char.bodyId,
            "bodyName": char.bodyName,
            "iconUrl": char.iconUrl,
            "element": char.element,
            "effect": char.effect,
            "quality": char.quality or 0,
            "grade": char.grade,
            "fightAbility": char.fightAbility or 0,
            "level": char.level or 0,
            "roleRank": char.roleRank,
            "priority": char.priority,
            "weaponType": char.weaponType,
        }

        if char.iconUrl:
            try:
                await pic_download_from_url(ROLE_ICON_PATH, char.iconUrl, save_name=body_id)
            except Exception as e:
                logger.warning(f"[PGR] 下载角色图标失败: {char.bodyName}, {e}")

    new_count = len(full_body)
    if new_count > old_count:
        save_full_body(full_body)
        logger.info(f"[PGR] full_body.json 已更新: {old_count} -> {new_count}")
        # 同步刷新 name2id
        _rebuild_name2id(full_body)

    return full_body


# ===== name2id =====

_name2id: Dict[str, int] = {}


def _rebuild_name2id(full_body: Optional[Dict[str, dict]] = None):
    """从 full_body 重建 name2id 映射"""
    global _name2id
    if full_body is None:
        full_body = load_full_body()
    _name2id.clear()
    for body_id, info in full_body.items():
        name = info.get("bodyName", "")
        if name:
            _name2id[name] = int(body_id)


def get_name2id() -> Dict[str, int]:
    """获取 name -> bodyId 字典（懒加载）"""
    if not _name2id:
        _rebuild_name2id()
    return _name2id


# ===== 自定义别名 =====

def _load_alias() -> Dict[str, List[str]]:
    """加载别名: { bodyId_str: [alias1, alias2, ...] }"""
    if not CHAR_ALIAS_PATH.exists():
        return {}
    try:
        with open(CHAR_ALIAS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_alias(data: Dict[str, List[str]]):
    with open(CHAR_ALIAS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_alias(body_name: str, alias: str) -> str:
    """添加别名，返回提示消息"""
    name2id = get_name2id()
    body_id = name2id.get(body_name)
    if body_id is None:
        return f"未找到角色「{body_name}」"

    alias_data = _load_alias()
    key = str(body_id)
    alias_list = alias_data.get(key, [])
    if alias in alias_list:
        return f"「{body_name}」已有别名「{alias}」"

    alias_list.append(alias)
    alias_data[key] = alias_list
    _save_alias(alias_data)
    return f"已为「{body_name}」添加别名「{alias}」"


def remove_alias(body_name: str, alias: str) -> str:
    """删除别名，返回提示消息"""
    name2id = get_name2id()
    body_id = name2id.get(body_name)
    if body_id is None:
        return f"未找到角色「{body_name}」"

    alias_data = _load_alias()
    key = str(body_id)
    alias_list = alias_data.get(key, [])
    if alias not in alias_list:
        return f"「{body_name}」没有别名「{alias}」"

    alias_list.remove(alias)
    alias_data[key] = alias_list
    _save_alias(alias_data)
    return f"已删除「{body_name}」的别名「{alias}」"


def get_alias_list(body_name: str) -> Optional[List[str]]:
    """获取角色的别名列表"""
    name2id = get_name2id()
    body_id = name2id.get(body_name)
    if body_id is None:
        return None
    alias_data = _load_alias()
    return alias_data.get(str(body_id), [])


def resolve_char_name(input_name: str) -> Optional[int]:
    """将输入名称（原名或别名）解析为 bodyId

    匹配顺序：精确原名 → 精确别名 → endswith 原名 → endswith 别名
    """
    name2id = get_name2id()

    # 1. 精确匹配原名
    if input_name in name2id:
        return name2id[input_name]

    # 2. 精确匹配别名
    alias_data = _load_alias()
    for body_id_str, aliases in alias_data.items():
        if input_name in aliases:
            return int(body_id_str)

    # 3. endswith 匹配原名（输入可能带前缀）
    for name, body_id in name2id.items():
        if input_name.endswith(name):
            return body_id

    # 4. endswith 匹配别名
    for body_id_str, aliases in alias_data.items():
        for alias in aliases:
            if input_name.endswith(alias):
                return int(body_id_str)

    return None


def get_body_name_by_id(body_id: int) -> str:
    """通过 bodyId 获取 bodyName"""
    full_body = load_full_body()
    info = full_body.get(str(body_id))
    return info["bodyName"] if info else str(body_id)
