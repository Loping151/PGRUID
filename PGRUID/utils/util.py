def hide_uid(uid, user_pref: str = "") -> str:
    """user_pref: 该 uid 对应 WavesUser.hide_uid_self_value, 由 caller 传入。

    "on" 强制隐藏 / "off" 强制不隐藏 / "" 跟随全局 HideUid。
    """
    from ..pgr_config.config_default import PGRConfig

    uid_str = str(uid) if uid is not None else ""
    if user_pref == "off":
        return uid_str
    if user_pref != "on":
        if not PGRConfig.get_config("HideUid").data:
            return uid_str
    if len(uid_str) < 2:
        return uid_str
    return uid_str[:2] + "*" * 4 + uid_str[-2:]


async def get_hide_uid_pref(uid: str, user_id: str, bot_id: str) -> str:
    """读战双账号的 hide_uid_self_value, 没绑定就回空 (走全局 HideUid)。"""

    from ..utils.constants import PGR_GAME_ID
    from plugins.XutheringWavesUID.XutheringWavesUID.utils.database.models import (
        WavesUser,
    )

    try:
        user = await WavesUser.select_waves_user(
            uid,
            user_id,
            bot_id,
            game_id=PGR_GAME_ID,
        )
        return user.hide_uid_self_value if user else ""
    except Exception:
        return ""
