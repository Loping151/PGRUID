"""PGRUID - 战双帕弥什插件"""
import asyncio

from gsuid_core.sv import Plugins
from gsuid_core.logger import logger
from gsuid_core.server import on_core_shutdown


Plugins(
    name="PGRUID",
    force_prefix=["pgr", "zs"],
    allow_empty_prefix=False
)

from .utils.bot_send_hook import (
    install_bot_hooks,
    register_group_activity_hook,
    register_user_activity_hook,
)
from .utils.database.models import PGRGroupActivity, PGRUserActivity, ANN_PUSH_GUARD
from .utils.plugin_checker import is_from_pgr_plugin

_group_activity_buffer: dict[str, tuple[str, str, str]] = {}
_user_activity_buffer: dict[str, tuple[str, str, str]] = {}
_FLUSH_INTERVAL = 60
_ACTIVITY_CHUNK = 400


async def _flush_activity_buffer():
    if _group_activity_buffer:
        pending = list(_group_activity_buffer.values())
        _group_activity_buffer.clear()
        for start in range(0, len(pending), _ACTIVITY_CHUNK):
            chunk = pending[start : start + _ACTIVITY_CHUNK]
            try:
                await PGRGroupActivity.update_many(chunk)
            except Exception as e:
                logger.warning(f"[战双·插件] 批量群活跃度写入失败: {e}")

    if _user_activity_buffer:
        user_pending = list(_user_activity_buffer.values())
        _user_activity_buffer.clear()
        for start in range(0, len(user_pending), _ACTIVITY_CHUNK):
            chunk = user_pending[start : start + _ACTIVITY_CHUNK]
            try:
                await PGRUserActivity.update_many(chunk)
            except Exception as e:
                logger.warning(f"[战双·插件] 批量用户活跃度写入失败: {e}")


_shutdown_event = asyncio.Event()


async def _activity_flush_loop():
    while not _shutdown_event.is_set():
        try:
            await asyncio.wait_for(_shutdown_event.wait(), timeout=_FLUSH_INTERVAL)
            break
        except asyncio.TimeoutError:
            pass
        try:
            await _flush_activity_buffer()
        except Exception as e:
            logger.warning(f"[战双·插件] 群活跃度刷写循环异常: {e}")


_flush_task = asyncio.get_event_loop().create_task(_activity_flush_loop())


@on_core_shutdown
async def _flush_on_shutdown():
    _shutdown_event.set()
    try:
        await asyncio.wait_for(_flush_task, timeout=5)
    except asyncio.TimeoutError:
        _flush_task.cancel()
    await _flush_activity_buffer()


async def pgr_group_activity_hook(group_id: str, bot_id: str, bot_self_id: str):
    if ANN_PUSH_GUARD.get():
        return
    if not is_from_pgr_plugin():
        return
    if not group_id:
        return
    _group_activity_buffer[f"{group_id}:{bot_id}:{bot_self_id}"] = (group_id, bot_id, bot_self_id)


async def pgr_user_activity_hook(user_id: str, bot_id: str, bot_self_id: str):
    if ANN_PUSH_GUARD.get():
        return
    if not is_from_pgr_plugin():
        return
    if not user_id:
        return
    _user_activity_buffer[f"{user_id}:{bot_id}:{bot_self_id}"] = (user_id, bot_id, bot_self_id)


install_bot_hooks()
register_group_activity_hook(pgr_group_activity_hook)
register_user_activity_hook(pgr_user_activity_hook)

logger.success("[战双·插件] 插件加载完成")
