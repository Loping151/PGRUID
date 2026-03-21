"""PGR API 响应模型"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ===== baseData =====

class PGRAccountData(BaseModel):
    """战双账号数据"""
    roleId: Optional[str] = ""
    level: Optional[int] = 0
    roleName: Optional[str] = ""
    serverName: Optional[str] = ""
    headIconUrl: Optional[str] = ""
    rank: Optional[int] = 0


class PGRBaseData(BaseModel):
    """战双基础数据"""
    show: Optional[bool] = False
    characterCount: Optional[int] = 0
    roleAllScore: Optional[int] = 0
    achievement: Optional[int] = 0
    scoreTitleCount: Optional[int] = 0
    fashionProcess: Optional[str] = "0.0%"
    storyProcess: Optional[str] = "0%"
    grandTotalLoginNum: Optional[int] = 0
    sgTreasureBoxCount: Optional[int] = 0
    sgTreasureBoxTotalCount: Optional[int] = 0


# ===== dailyData =====

class PGRDailyItem(BaseModel):
    """日常数据项（血清/委托/活跃/Boss等）"""
    name: Optional[str] = None
    key: Optional[str] = None
    refreshTimeStamp: Optional[int] = None
    expireTimeStamp: Optional[int] = None
    value: Optional[str] = ""
    status: Optional[int] = 0
    cur: Optional[int] = 0
    total: Optional[int] = 0


class PGRDailyData(BaseModel):
    """战双日常数据"""
    serverTime: Optional[int] = 0
    actionData: PGRDailyItem = Field(default_factory=PGRDailyItem)
    dormData: PGRDailyItem = Field(default_factory=PGRDailyItem)
    activeData: PGRDailyItem = Field(default_factory=PGRDailyItem)
    bossData: List[PGRDailyItem] = Field(default_factory=list)
    temporaryClose: Optional[bool] = False


# ===== halfOfYear =====

class PGRMonthResource(BaseModel):
    """月度资源收入"""
    currentYear: Optional[int] = 0
    currentMonth: Optional[int] = 0
    month: Optional[str] = ""
    monthBlackCard: Optional[int] = 0
    monthDevelopResource: Optional[int] = 0
    monthTradeCredit: Optional[int] = 0
    isHighest: Optional[bool] = False


class PGRHalfYearData(BaseModel):
    """半年资源汇总"""
    totalBlackCard: Optional[int] = 0
    totalDevelopResource: Optional[int] = 0
    totalTradeCredit: Optional[int] = 0
    perMonthList: List[PGRMonthResource] = Field(default_factory=list)


# ===== roleIndex =====

class PGRCharacter(BaseModel):
    """角色信息"""
    bodyId: Optional[int] = 0
    bodyName: Optional[str] = ""
    iconUrl: Optional[str] = ""
    element: Optional[str] = ""
    effect: Optional[str] = ""
    quality: Optional[int] = 0
    grade: Optional[str] = ""
    fightAbility: Optional[int] = 0
    level: Optional[int] = 0
    roleRank: Optional[str] = ""
    priority: Optional[int] = 0
    weaponType: Optional[int] = 0


class PGRRoleIndexData(BaseModel):
    """角色列表数据"""
    characterList: Optional[List[PGRCharacter]] = Field(default_factory=list)
    showRoleIdList: Optional[List[int]] = None
    show: Optional[bool] = False


# ===== characterFashion =====

class PGRFashionItem(BaseModel):
    """涂装/皮肤"""
    skinId: Optional[int] = 0
    skinName: Optional[str] = ""
    skinIcon: Optional[str] = ""
    characterId: Optional[int] = 0


class PGRFashionData(BaseModel):
    """涂装数据"""
    fashionList: Optional[List[PGRFashionItem]] = Field(default_factory=list)
    topFashionList: Optional[List[PGRFashionItem]] = Field(default_factory=list)
    rate: Optional[str] = "0"
    show: Optional[bool] = False


# ===== weaponFashion =====

class PGRWeaponFashionItem(BaseModel):
    """武器涂装"""
    skinId: Optional[int] = 0
    skinName: Optional[str] = ""
    skinIcon: Optional[str] = ""
    equipType: Optional[int] = 0


class PGRWeaponFashionData(BaseModel):
    """武器涂装数据"""
    fashionList: Optional[List[PGRWeaponFashionItem]] = Field(default_factory=list)
    topFashionList: Optional[List[PGRWeaponFashionItem]] = Field(default_factory=list)
    rate: Optional[str] = "0"
    show: Optional[bool] = False


# ===== prisonerCage (幻痛囚笼) =====

class PGRBossInfo(BaseModel):
    name: Optional[str] = ""
    iconUrl: Optional[str] = ""
    bossId: Optional[int] = 0


class PGRStageBody(BaseModel):
    auto: bool = False
    bodyInfo: Optional[Dict[str, Any]] = None


class PGRStageInfo(BaseModel):
    point: Optional[int] = 0
    autoFight: Optional[bool] = False
    fightTime: Optional[int] = 0
    stageName: Optional[str] = ""
    bodyList: Optional[List[PGRStageBody]] = Field(default_factory=list)


class PGRBossFightInfo(BaseModel):
    totalPoint: Optional[int] = 0
    totalNum: Optional[int] = 0
    boss: Optional[PGRBossInfo] = None
    stageInfoList: Optional[List[PGRStageInfo]] = Field(default_factory=list)


class PGRPrisonerCageInfo(BaseModel):
    totalPoint: Optional[int] = 0
    totalChallengeTimes: Optional[int] = 0
    bossFightInfoList: Optional[List[PGRBossFightInfo]] = Field(default_factory=list)


class PGRPrisonerCageData(BaseModel):
    """幻痛囚笼数据"""
    show: Optional[bool] = False
    isOpen: Optional[bool] = False
    isUnlock: Optional[bool] = False
    chooseArea: Optional[bool] = False
    challengeArea: Optional[str] = ""
    challengeLevel: Optional[str] = ""
    prisonerCage: Optional[PGRPrisonerCageInfo] = None


# ===== area (纷争战区) =====

class PGRAreaInfo(BaseModel):
    totalPoint: Optional[int] = 0
    totalChallengeTimes: Optional[int] = 0
    stageFightInfoList: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class PGRAreaData(BaseModel):
    """纷争战区数据"""
    show: Optional[bool] = False
    isOpen: Optional[bool] = False
    isUnlock: Optional[bool] = False
    groupName: Optional[str] = ""
    groupLevel: Optional[str] = ""
    areaInfo: Optional[PGRAreaInfo] = None


# ===== getChipOverclocking (芯片超频) =====

class PGRChipSkill(BaseModel):
    skillId: Optional[int] = 0
    skillDesc: Optional[str] = ""
    skillIcon: Optional[str] = ""
    pos: Optional[int] = None
    isActive: Optional[bool] = False
    isRecommend: Optional[bool] = False


class PGRChipOverclockingData(BaseModel):
    """芯片超频数据"""
    userChipSkill: Dict[str, List[PGRChipSkill]] = Field(default_factory=dict)
    notUserChipSkill: Dict[str, List[PGRChipSkill]] = Field(default_factory=dict)


# ===== transfinite (历战映射) =====

class PGRTransfiniteData(BaseModel):
    """历战映射数据"""
    show: Optional[bool] = False
    isOpen: Optional[bool] = False
    isUnlock: Optional[bool] = False
    operatorArea: Optional[str] = ""
    challengeArea: Optional[str] = ""
    challengeLevel: Optional[str] = ""
    bossIconUrl: Optional[str] = ""
    operatorCount: Optional[int] = 0
    process: Optional[int] = 0
    fightTime: Optional[int] = 0
    characterList: List[PGRCharacter] = Field(default_factory=list)


# ===== stronghold (诺曼矿区) =====

class PGRBuffInfo(BaseModel):
    name: Optional[str] = ""
    iconUrl: Optional[str] = ""
    buffId: Optional[int] = 0


class PGRGroupBuff(BaseModel):
    groupId: Optional[str] = ""
    isComplete: Optional[bool] = False
    buff: Optional[PGRBuffInfo] = None


class PGRStrongholdGroup(BaseModel):
    groupId: Optional[str] = ""
    groupName: Optional[str] = ""
    order: Optional[int] = 0
    isUnlock: Optional[bool] = False
    pass_: Optional[bool] = Field(default=False, alias="pass")
    completeBuffNum: Optional[int] = 0
    buffList: List[PGRGroupBuff] = Field(default_factory=list)


class PGRStrongholdTeam(BaseModel):
    element: Optional[Dict[str, Any]] = None
    electricNum: Optional[int] = 0
    rune: Optional[Dict[str, Any]] = None
    characterList: List[PGRCharacter] = Field(default_factory=list)


class PGRStrongholdData(BaseModel):
    """诺曼矿区数据"""
    show: Optional[bool] = False
    isOpen: Optional[bool] = False
    isUnlock: Optional[bool] = False
    challengeArea: Optional[str] = ""
    challengeLevel: Optional[str] = ""
    groupList: List[PGRStrongholdGroup] = Field(default_factory=list)
    teamList: List[PGRStrongholdTeam] = Field(default_factory=list)


# ===== roleDetail (角色详情) =====

class PGRBodyInfo(BaseModel):
    """角色本体信息"""
    bodyId: Optional[int] = 0
    roleName: Optional[str] = ""
    bodyName: Optional[str] = ""
    careerId: Optional[int] = 0
    career: Optional[str] = ""
    isNewRole: Optional[int] = 0
    iconUrl: Optional[str] = ""
    imgUrl: Optional[str] = ""
    element: Optional[str] = ""
    elementDetail: Optional[str] = ""
    effect: Optional[str] = ""
    wikiLink: Optional[str] = ""
    roleRank: Optional[str] = ""
    priority: Optional[int] = 0
    weaponType: Optional[int] = 0


class PGRWeaponDetail(BaseModel):
    """武器信息"""
    name: Optional[str] = ""
    iconUrl: Optional[str] = ""
    weaponId: Optional[int] = 0
    skillName: Optional[str] = ""
    skillDescription: Optional[str] = ""


class PGRSuitDetail(BaseModel):
    """意识套装"""
    name: Optional[str] = ""
    iconUrl: Optional[str] = ""
    suitId: Optional[int] = 0
    skillDescriptionTwo: Optional[str] = ""
    skillDescriptionFour: Optional[str] = ""
    skillDescriptionSix: Optional[str] = None


class PGRResonance(BaseModel):
    """武器共鸣"""
    name: Optional[str] = ""
    iconUrl: Optional[str] = ""
    skillId: Optional[int] = 0
    skillDescription: Optional[str] = ""


class PGRWeaponInfo(BaseModel):
    """武器完整信息"""
    weapon: Optional[PGRWeaponDetail] = None
    overRunLevel: Optional[int] = 0
    quality: Optional[int] = 0
    suit: Optional[PGRSuitDetail] = None
    resonanceList: List[PGRResonance] = Field(default_factory=list)


class PGRPartnerInfo(BaseModel):
    """辅助机信息"""
    name: Optional[str] = ""
    iconUrl: Optional[str] = ""
    partnerId: Optional[int] = 0
    grade: Optional[int] = 0
    gradeStr: Optional[str] = None


class PGRPartnerSkill(BaseModel):
    """辅助机技能"""
    name: Optional[str] = ""
    iconUrl: Optional[str] = ""
    level: Optional[int] = 0
    description: Optional[str] = ""


class PGRPartner(BaseModel):
    """辅助机完整信息"""
    partner: Optional[PGRPartnerInfo] = None
    level: Optional[int] = 0
    breakThrough: Optional[int] = 0
    grade: Optional[str] = ""
    quality: Optional[int] = 0
    skillList: List[PGRPartnerSkill] = Field(default_factory=list)


class PGRChipSuit(BaseModel):
    """芯片套装"""
    name: Optional[str] = ""
    iconUrl: Optional[str] = ""
    suitId: Optional[int] = 0
    num: Optional[int] = 0
    descriptionTwo: Optional[str] = ""
    descriptionFour: Optional[str] = ""
    descriptionSix: Optional[str] = None


class PGRChipResonance(BaseModel):
    """芯片共鸣槽"""
    chipIconUrl: Optional[str] = ""
    site: Optional[int] = 0
    chipName: Optional[str] = ""
    defend: Optional[bool] = False
    superSlotIconUrl: Optional[str] = ""
    superAwake: Optional[bool] = False
    superDescription: Optional[str] = ""
    subSlotIconUrl: Optional[str] = ""
    subAwake: Optional[bool] = False
    subDescription: Optional[str] = ""


class PGRCharacterDetail(BaseModel):
    """角色详情（含装备）"""
    body: Optional[PGRBodyInfo] = None
    quality: Optional[int] = 0
    grade: Optional[str] = ""
    fightAbility: Optional[int] = 0
    weaponInfo: Optional[PGRWeaponInfo] = None
    partner: Optional[PGRPartner] = None
    chipSuitList: List[PGRChipSuit] = Field(default_factory=list)
    chipResonanceList: List[PGRChipResonance] = Field(default_factory=list)
    chipExDamage: Optional[str] = ""


class PGRRoleDetailData(BaseModel):
    """角色详情响应"""
    character: Optional[PGRCharacterDetail] = None
    show: Optional[bool] = False
