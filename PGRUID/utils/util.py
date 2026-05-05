def hide_uid(uid) -> str:
    from ..pgr_config.config_default import PGRConfig
    # 复用 XutheringWavesUID 共享的 WavesUser.hide_uid_self_value 缓存
    from gsuid_core.plugins.XutheringWavesUID.XutheringWavesUID.utils.hide_uid_pref import get_pref

    uid_str = str(uid) if uid is not None else ""
    pref = get_pref(uid_str)
    if pref == "off":
        return uid_str
    if pref != "on":
        if not PGRConfig.get_config("HideUid").data:
            return uid_str
    if len(uid_str) < 2:
        return uid_str
    return uid_str[:2] + "*" * 4 + uid_str[-2:]
