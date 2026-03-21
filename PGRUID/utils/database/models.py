"""PGRUID 数据库模型"""
from typing import Dict, List, Type, Optional, TypeVar

from sqlmodel import Field, select
from sqlalchemy.ext.asyncio import AsyncSession
from gsuid_core.utils.database.base_models import BaseIDModel, BaseBotIDModel, with_session

# 从 xwuid 导入数据库模型
from gsuid_core.plugins.XutheringWavesUID.XutheringWavesUID.utils.database.waves_subscribe import (
    WavesSubscribe,
)

T_PGRUserSettings = TypeVar("T_PGRUserSettings", bound="PGRUserSettings")
T_PGRServerMap = TypeVar("T_PGRServerMap", bound="PGRServerMap")


class PGRServerMap(BaseIDModel, table=True):
    """PGR UID -> ServerId 映射表"""

    uid: str = Field(default="", title="游戏UID", unique=True)
    server_id: str = Field(default="1000", title="服务器ID")

    @classmethod
    @with_session
    async def get_server_id(
        cls: Type[T_PGRServerMap],
        session: AsyncSession,
        uid: str,
    ) -> Optional[str]:
        sql = select(cls.server_id).where(cls.uid == uid)
        result = await session.execute(sql)
        row = result.scalar_one_or_none()
        return row

    @classmethod
    @with_session
    async def set_server_id(
        cls: Type[T_PGRServerMap],
        session: AsyncSession,
        uid: str,
        server_id: str,
    ):
        sql = select(cls).where(cls.uid == uid)
        result = await session.execute(sql)
        existing = result.scalars().first()
        if existing:
            existing.server_id = server_id
            session.add(existing)
        else:
            session.add(cls(uid=uid, server_id=server_id))


class PGRUserSettings(BaseBotIDModel, table=True):
    """PGR 用户设置表

    user_id + bot_id + uid 确定唯一记录
    """

    user_id: str = Field(default="", title="用户ID")
    uid: str = Field(default="", title="游戏UID")
    stamina_bg_value: str = Field(default="", title="体力背景")

    @classmethod
    @with_session
    async def get_user_settings(
        cls: Type[T_PGRUserSettings],
        session: AsyncSession,
        user_id: str,
        bot_id: str,
        uid: str,
    ) -> Optional[T_PGRUserSettings]:
        sql = select(cls).where(
            cls.user_id == user_id,
            cls.bot_id == bot_id,
            cls.uid == uid,
        )
        result = await session.execute(sql)
        data = result.scalars().first()
        return data

    @classmethod
    @with_session
    async def set_stamina_bg(
        cls: Type[T_PGRUserSettings],
        session: AsyncSession,
        user_id: str,
        bot_id: str,
        uid: str,
        value: str,
    ) -> int:
        sql = select(cls).where(
            cls.user_id == user_id,
            cls.bot_id == bot_id,
            cls.uid == uid,
        )
        result = await session.execute(sql)
        existing = result.scalars().first()
        if existing:
            existing.stamina_bg_value = value
            session.add(existing)
        else:
            session.add(cls(user_id=user_id, bot_id=bot_id, uid=uid, stamina_bg_value=value))
        return 0
