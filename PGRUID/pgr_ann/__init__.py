import time
import random
import asyncio
from pathlib import Path

from gsuid_core.sv import SV
from gsuid_core.aps import scheduler
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.subscribe import gs_subscribe

from .ann_card import ann_list_card, ann_detail_card
from ..utils.api.requests import pgr_api
from ..pgr_config.config_default import PGRConfig
from ..pgr_config.ann_config import get_ann_new_ids, set_ann_new_ids
from ..utils.path import ANN_CACHE_PATH, BAKE_PATH
from ..utils.database.models import WavesSubscribe

sv_ann = SV("战双公告")
sv_ann_clear_cache = SV("战双公告缓存清理", pm=0, priority=3)
sv_ann_sub = SV("订阅战双公告", pm=3)

task_name_ann = "订阅战双公告"
ann_minute_check: int = PGRConfig.get_config("AnnMinuteCheck").data


@sv_ann.on_command("公告")
async def ann_(bot: Bot, ev: Event):
    ann_id = ev.text
    if not ann_id or ann_id.strip() == "列表":
        try:
            img = await ann_list_card()
            return await bot.send(img)
        except Exception as e:
            return await bot.send(f"获取公告列表失败: {e}")

    ann_id = ann_id.replace("#", "")

    if ann_id.isdigit():
        img = await ann_detail_card(int(ann_id))
    else:
        from .utils.post_id_mapper import get_post_id_from_short
        post_id = get_post_id_from_short(ann_id)
        if post_id:
            if post_id.isdigit():
                img = await ann_detail_card(int(post_id))
            else:
                img = await ann_detail_card(post_id)
        else:
            return await bot.send("未找到对应的公告ID，请确认输入是否正确")

    return await bot.send(img)  # type: ignore


@sv_ann_sub.on_fullmatch(("订阅公告", "訂閱公告"))
async def sub_ann_(bot: Bot, ev: Event):
    if ev.bot_id != "onebot" and ev.bot_id != "feishu" and ev.bot_id != "lark":
        return

    if ev.group_id is None:
        return await bot.send("请在群聊中订阅")
    if not PGRConfig.get_config("PGRAnnOpen").data:
        return await bot.send("战双公告推送功能已关闭")

    data = await gs_subscribe.get_subscribe(task_name_ann)
    is_resubscribe = False
    if data:
        for subscribe in data:
            if subscribe.group_id == ev.group_id:
                await gs_subscribe.delete_subscribe("session", task_name_ann, ev)
                is_resubscribe = True
                break

    await gs_subscribe.add_subscribe(
        "session",
        task_name=task_name_ann,
        event=ev,
        extra_message="",
    )

    if is_resubscribe:
        await bot.send("已重新订阅战双公告！")
    else:
        await bot.send("成功订阅战双公告!")


@sv_ann_sub.on_fullmatch(("取消订阅公告", "取消公告", "退订公告", "取消訂閱公告", "退訂公告"))
async def unsub_ann_(bot: Bot, ev: Event):
    if ev.bot_id != "onebot" and ev.bot_id != "feishu" and ev.bot_id != "lark":
        return

    if ev.group_id is None:
        return await bot.send("请在群聊中取消订阅")

    data = await gs_subscribe.get_subscribe(task_name_ann)
    if data:
        for subscribe in data:
            if subscribe.group_id == ev.group_id:
                await gs_subscribe.delete_subscribe("session", task_name_ann, ev)
                return await bot.send("成功取消订阅战双公告!")
    else:
        if not PGRConfig.get_config("PGRAnnOpen").data:
            return await bot.send("战双公告推送功能已关闭")

    return await bot.send("未曾订阅战双公告！")


@scheduler.scheduled_job("interval", minutes=ann_minute_check)
async def pgr_check_ann_job():
    if not PGRConfig.get_config("PGRAnnOpen").data:
        return
    await check_pgr_ann_state()


