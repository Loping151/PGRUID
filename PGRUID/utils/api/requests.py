"""PGR API 请求模块

直接复用 xwuid 的请求底层（代理池、重试、session 管理等），只定义 PGR 的 API 端点
"""
import random
from typing import Any, Dict, List, Tuple, Union, Optional

from gsuid_core.logger import logger

from .api import (
    ANN_LIST_URL,
    ANN_CONTENT_URL,
    BBS_LIST,
    ROLE_LIST_URL,
    REFRESH_DATA_URL,
    ACCOUNT_DATA_URL,
    BASE_DATA_URL,
    DAILY_DATA_URL,
    HALF_YEAR_URL,
    ROLE_INDEX_URL,
    CHARACTER_FASHION_URL,
    WEAPON_FASHION_URL,
    PRISONER_CAGE_URL,
    AREA_URL,
    CHIP_OVERCLOCKING_URL,
    TRANSFINITE_URL,
    STRONGHOLD_URL,
    ROLE_DETAIL_URL,
)
from .model import (
    PGRAccountData,
    PGRBaseData,
    PGRDailyData,
    PGRHalfYearData,
    PGRRoleIndexData,
    PGRFashionData,
    PGRWeaponFashionData,
    PGRPrisonerCageData,
    PGRAreaData,
    PGRChipOverclockingData,
    PGRTransfiniteData,
    PGRStrongholdData,
    PGRRoleDetailData,
)
from ..constants import PGR_GAME_ID

# 直接复用 xwuid 的 waves_api 实例（含 session、代理、重试等）
from XutheringWavesUID.XutheringWavesUID.utils.waves_api import waves_api
from XutheringWavesUID.XutheringWavesUID.utils.api.request_util import (
    KuroApiResp,
    get_base_header,
    get_community_header,
)


