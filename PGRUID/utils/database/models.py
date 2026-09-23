"""PGRUID 数据库模型"""
import time
from typing import List, Set, Type, Optional, TypeVar
from contextvars import ContextVar

from sqlmodel import Field, select
from sqlalchemy.sql import and_
from sqlalchemy.ext.asyncio import AsyncSession
from gsuid_core.server import on_core_start
from gsuid_core.utils.database.base_models import BaseIDModel, BaseBotIDModel, with_session

try:
    from gsuid_core.utils.database.base_models import with_read_session
except ImportError:
    with_read_session = with_session

# 从 xwuid 导入数据库模型
from plugins.XutheringWavesUID.XutheringWavesUID.utils.database.waves_subscribe import (  # noqa: F401
    WavesSubscribe,
)

from .auto_migrate import auto_add_missing_columns

# 公告推送期间置位, 群活跃 hook 据此跳过推送自身
ANN_PUSH_GUARD: ContextVar[bool] = ContextVar("pgr_ann_push_guard", default=False)

T_PGRUserSettings = TypeVar("T_PGRUserSettings", bound="PGRUserSettings")
T_PGRServerMap = TypeVar("T_PGRServerMap", bound="PGRServerMap")
T_PGRGroupActivity = TypeVar("T_PGRGroupActivity", bound="PGRGroupActivity")
T_PGRUserActivity = TypeVar("T_PGRUserActivity", bound="PGRUserActivity")


class PGRServerMap(BaseIDModel, table=True):
    """PGR UID -> ServerId 映射表"""

    __table_args__ = {"extend_existing": True}

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

    __table_args__ = {"extend_existing": True}

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


class PGRGroupActivity(BaseBotIDModel, table=True):
    """群活跃度记录表: 群最后有人使用本插件的时间"""

    __tablename__ = "PGRGroupActivity"
    __table_args__ = {"extend_existing": True}

    group_id: str = Field(default="", title="群组ID")
    bot_self_id: str = Field(default="", title="BotSelfID")
    last_active_time: Optional[int] = Field(default=None, title="最后活跃时间")

    @classmethod
    @with_session
    async def update_group_activity(
        cls: Type[T_PGRGroupActivity],
        session: AsyncSession,
        group_id: str,
        bot_id: str,
        bot_self_id: str,
    ) -> bool:
        return await cls._touch(session, group_id, bot_id, bot_self_id)

    @classmethod
    @with_session
    async def update_many(
        cls: Type[T_PGRGroupActivity],
        session: AsyncSession,
        rows: List[tuple[str, str, str]],
    ) -> None:
        for group_id, bot_id, bot_self_id in rows:
            await cls._touch(session, group_id, bot_id, bot_self_id)

    @classmethod
    async def _touch(
        cls: Type[T_PGRGroupActivity],
        session: AsyncSession,
        group_id: str,
        bot_id: str,
        bot_self_id: str,
    ) -> bool:
        current_time = int(time.time())
        sql = select(cls).where(
            and_(
                cls.group_id == group_id,
                cls.bot_id == bot_id,
                cls.bot_self_id == bot_self_id,
            )
        )
        result = await session.execute(sql)
        existing = result.scalars().first()
        if existing:
            existing.last_active_time = current_time
            session.add(existing)
        else:
            session.add(
                cls(
                    group_id=group_id,
                    bot_id=bot_id,
                    bot_self_id=bot_self_id,
                    last_active_time=current_time,
                )
            )
        return True

    @classmethod
    @with_read_session
    async def get_active_group_ids(
        cls: Type[T_PGRGroupActivity],
        session: AsyncSession,
        active_days: int,
    ) -> Set[str]:
        """一次性取出所有活跃群的 group_id 集合"""
        threshold_time = int(time.time()) - active_days * 24 * 60 * 60
        sql = select(cls.group_id).where(
            and_(
                cls.last_active_time.is_not(None),
                cls.last_active_time >= threshold_time,
            )
        )
        result = await session.execute(sql)
        return {gid for gid in result.scalars().all() if gid}


class PGRUserActivity(BaseBotIDModel, table=True):
    """用户活跃度记录表: 用户最后使用本插件的时间"""

    __tablename__ = "PGRUserActivity"
    __table_args__ = {"extend_existing": True}

    user_id: str = Field(default="", title="用户ID")
    bot_self_id: str = Field(default="", title="BotSelfID")
    last_active_time: Optional[int] = Field(default=None, title="最后活跃时间")

    @classmethod
    @with_session
    async def update_user_activity(
        cls: Type[T_PGRUserActivity],
        session: AsyncSession,
        user_id: str,
        bot_id: str,
        bot_self_id: str,
    ) -> bool:
        return await cls._touch(session, user_id, bot_id, bot_self_id)

    @classmethod
    @with_session
    async def update_many(
        cls: Type[T_PGRUserActivity],
        session: AsyncSession,
        rows: List[tuple[str, str, str]],
    ) -> None:
        for user_id, bot_id, bot_self_id in rows:
            await cls._touch(session, user_id, bot_id, bot_self_id)

    @classmethod
    async def _touch(
        cls: Type[T_PGRUserActivity],
        session: AsyncSession,
        user_id: str,
        bot_id: str,
        bot_self_id: str,
    ) -> bool:
        current_time = int(time.time())
        sql = select(cls).where(
            and_(
                cls.user_id == user_id,
                cls.bot_id == bot_id,
                cls.bot_self_id == bot_self_id,
            )
        )
        result = await session.execute(sql)
        existing = result.scalars().first()
        if existing:
            existing.last_active_time = current_time
            session.add(existing)
        else:
            session.add(
                cls(
                    user_id=user_id,
                    bot_id=bot_id,
                    bot_self_id=bot_self_id,
                    last_active_time=current_time,
                )
            )
        return True

    @classmethod
    @with_read_session
    async def get_active_user_ids(
        cls: Type[T_PGRUserActivity],
        session: AsyncSession,
        active_days: int,
    ) -> Set[str]:
        """一次性取出所有活跃用户的 user_id 集合"""
        threshold_time = int(time.time()) - active_days * 24 * 60 * 60
        sql = select(cls.user_id).where(
            and_(
                cls.last_active_time.is_not(None),
                cls.last_active_time >= threshold_time,
            )
        )
        result = await session.execute(sql)
        return {uid for uid in result.scalars().all() if uid}


@on_core_start
async def _pgr_auto_migrate():
    await auto_add_missing_columns(__name__, log_prefix="[战双·补列]")