async def check_pgr_ann_state():
    logger.info("[PGRUID公告] 定时任务: 战双公告查询..")
    datas = await gs_subscribe.get_subscribe(task_name_ann)
    if not datas:
        logger.info("[PGRUID公告] 暂无群订阅")
        return

    ids = get_ann_new_ids()
    new_ann_list = await pgr_api.get_ann_list()
    if not new_ann_list:
        return

    new_ann_ids = [x["id"] for x in new_ann_list]
    if not ids:
        set_ann_new_ids(new_ann_ids)
        logger.info("[PGRUID公告] 初始成功, 将在下个轮询中更新.")
        return

    new_ann_need_send = []
    for ann_id in new_ann_ids:
        if ann_id not in ids:
            new_ann_need_send.append(ann_id)

    if not new_ann_need_send:
        logger.info("[PGRUID公告] 没有最新公告")
        return

    logger.info(f"[PGRUID公告] 更新公告id: {new_ann_need_send}")
    save_ids = sorted(ids, reverse=True) + new_ann_ids
    set_ann_new_ids(list(set(save_ids)))

    for ann_id in new_ann_need_send:
        try:
            img = await ann_detail_card(ann_id, is_check_time=True)
            if isinstance(img, str):
                continue
            for subscribe in datas:
                if subscribe.group_id:
                    latest_bot = await WavesSubscribe.get_group_bot(subscribe.group_id)
                    if latest_bot and latest_bot != subscribe.bot_self_id:
                        subscribe.bot_self_id = latest_bot
                await subscribe.send(img)  # type: ignore
                await asyncio.sleep(random.uniform(1, 3))
        except Exception as e:
            logger.exception(e)

    logger.info("[PGRUID公告] 推送完毕")


# ===== 缓存清理 =====

def clean_old_cache_files(directory: Path, days: int) -> tuple[int, float]:
    if not directory.exists():
        return 0, 0.0
    current_time = time.time()
    cutoff_time = current_time - (days * 86400)
    deleted_count = 0
    freed_space = 0.0
    try:
        for file_path in directory.iterdir():
            if not file_path.is_file():
                continue
            if file_path.stat().st_ctime < cutoff_time:
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_count += 1
                    freed_space += file_size
                except Exception as e:
                    logger.error(f"删除文件失败 {file_path.name}: {e}")
    except Exception as e:
        logger.error(f"清理目录失败 {directory}: {e}")
    return deleted_count, freed_space / (1024 * 1024)


async def clean_cache_directories(days: int) -> str:
    results = []
    total_count = 0
    total_space = 0.0

    ann_count, ann_space = clean_old_cache_files(ANN_CACHE_PATH, days)
    if ann_count > 0:
        results.append(f"公告: {ann_count}个文件, {ann_space:.2f}MB")
        total_count += ann_count
        total_space += ann_space

    bake_count, bake_space = 0, 0.0
    if BAKE_PATH.exists():
        cutoff = time.time() - (days * 86400)
        for f in BAKE_PATH.rglob("*"):
            if f.is_file() and f.stat().st_ctime < cutoff:
                try:
                    sz = f.stat().st_size
                    f.unlink()
                    bake_count += 1
                    bake_space += sz
                except Exception:
                    pass
    if bake_count > 0:
        results.append(f"烘焙: {bake_count}个文件, {bake_space / 1024 / 1024:.2f}MB")
        total_count += bake_count
        total_space += bake_space / 1024 / 1024

    if total_count == 0:
        return f"没有找到需要清理的缓存文件(公告/烘焙保留{days}天内的文件)"

    result_msg = f"[战双] 清理完成！共删除{total_count}个文件，{total_space:.2f}MB\n"
    result_msg += "\n".join(f" - {r}" for r in results)
    return result_msg


@sv_ann_clear_cache.on_fullmatch(("清理缓存", "删除缓存", "清理緩存", "刪除緩存"), block=True)
async def pgr_clean_cache_(bot: Bot, ev: Event):
    days = PGRConfig.get_config("CacheDaysToKeep").data
    logger.info(f"[PGRUID缓存清理] 手动触发清理，保留{days}天内的文件")
    result = await clean_cache_directories(days)
    await bot.send(result)


@scheduler.scheduled_job("cron", hour=3, minute=10)
async def pgr_auto_clean_cache_daily():
    days = PGRConfig.get_config("CacheDaysToKeep").data
    result = await clean_cache_directories(days)
    logger.info(f"[PGRUID缓存清理] {result}")


@scheduler.scheduled_job("date")
async def pgr_clean_cache_on_startup():
    await asyncio.sleep(8)
    days = PGRConfig.get_config("CacheDaysToKeep").data
    result = await clean_cache_directories(days)
    logger.info(f"[PGRUID缓存清理] {result}")
