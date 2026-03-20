import json
import hashlib
import string
from typing import Optional, Dict

from gsuid_core.logger import logger
from ...utils.path import CACHE_BASE

MAPPER_FILE = CACHE_BASE / "post_id_mapping.json"


class PostIdMapper:
    """postId 到短字母 ID 的映射器"""

    def __init__(self):
        self.id_to_post: Dict[str, str] = {}
        self.post_to_id: Dict[str, str] = {}
        self.load()

    def _generate_short_id(self, post_id: str) -> str:
        hash_obj = hashlib.md5(post_id.encode())
        hash_hex = hash_obj.hexdigest()
        chars = string.ascii_lowercase
        short_id = ""
        for i in range(0, 8, 2):
            byte_val = int(hash_hex[i:i+2], 16)
            short_id += chars[byte_val % len(chars)]
        return short_id

    def get_or_create(self, post_id: str) -> str:
        post_id = str(post_id)
        if post_id in self.post_to_id:
            return self.post_to_id[post_id]
        short_id = self._generate_short_id(post_id)
        counter = 1
        original_short_id = short_id
        while short_id in self.id_to_post:
            short_id = f"{original_short_id}{counter}"
            counter += 1
        self.id_to_post[short_id] = post_id
        self.post_to_id[post_id] = short_id
        self.save()
        return short_id

    def get_post_id(self, short_id: str) -> Optional[str]:
        return self.id_to_post.get(short_id)

    def load(self):
        if not MAPPER_FILE.exists():
            return
        try:
            with open(MAPPER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.id_to_post = data.get("id_to_post", {})
                self.post_to_id = data.get("post_to_id", {})
        except Exception as e:
            logger.warning(f"[PGR PostIdMapper] 加载映射失败: {e}")

    def save(self):
        try:
            MAPPER_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(MAPPER_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "id_to_post": self.id_to_post,
                    "post_to_id": self.post_to_id,
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[PGR PostIdMapper] 保存映射失败: {e}")


_mapper = PostIdMapper()


def get_or_create_short_id(post_id: str) -> str:
    return _mapper.get_or_create(post_id)


def get_post_id_from_short(short_id: str) -> Optional[str]:
    return _mapper.get_post_id(short_id)
