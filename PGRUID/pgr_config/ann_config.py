import json
from typing import Dict, List

from gsuid_core.logger import logger

from ..utils.path import ANN_DATA_PATH


def load_ann_data() -> Dict:
    """加载公告数据"""
    if not ANN_DATA_PATH.exists():
        return {"groups": {}, "new_ids": []}

    try:
        with open(ANN_DATA_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {"groups": {}, "new_ids": []}
            data = json.loads(content)
            if not isinstance(data, dict):
                return {"groups": {}, "new_ids": []}
            if "groups" not in data:
                data["groups"] = {}
            if "new_ids" not in data:
                data["new_ids"] = []
            return data
    except Exception as e:
        logger.exception(f"加载公告数据失败: {e}")
        return {"groups": {}, "new_ids": []}


def save_ann_data(data: Dict) -> bool:
    """保存公告数据"""
    try:
        with open(ANN_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.exception(f"保存公告数据失败: {e}")
        return False


def get_ann_groups() -> Dict:
    """获取公告群组配置"""
    data = load_ann_data()
    return data.get("groups", {})


def set_ann_groups(groups: Dict) -> bool:
    """设置公告群组配置"""
    data = load_ann_data()
    data["groups"] = groups
    return save_ann_data(data)


def get_ann_new_ids() -> List:
    """获取新公告ID列表"""
    data = load_ann_data()
    return data.get("new_ids", [])


def set_ann_new_ids(new_ids: List) -> bool:
    """设置新公告ID列表"""
    data = load_ann_data()
    data["new_ids"] = new_ids
    return save_ann_data(data)
