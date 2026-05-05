def hide_uid(uid) -> str:
    from ..pgr_config.config_default import PGRConfig

    uid_str = str(uid) if uid is not None else ""
    if not PGRConfig.get_config("HideUid").data:
        return uid_str
    if len(uid_str) < 2:
        return uid_str
    return uid_str[:2] + "*" * 4 + uid_str[-2:]
