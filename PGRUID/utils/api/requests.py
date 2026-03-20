"""PGR API 请求模块

直接复用 xwuid 的请求底层（代理池、重试、session 管理等），只定义 PGR 的 API 端点
"""
from typing import Any, Dict, List, Union, Optional

from gsuid_core.logger import logger

from .api import (
    ANN_LIST_URL,
    ANN_CONTENT_URL,
    BBS_LIST,
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

    # ===== 刷新数据 =====

    async def refresh_data(
        self, role_id: str, token: str, server_id: str = "1000"
    ) -> KuroApiResp:
        """刷新战双数据（/haru/roleBox/refreshData）"""
        headers = await get_base_header()
        headers["token"] = token
        data = {"serverId": server_id, "roleId": role_id}
        return await self._request(REFRESH_DATA_URL, headers, data)

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
        self, role_id: str, token: str, server_id: str = "1000"
    ) -> Optional[PGRAccountData]:
        """获取战双账号数据（等级/昵称/服务器/头像/段位）"""
        headers = await get_base_header()
        headers["token"] = token
        data = {"serverId": server_id, "roleId": role_id}
        res = await self._request(ACCOUNT_DATA_URL, headers, data)
        if res.success and res.data:
            return PGRAccountData.model_validate(res.data)
        return None

    async def get_base_data(
        self, role_id: str, token: str, server_id: str = "1000"
    ) -> Optional[PGRBaseData]:
        """获取战双基础数据"""
        headers = await get_base_header()
        headers["token"] = token
        data = {"serverId": server_id, "roleId": role_id}
        res = await self._request(BASE_DATA_URL, headers, data)
        if res.success and res.data:
            return PGRBaseData.model_validate(res.data)
        return None

    async def get_daily_data(
        self, role_id: str, token: str, server_id: str = "1000"
    ) -> Optional[PGRDailyData]:
        """获取战双日常数据（血清/委托/活跃/Boss）"""
        headers = await get_base_header()
        headers["token"] = token
        data = {"type": "2", "serverId": server_id, "roleId": role_id}
        res = await self._request(DAILY_DATA_URL, headers, data)
        if res.success and res.data:
            return PGRDailyData.model_validate(res.data)
        return None


    async def get_role_index(
        self, role_id: str, token: str, server_id: str = "1000"
    ) -> Optional[PGRRoleIndexData]:
        """获取战双角色列表"""
        headers = await get_base_header()
        headers["token"] = token
        data = {"serverId": server_id, "roleId": role_id}
        res = await self._request(ROLE_INDEX_URL, headers, data)
        if res.success and res.data:
            return PGRRoleIndexData.model_validate(res.data)
        return None

    async def get_character_fashion(
        self, role_id: str, token: str, server_id: str = "1000"
    ) -> Optional[PGRFashionData]:
        """获取战双涂装/皮肤数据"""
        headers = await get_base_header()
        headers["token"] = token
        data = {"serverId": server_id, "roleId": role_id}
        res = await self._request(CHARACTER_FASHION_URL, headers, data)
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
        self, role_id: str, token: str, server_id: str = "1000"
    ) -> Optional[PGRWeaponFashionData]:
        """获取战双武器涂装数据"""
        headers = await get_base_header()
        headers["token"] = token
        data = {"serverId": server_id, "roleId": role_id}
        res = await self._request(WEAPON_FASHION_URL, headers, data)
        if res.success and res.data:
            return PGRWeaponFashionData.model_validate(res.data)
        return None

    async def get_prisoner_cage(
        self, role_id: str, token: str, server_id: str = "1000"
    ) -> Optional[PGRPrisonerCageData]:
        """获取战双幻痛囚笼数据"""
        headers = await get_base_header()
        headers["token"] = token
        data = {"serverId": server_id, "roleId": role_id}
        res = await self._request(PRISONER_CAGE_URL, headers, data)
        if res.success and res.data:
            return PGRPrisonerCageData.model_validate(res.data)
        return None

    async def get_area(
        self, role_id: str, token: str, server_id: str = "1000"
    ) -> Optional[PGRAreaData]:
        """获取战双纷争战区数据"""
        headers = await get_base_header()
        headers["token"] = token
        data = {"serverId": server_id, "roleId": role_id}
        res = await self._request(AREA_URL, headers, data)
        if res.success and res.data:
            return PGRAreaData.model_validate(res.data)
        return None

    async def get_chip_overclocking(
        self, role_id: str, token: str, server_id: str = "1000"
    ) -> Optional[PGRChipOverclockingData]:
        """获取战双芯片超频数据"""
        headers = await get_base_header()
        headers["token"] = token
        data = {"serverId": server_id, "roleId": role_id}
        res = await self._request(CHIP_OVERCLOCKING_URL, headers, data)
        if res.success and res.data:
            return PGRChipOverclockingData.model_validate(res.data)
        return None

    async def get_transfinite(
        self, role_id: str, token: str, server_id: str = "1000"
    ) -> Optional[PGRTransfiniteData]:
        """获取战双历战映射数据"""
        headers = await get_base_header()
        headers["token"] = token
        data = {"serverId": server_id, "roleId": role_id}
        res = await self._request(TRANSFINITE_URL, headers, data)
        if res.success and res.data:
            return PGRTransfiniteData.model_validate(res.data)
        return None

    async def get_stronghold(
        self, role_id: str, token: str, server_id: str = "1000"
    ) -> Optional[PGRStrongholdData]:
        """获取战双诺曼矿区数据"""
        headers = await get_base_header()
        headers["token"] = token
        data = {"serverId": server_id, "roleId": role_id}
        res = await self._request(STRONGHOLD_URL, headers, data)
        if res.success and res.data:
            return PGRStrongholdData.model_validate(res.data)
        return None


    async def get_role_detail(
        self, role_id: str, token: str, character_id: int, server_id: str = "1000"
    ) -> Optional[PGRRoleDetailData]:
        """获取战双角色详情（装备/武器/辅助机/芯片）"""
        headers = await get_base_header()
        headers["token"] = token
        data = {"serverId": server_id, "roleId": role_id, "characterId": str(character_id)}
        res = await self._request(ROLE_DETAIL_URL, headers, data)
        if res.success and res.data:
            return PGRRoleDetailData.model_validate(res.data)
        return None


pgr_api = PGRApi()
