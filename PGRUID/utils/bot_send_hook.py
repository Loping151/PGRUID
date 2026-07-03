import inspect
import sys
from typing import Callable, Optional

from gsuid_core.bot import Bot
from gsuid_core.logger import logger


if not hasattr(sys, "_gs_bot_hook_managers"):
    sys._gs_bot_hook_managers = {}
_plugin_hook_managers = sys._gs_bot_hook_managers


class PluginHookManager:
    """插件 hook 管理器"""

    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        self.target_send_hooks: list[Callable] = []
        self.user_activity_hooks: list[Callable] = []
        self.group_activity_hooks: list[Callable] = []

    def register_target_send_hook(self, func: Callable):
        self.target_send_hooks[:] = [h for h in self.target_send_hooks if h.__name__ != func.__name__]
        self.target_send_hooks.append(func)

    def register_user_activity_hook(self, func: Callable):
        self.user_activity_hooks[:] = [h for h in self.user_activity_hooks if h.__name__ != func.__name__]
        self.user_activity_hooks.append(func)

    def register_group_activity_hook(self, func: Callable):
        self.group_activity_hooks[:] = [h for h in self.group_activity_hooks if h.__name__ != func.__name__]
        self.group_activity_hooks.append(func)


def get_or_create_hook_manager(plugin_name: str) -> PluginHookManager:
    if plugin_name not in _plugin_hook_managers:
        _plugin_hook_managers[plugin_name] = PluginHookManager(plugin_name)
    return _plugin_hook_managers[plugin_name]


_pgr_manager = get_or_create_hook_manager("PGR")


def _hook_arity(hook: Callable) -> int:
    try:
        return len(inspect.signature(hook).parameters)
    except (TypeError, ValueError):
        return 3


def register_target_send_hook(func: Callable):
    _pgr_manager.register_target_send_hook(func)


def register_user_activity_hook(func: Callable):
    _pgr_manager.register_user_activity_hook(func)


def register_group_activity_hook(func: Callable):
    _pgr_manager.register_group_activity_hook(func)


async def _call_all_target_send_hooks(
    target_type: str,
    target_id: Optional[str],
    bot_id: str,
    bot_self_id: str,
):
    group_id = target_id if target_type == "group" else None
    if not group_id:
        return

    for plugin_name, manager in _plugin_hook_managers.items():
        if not manager.target_send_hooks:
            continue
        for hook in manager.target_send_hooks:
            try:
                if _hook_arity(hook) >= 3:
                    await hook(group_id, bot_id, bot_self_id)
                else:
                    await hook(group_id, bot_self_id)
            except Exception as e:
                logger.warning(f"[战双·BotHook] target_send hook {hook.__name__} 执行失败: {e}")


async def _call_all_group_activity_hooks(
    group_id: Optional[str],
    bot_id: str,
    bot_self_id: str,
):
    if not group_id:
        return

    for plugin_name, manager in _plugin_hook_managers.items():
        if not manager.group_activity_hooks:
            continue
        for hook in manager.group_activity_hooks:
            try:
                await hook(group_id, bot_id, bot_self_id)
            except Exception as e:
                logger.warning(f"[战双·BotHook] group_activity hook {hook.__name__} 执行失败: {e}")


async def _call_all_user_activity_hooks(user_id: Optional[str], bot_id: str, bot_self_id: str):
    if not user_id:
        return

    for plugin_name, manager in _plugin_hook_managers.items():
        if not manager.user_activity_hooks:
            continue
        for hook in manager.user_activity_hooks:
            try:
                try:
                    await hook(user_id, bot_id, bot_self_id)
                except TypeError:
                    await hook(user_id, bot_id)
            except Exception as e:
                logger.warning(f"[战双·BotHook] user_activity hook {hook.__name__} 执行失败: {e}")


def install_bot_hooks():
    """Monkey Patch 拦截 Bot.send 和 Bot.target_send，全局只安装一次"""
    if hasattr(Bot, "_bot_hooks_installed"):
        return

    original_send = Bot.send
    original_target_send = Bot.target_send

    async def hooked_send(self, *args, **kwargs):
        user_id = getattr(self.ev, "user_id", None) if hasattr(self, "ev") else None
        bot_id = getattr(self, "bot_id", "") if hasattr(self, "bot_id") else ""
        bot_self_id = getattr(self, "bot_self_id", "") if hasattr(self, "bot_self_id") else ""

        await _call_all_user_activity_hooks(user_id, bot_id, bot_self_id)

        if hasattr(self, "ev"):
            target_type = getattr(self.ev, "user_type", "")
            group_id = getattr(self.ev, "group_id", None)
            if target_type and group_id:
                await _call_all_target_send_hooks(target_type, group_id, bot_id, bot_self_id)
                await _call_all_group_activity_hooks(group_id, bot_id, bot_self_id)

        return await original_send(self, *args, **kwargs)

    async def hooked_target_send(self, *args, **kwargs):
        if hasattr(self, "ev") and len(args) >= 3:
            target_type = args[1]
            target_id = args[2]
            bot_id = getattr(self.ev, "real_bot_id", getattr(self, "bot_id", ""))
            bot_self_id = getattr(self.ev, "bot_self_id", getattr(self, "bot_self_id", ""))
            await _call_all_target_send_hooks(target_type, target_id, bot_id, bot_self_id)

        return await original_target_send(self, *args, **kwargs)

    Bot.send = hooked_send
    Bot.target_send = hooked_target_send
    Bot._bot_hooks_installed = True

    logger.debug("[战双·BotHook] Bot hooks 已安装")
