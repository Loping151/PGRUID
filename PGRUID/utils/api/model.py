"""PGR API 响应模型"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ===== baseData =====

class PGRAccountData(BaseModel):
    """战双账号数据"""
    roleId: str = ""
    level: int = 0
    roleName: str = ""
    serverName: str = ""
    headIconUrl: str = ""
    rank: int = 0


class PGRBaseData(BaseModel):
    """战双基础数据"""
    show: bool = False
    characterCount: int = 0
    roleAllScore: int = 0
    achievement: int = 0
    scoreTitleCount: int = 0
    fashionProcess: str = "0.0%"
    storyProcess: str = "0%"
    grandTotalLoginNum: int = 0
    sgTreasureBoxCount: int = 0
    sgTreasureBoxTotalCount: int = 0


# ===== dailyData =====

class PGRDailyItem(BaseModel):
    """日常数据项（血清/委托/活跃/Boss等）"""
    name: Optional[str] = None
    key: Optional[str] = None
    refreshTimeStamp: Optional[int] = None
    expireTimeStamp: Optional[int] = None
    value: Optional[str] = ""
    status: int = 0
    cur: int = 0
    total: int = 0


class PGRDailyData(BaseModel):
    """战双日常数据"""
    serverTime: int = 0
    actionData: PGRDailyItem = Field(default_factory=PGRDailyItem)
    dormData: PGRDailyItem = Field(default_factory=PGRDailyItem)
    activeData: PGRDailyItem = Field(default_factory=PGRDailyItem)
    bossData: List[PGRDailyItem] = Field(default_factory=list)
    temporaryClose: bool = False


# ===== halfOfYear =====

class PGRMonthResource(BaseModel):
    """月度资源收入"""
    currentYear: int = 0
    currentMonth: int = 0
    month: str = ""
    monthBlackCard: int = 0
    monthDevelopResource: int = 0
    monthTradeCredit: int = 0
    isHighest: bool = False


class PGRHalfYearData(BaseModel):
    """半年资源汇总"""
    totalBlackCard: int = 0
    totalDevelopResource: int = 0
    totalTradeCredit: int = 0
    perMonthList: List[PGRMonthResource] = Field(default_factory=list)


# ===== roleIndex =====

class PGRCharacter(BaseModel):
    """角色信息"""
    bodyId: int = 0
    bodyName: str = ""
    iconUrl: str = ""
    element: str = ""
    effect: str = ""
    quality: Optional[int] = 0
    grade: str = ""
    fightAbility: Optional[int] = 0
    level: Optional[int] = 0
    roleRank: str = ""
    priority: int = 0
    weaponType: int = 0


class PGRRoleIndexData(BaseModel):
    """角色列表数据"""
    characterList: List[PGRCharacter] = Field(default_factory=list)
    showRoleIdList: Optional[List[int]] = None
    show: bool = False


# ===== characterFashion =====

class PGRFashionItem(BaseModel):
    """涂装/皮肤"""
    skinId: int = 0
    skinName: str = ""
    skinIcon: str = ""
    characterId: int = 0


class PGRFashionData(BaseModel):
    """涂装数据"""
    fashionList: List[PGRFashionItem] = Field(default_factory=list)
    topFashionList: List[PGRFashionItem] = Field(default_factory=list)
    rate: str = "0"
    show: bool = False


# ===== weaponFashion =====

class PGRWeaponFashionItem(BaseModel):
    """武器涂装"""
    skinId: int = 0
    skinName: str = ""
    skinIcon: str = ""
    equipType: int = 0


class PGRWeaponFashionData(BaseModel):
    """武器涂装数据"""
    fashionList: List[PGRWeaponFashionItem] = Field(default_factory=list)
    topFashionList: List[PGRWeaponFashionItem] = Field(default_factory=list)
    rate: str = "0"
    show: bool = False


# ===== prisonerCage (幻痛囚笼) =====

class PGRBossInfo(BaseModel):
    name: str = ""
    iconUrl: str = ""
    bossId: int = 0


class PGRStageBody(BaseModel):
    auto: bool = False
    bodyInfo: Optional[Dict[str, Any]] = None


class PGRStageInfo(BaseModel):
    point: int = 0
    autoFight: bool = False
    fightTime: int = 0
    stageName: str = ""
    bodyList: List[PGRStageBody] = Field(default_factory=list)


class PGRBossFightInfo(BaseModel):
    totalPoint: int = 0
    totalNum: int = 0
    boss: Optional[PGRBossInfo] = None
    stageInfoList: Optional[List[PGRStageInfo]] = Field(default_factory=list)


class PGRPrisonerCageInfo(BaseModel):
    totalPoint: int = 0
    totalChallengeTimes: int = 0
    bossFightInfoList: List[PGRBossFightInfo] = Field(default_factory=list)


class PGRPrisonerCageData(BaseModel):
    """幻痛囚笼数据"""
    show: bool = False
    isOpen: bool = False
    isUnlock: bool = False
    chooseArea: bool = False
    challengeArea: str = ""
    challengeLevel: str = ""
    prisonerCage: Optional[PGRPrisonerCageInfo] = None


# ===== area (纷争战区) =====

class PGRAreaInfo(BaseModel):
    totalPoint: int = 0
    totalChallengeTimes: int = 0
    stageFightInfoList: List[Dict[str, Any]] = Field(default_factory=list)


class PGRAreaData(BaseModel):
    """纷争战区数据"""
    show: bool = False
    isOpen: bool = False
    isUnlock: bool = False
    groupName: str = ""
    groupLevel: str = ""
    areaInfo: Optional[PGRAreaInfo] = None


# ===== getChipOverclocking (芯片超频) =====

class PGRChipSkill(BaseModel):
    skillId: int = 0
    skillDesc: str = ""
    skillIcon: str = ""
    pos: Optional[int] = None
    isActive: bool = False
    isRecommend: bool = False


class PGRChipOverclockingData(BaseModel):
    """芯片超频数据"""
    userChipSkill: Dict[str, List[PGRChipSkill]] = Field(default_factory=dict)
    notUserChipSkill: Dict[str, List[PGRChipSkill]] = Field(default_factory=dict)


# ===== transfinite (历战映射) =====

class PGRTransfiniteData(BaseModel):
    """历战映射数据"""
    show: bool = False
    isOpen: bool = False
    isUnlock: bool = False
    operatorArea: str = ""
    challengeArea: str = ""
    challengeLevel: str = ""
    bossIconUrl: str = ""
    operatorCount: int = 0
    process: int = 0
    fightTime: int = 0
    characterList: List[PGRCharacter] = Field(default_factory=list)


# ===== stronghold (诺曼矿区) =====

class PGRBuffInfo(BaseModel):
    name: str = ""
    iconUrl: str = ""
    buffId: int = 0


class PGRGroupBuff(BaseModel):
    groupId: str = ""
    isComplete: bool = False
    buff: Optional[PGRBuffInfo] = None


class PGRStrongholdGroup(BaseModel):
    groupId: str = ""
    groupName: str = ""
    order: int = 0
    isUnlock: bool = False
    pass_: bool = Field(default=False, alias="pass")
    completeBuffNum: int = 0
    buffList: List[PGRGroupBuff] = Field(default_factory=list)


class PGRStrongholdTeam(BaseModel):
    element: Optional[Dict[str, Any]] = None
    electricNum: int = 0
    rune: Optional[Dict[str, Any]] = None
    characterList: List[PGRCharacter] = Field(default_factory=list)


class PGRStrongholdData(BaseModel):
    """诺曼矿区数据"""
    show: bool = False
    isOpen: bool = False
    isUnlock: bool = False
    challengeArea: str = ""
    challengeLevel: str = ""
    groupList: List[PGRStrongholdGroup] = Field(default_factory=list)
    teamList: List[PGRStrongholdTeam] = Field(default_factory=list)


# ===== roleDetail (角色详情) =====

class PGRBodyInfo(BaseModel):
    """角色本体信息"""
    bodyId: int = 0
    roleName: str = ""
    bodyName: str = ""
    careerId: int = 0
    career: str = ""
    isNewRole: int = 0
    iconUrl: str = ""
    imgUrl: str = ""
    element: str = ""
    elementDetail: str = ""
    effect: str = ""
    wikiLink: str = ""
    roleRank: str = ""
    priority: int = 0
    weaponType: int = 0


class PGRWeaponDetail(BaseModel):
    """武器信息"""
    name: str = ""
    iconUrl: str = ""
    weaponId: int = 0
    skillName: str = ""
    skillDescription: str = ""


class PGRSuitDetail(BaseModel):
    """意识套装"""
    name: str = ""
    iconUrl: str = ""
    suitId: int = 0
    skillDescriptionTwo: str = ""
    skillDescriptionFour: str = ""
    skillDescriptionSix: Optional[str] = None


class PGRResonance(BaseModel):
    """武器共鸣"""
    name: str = ""
    iconUrl: str = ""
    skillId: int = 0
    skillDescription: str = ""


class PGRWeaponInfo(BaseModel):
    """武器完整信息"""
    weapon: Optional[PGRWeaponDetail] = None
    overRunLevel: int = 0
    quality: int = 0
    suit: Optional[PGRSuitDetail] = None
    resonanceList: List[PGRResonance] = Field(default_factory=list)


class PGRPartnerInfo(BaseModel):
    """辅助机信息"""
    name: str = ""
    iconUrl: str = ""
    partnerId: int = 0
    grade: int = 0
    gradeStr: Optional[str] = None


class PGRPartnerSkill(BaseModel):
    """辅助机技能"""
    name: str = ""
    iconUrl: str = ""
    level: int = 0
    description: str = ""


class PGRPartner(BaseModel):
    """辅助机完整信息"""
    partner: Optional[PGRPartnerInfo] = None
    level: int = 0
    breakThrough: int = 0
    grade: str = ""
    quality: int = 0
    skillList: List[PGRPartnerSkill] = Field(default_factory=list)


class PGRChipSuit(BaseModel):
    """芯片套装"""
    name: str = ""
    iconUrl: str = ""
    suitId: int = 0
    num: int = 0
    descriptionTwo: str = ""
    descriptionFour: str = ""
    descriptionSix: Optional[str] = None


class PGRChipResonance(BaseModel):
    """芯片共鸣槽"""
    chipIconUrl: str = ""
    site: int = 0
    chipName: str = ""
    defend: bool = False
    superSlotIconUrl: str = ""
    superAwake: bool = False
    superDescription: str = ""
    subSlotIconUrl: str = ""
    subAwake: bool = False
    subDescription: str = ""


class PGRCharacterDetail(BaseModel):
    """角色详情（含装备）"""
    body: Optional[PGRBodyInfo] = None
    quality: int = 0
    grade: str = ""
    fightAbility: int = 0
    weaponInfo: Optional[PGRWeaponInfo] = None
    partner: Optional[PGRPartner] = None
    chipSuitList: List[PGRChipSuit] = Field(default_factory=list)
    chipResonanceList: List[PGRChipResonance] = Field(default_factory=list)
    chipExDamage: str = ""


class PGRRoleDetailData(BaseModel):
    """角色详情响应"""
    character: Optional[PGRCharacterDetail] = None
    show: bool = False
