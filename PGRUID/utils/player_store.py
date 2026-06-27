"""逐用户面板 JSON 的 gzip 落盘层。"""
import os
import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Optional, Union

from gsuid_core.logger import logger

PathLike = Union[str, Path]


def _is_gzip(name: str) -> bool:
    return Path(name).stem.isdigit()


def resolve_player_path(path: PathLike) -> Optional[Path]:
    p = Path(path)
    if _is_gzip(p.name):
        gp = p.with_name(p.name + ".gz")
        if gp.exists():
            return gp
    return p if p.exists() else None


def read_player_json_sync(path: PathLike) -> Any:
    p = resolve_player_path(path)
    if p is None:
        return None
    try:
        opener = gzip.open if p.suffix == ".gz" else open
        with opener(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[player_store] 读取失败 {p}: {e}")
        return None


def _gzip_dump(path: Path, obj: Any) -> None:
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    with open(path, "wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=6, filename="", mtime=0) as f:
            f.write(data)


def write_player_json_sync(path: PathLike, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    gz = _is_gzip(p.name)
    target = p.with_name(p.name + ".gz") if gz else p
    fd, tmp_name = tempfile.mkstemp(dir=str(p.parent), prefix=p.name + ".", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        os.close(fd)
        if gz:
            _gzip_dump(tmp, obj)
        else:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(obj, fh, ensure_ascii=False)
        os.chmod(tmp, 0o644)
        tmp.replace(target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    if gz:
        p.unlink(missing_ok=True)


def compress_all(player_path: PathLike) -> tuple[int, int, int, int]:
    """存量明文批量转 gz,放 to_thread 跑。"""
    done = fail = before = after = 0
    base = Path(player_path)
    if not base.is_dir():
        return done, fail, before, after
    for uid_dir in base.iterdir():
        if not uid_dir.is_dir():
            continue
        for plain in uid_dir.glob("*.json"):
            if not plain.is_file() or not _is_gzip(plain.name):
                continue
            try:
                size = plain.stat().st_size
                obj = read_player_json_sync(plain)
                if obj is None:
                    fail += 1
                    continue
                write_player_json_sync(plain, obj)
                before += size
                after += plain.with_name(plain.name + ".gz").stat().st_size
                done += 1
            except Exception:
                fail += 1
    return done, fail, before, after
