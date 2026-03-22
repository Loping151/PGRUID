from pathlib import Path

from PIL import Image

from gsuid_core.logger import logger

ICON = Path(__file__).parent.parent.parent / "ICON.png"


def get_ICON():
    return Image.open(ICON)


async def pic_download_from_url(
    path: Path,
    pic_url: str,
    save_name: str = "",
) -> Image.Image:
    path.mkdir(parents=True, exist_ok=True)

    orig_name = pic_url.split("/")[-1]
    if save_name:
        ext = Path(orig_name).suffix or ".png"
        name = f"{save_name}{ext}"
    else:
        name = orig_name
    _path = path / name
    webp_path = _path.with_suffix(".webp")

    if webp_path.exists():
        return Image.open(webp_path).convert("RGBA")

    if not _path.exists():
        from gsuid_core.utils.download_resource.download_file import download

        await download(pic_url, path, name, tag="[PGR]")

    # 并发时另一个任务可能已将 png 转为 webp 并删除原文件，再次检查
    if webp_path.exists():
        return Image.open(webp_path).convert("RGBA")

    try:
        img = Image.open(_path).convert("RGBA")
    except Exception as e:
        logger.warning(f"[PGR] 打开图片失败: {_path}, {e}")
        raise

    if _path != webp_path:
        try:
            img.save(webp_path, "WEBP", quality=85)
            _path.unlink(missing_ok=True)
            logger.debug(f"[PGR] 已将图片转为webp: {webp_path.name}")
        except Exception as e:
            logger.warning(f"[PGR] 转换webp失败: {e}")

    return img