class PGRApi:
    ann_map: Dict[str, dict] = {}
    ann_list_data: List[dict] = []
    event_type = {"2": "资讯", "3": "公告", "1": "活动"}

    async def _request(self, url: str, headers: dict, data: dict) -> KuroApiResp:
        """复用 xwuid 的请求底层"""
        return await waves_api._waves_request(url, "POST", headers, data=data)

    async def _resolve_server_id(self, role_id: str, server_id: Optional[str] = None) -> str:
        """从数据库获取 serverId，未缓存则返回默认值 1000"""
        if server_id:
            return server_id
        from ..database.models import PGRServerMap
        cached = await PGRServerMap.get_server_id(role_id)
        return cached or "1000"

    # ===== 服务器探测 =====

    async def get_server_id(self, role_id: str, token: str) -> str:
        """获取 UID 对应的 serverId，优先从数据库读取，否则自动探测"""
        from ..database.models import PGRServerMap

        cached = await PGRServerMap.get_server_id(role_id)
        if cached:
            return cached

        # 自动探测
        sid = await self._detect_server_id(role_id, token)
        await PGRServerMap.set_server_id(role_id, sid)
        return sid

    async def _detect_server_id(self, role_id: str, token: str) -> str:
        """通过 /gamer/role/list 获取 serverId"""
        headers = await get_base_header()
        headers["token"] = token
        data = {"gameId": PGR_GAME_ID}
        res = await self._request(ROLE_LIST_URL, headers, data)
        if res.success and isinstance(res.data, list):
            for role in res.data:
                if str(role.get("roleId")) == str(role_id):
                    sid = str(role.get("serverId", ""))
                    if sid:
                        logger.info(f"[PGRUID] UID {role_id} serverId={sid}")
                        return sid
        logger.warning(f"[PGRUID] 未获取到 UID {role_id} 的 serverId，使用默认 1000")
        return "1000"

    # ===== 通用游戏数据请求（带 serverId 自动重试） =====

    async def _game_request(
        self,
        url: str,
        role_id: str,
        token: str,
        server_id: Optional[str] = None,
        extra_data: Optional[Dict] = None,
    ) -> KuroApiResp:
        """通用游戏数据请求，data 为空时自动重新探测 serverId 并重试"""
        server_id = await self._resolve_server_id(role_id, server_id)
        headers = await get_base_header()
        headers["token"] = token
        data: Dict = {"serverId": server_id, "roleId": role_id}
        if extra_data:
            data.update(extra_data)

        res = await self._request(url, headers, data)

        # 请求成功且有数据，直接返回
        if res.success and res.data:
            return res
        # 请求失败（非200），不重试 serverId
        if not res.success:
            return res

        # success=True 但 data 为空，尝试重新探测 serverId
        new_sid = await self._detect_server_id(role_id, token)
        if new_sid == server_id:
            return res

        from ..database.models import PGRServerMap
        logger.info(
            f"[PGRUID] UID {role_id} serverId {server_id} → {new_sid}，重试请求"
        )
        await PGRServerMap.set_server_id(role_id, new_sid)
        data["serverId"] = new_sid
        headers = await get_base_header()
        headers["token"] = token
        return await self._request(url, headers, data)

    # ===== Token 验证 =====

    async def get_self_pgr_ck(
        self, uid: str, user_id: str, bot_id: str
    ) -> Optional[str]:
        """获取并验证 PGR 用户的 token，返回有效 token 或空串"""
        from XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesUser

        waves_user = await WavesUser.select_waves_user(uid, user_id, bot_id, game_id=PGR_GAME_ID)
        if not waves_user or not waves_user.cookie:
            return ""
        if waves_user.status == "无效":
            return ""

        # 用 login_log 验证 token 有效性
        data = await waves_api.login_log(uid, waves_user.cookie)
        if not data.success:
            await data.mark_cookie_invalid(uid, waves_user.cookie)
            return ""

        # 刷新数据
        data = await self.refresh_data(uid, waves_user.cookie)
        if not data.success:
            if data.is_server_maintenance:
                logger.warning(f"[PGRUID] 官方系统维护中，跳过刷新，UID: {uid}")
                await WavesUser.update_last_used_time(uid, user_id, bot_id, game_id=PGR_GAME_ID)
                return waves_user.cookie
            await data.mark_cookie_invalid(uid, waves_user.cookie)
            return ""

        await WavesUser.update_last_used_time(uid, user_id, bot_id, game_id=PGR_GAME_ID)
        return waves_user.cookie

    async def get_pgr_random_cookie(self, uid: str) -> Optional[str]:
        """随机获取一个有效的公共 PGR cookie"""
        from XutheringWavesUID.XutheringWavesUID.utils.database.models import WavesUser

        user_list = await WavesUser.get_waves_all_user()
        random.shuffle(user_list)
        for user in user_list:
            if user.game_id != PGR_GAME_ID:
                continue
            if not await WavesUser.cookie_validate(user.uid):
                continue

            data = await waves_api.login_log(user.uid, user.cookie)
            if not data.success:
                await data.mark_cookie_invalid(user.uid, user.cookie)
                continue

            return user.cookie
        return None

    async def get_ck_result(
        self, uid: str, user_id: str, bot_id: str
    ) -> Tuple[bool, Optional[str]]:
        """获取有效 cookie，先自己的，没有则用公共的

        Returns:
            (is_self_ck, cookie)
        """
        ck = await self.get_self_pgr_ck(uid, user_id, bot_id)
        if ck:
            await self.get_server_id(uid, ck)
            return True, ck
        ck = await self.get_pgr_random_cookie(uid)
        if ck:
            await self.get_server_id(uid, ck)
        return False, ck

    # ===== 刷新数据 =====

    async def refresh_data(
        self, role_id: str, token: str, server_id: Optional[str] = None
    ) -> KuroApiResp:
        """刷新战双数据（/haru/roleBox/refreshData）"""
        return await self._game_request(REFRESH_DATA_URL, role_id, token, server_id)

    # ===== 公告接口 =====

    async def get_ann_list_by_type(
        self, eventType: str = "", pageSize: Optional[int] = None
    ):
        data: Dict[str, Any] = {"gameId": PGR_GAME_ID}
        if eventType:
            data["eventType"] = eventType
        if pageSize:
            data["pageSize"] = pageSize
        headers = await get_community_header()
        return await self._request(ANN_LIST_URL, headers, data)

    async def get_ann_detail(self, post_id: str) -> dict:
        if post_id in self.ann_map:
            return self.ann_map[post_id]

        headers = await get_community_header()
        headers.update({"token": "", "devcode": ""})
        data = {"isOnlyPublisher": 1, "postId": post_id, "showOrderType": 2}
        res = await self._request(ANN_CONTENT_URL, headers, data)
        if res.success:
            raw_data = res.model_dump()
            if "headCodeUrl" in raw_data["data"]:
                raw_data["data"]["postDetail"]["headCodeUrl"] = raw_data["data"]["headCodeUrl"]
            self.ann_map[post_id] = raw_data["data"]["postDetail"]
            return raw_data["data"]["postDetail"]
        return {}

    async def get_ann_list(self, is_cache: bool = False) -> List[dict]:
        if is_cache and self.ann_list_data:
            return self.ann_list_data

        self.ann_list_data = []
        for _event in self.event_type.keys():
            res = await self.get_ann_list_by_type(eventType=_event, pageSize=9)
            if res.success:
                raw_data = res.model_dump()
                value = [{**x, "id": int(x["id"])} for x in raw_data["data"]["list"]]
                self.ann_list_data.extend(value)

        return self.ann_list_data

    async def get_bbs_list(
        self,
        otherUserId: Union[int, str],
        pageIndex: int = 1,
        pageSize: int = 10,
    ):
        headers = await get_community_header()
        headers.update({"token": "", "devCode": ""})
        data = {
            "searchType": 1,
            "type": 2,
            "otherUserId": otherUserId,
            "pageIndex": pageIndex,
            "pageSize": pageSize,
        }
        return await self._request(BBS_LIST, headers, data)

    # ===== 游戏数据接口 =====

    async def get_account_data(
        self, role_id: str, token: str, server_id: Optional[str] = None
    ) -> Optional[PGRAccountData]:
        """获取战双账号数据（等级/昵称/服务器/头像/段位）"""
        res = await self._game_request(ACCOUNT_DATA_URL, role_id, token, server_id)
        if res.success and res.data:
            return PGRAccountData.model_validate(res.data)
        return None

    async def get_base_data(
        self, role_id: str, token: str, server_id: Optional[str] = None
    ) -> Optional[PGRBaseData]:
        """获取战双基础数据"""
        res = await self._game_request(BASE_DATA_URL, role_id, token, server_id)
        if res.success and res.data:
            return PGRBaseData.model_validate(res.data)
        return None

    async def get_daily_data(
        self, role_id: str, token: str, server_id: Optional[str] = None
    ) -> Optional[PGRDailyData]:
        """获取战双日常数据（血清/委托/活跃/Boss）"""
        res = await self._game_request(
            DAILY_DATA_URL, role_id, token, server_id, extra_data={"type": "2"}
        )
        if res.success and res.data:
            return PGRDailyData.model_validate(res.data)
        return None

    async def get_role_index(
        self, role_id: str, token: str, server_id: Optional[str] = None
    ) -> Optional[PGRRoleIndexData]:
        """获取战双角色列表"""
        res = await self._game_request(ROLE_INDEX_URL, role_id, token, server_id)
        if res.success and res.data:
            return PGRRoleIndexData.model_validate(res.data)
        return None

    async def get_character_fashion(
        self, role_id: str, token: str, server_id: Optional[str] = None
    ) -> Optional[PGRFashionData]:
        """获取战双涂装/皮肤数据"""
        res = await self._game_request(CHARACTER_FASHION_URL, role_id, token, server_id)
        if res.success and res.data:
            return PGRFashionData.model_validate(res.data)
        return None

    async def get_half_year_data(
        self, role_id: str, token: str
    ) -> Optional[PGRHalfYearData]:
        """获取战双半年资源汇总（黑卡/研发资源/商店信用）"""
        headers = await get_base_header()
        headers["token"] = token
        data = {"roleId": role_id}
        res = await self._request(HALF_YEAR_URL, headers, data)
        if res.success and res.data:
            return PGRHalfYearData.model_validate(res.data)
        return None

    async def get_weapon_fashion(
        self, role_id: str, token: str, server_id: Optional[str] = None
    ) -> Optional[PGRWeaponFashionData]:
        """获取战双武器涂装数据"""
        res = await self._game_request(WEAPON_FASHION_URL, role_id, token, server_id)
        if res.success and res.data:
            return PGRWeaponFashionData.model_validate(res.data)
        return None

    async def get_prisoner_cage(
        self, role_id: str, token: str, server_id: Optional[str] = None
    ) -> Optional[PGRPrisonerCageData]:
        """获取战双幻痛囚笼数据"""
        res = await self._game_request(PRISONER_CAGE_URL, role_id, token, server_id)
        if res.success and res.data:
            return PGRPrisonerCageData.model_validate(res.data)
        return None

    async def get_area(
        self, role_id: str, token: str, server_id: Optional[str] = None
    ) -> Optional[PGRAreaData]:
        """获取战双纷争战区数据"""
        res = await self._game_request(AREA_URL, role_id, token, server_id)
        if res.success and res.data:
            return PGRAreaData.model_validate(res.data)
        return None

    async def get_chip_overclocking(
        self, role_id: str, token: str, server_id: Optional[str] = None
    ) -> Optional[PGRChipOverclockingData]:
        """获取战双芯片超频数据"""
        res = await self._game_request(CHIP_OVERCLOCKING_URL, role_id, token, server_id)
        if res.success and res.data:
            return PGRChipOverclockingData.model_validate(res.data)
        return None

    async def get_transfinite(
        self, role_id: str, token: str, server_id: Optional[str] = None
    ) -> Optional[PGRTransfiniteData]:
        """获取战双历战映射数据"""
        res = await self._game_request(TRANSFINITE_URL, role_id, token, server_id)
        if res.success and res.data:
            return PGRTransfiniteData.model_validate(res.data)
        return None

    async def get_stronghold(
        self, role_id: str, token: str, server_id: Optional[str] = None
    ) -> Optional[PGRStrongholdData]:
        """获取战双诺曼矿区数据"""
        res = await self._game_request(STRONGHOLD_URL, role_id, token, server_id)
        if res.success and res.data:
            return PGRStrongholdData.model_validate(res.data)
        return None

    async def get_role_detail(
        self, role_id: str, token: str, character_id: int, server_id: Optional[str] = None
    ) -> Optional[PGRRoleDetailData]:
        """获取战双角色详情（装备/武器/辅助机/芯片）"""
        res = await self._game_request(
            ROLE_DETAIL_URL, role_id, token, server_id,
            extra_data={"characterId": str(character_id)},
        )
        if res.success and res.data:
            return PGRRoleDetailData.model_validate(res.data)
        return None


pgr_api = PGRApi()
