import os
import json
import asyncio
from nonebot import on_command, on_message, get_driver
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.log import logger
import time
from typing import Dict, List, Tuple, Set
from collections import defaultdict

from .data_manager import bot_manager

# --- Configuration Loading ---
config = get_driver().config
ENABLED_GROUPS: Set[int] = set()
enabled_groups_config = getattr(config, "enabled_groups", [])
if enabled_groups_config:
    ENABLED_GROUPS = set(int(g) for g in enabled_groups_config)

def is_group_enabled(group_id: int) -> bool:
    """Check if the feature is enabled for the given group."""
    if not ENABLED_GROUPS:
        return True
    return group_id in ENABLED_GROUPS

# --- Command Handlers ---

add_bot_cmd = on_command("add_bot", permission=SUPERUSER, priority=10, block=True)
del_bot_cmd = on_command("del_bot", permission=SUPERUSER, priority=10, block=True)
list_bots_cmd = on_command("list_bots", permission=SUPERUSER, priority=10, block=True)
update_cmd = on_command("update", permission=SUPERUSER, priority=10, block=True)

@update_cmd.handle()
async def handle_update():
    await update_cmd.send("正在检查更新...")
    try:
        # Check if git is available
        proc = await asyncio.create_subprocess_shell(
            "git --version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if proc.returncode != 0:
            await update_cmd.finish("未找到 git 命令，无法自动更新。")
            return

        # Pull changes
        # Use subprocess to run git pull
        proc = await asyncio.create_subprocess_shell(
            "git pull",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        output = stdout.decode('utf-8', errors='replace').strip()
        
        if proc.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='replace').strip()
            # If git fails, it usually won't touch files, so .env and bots.json are safe.
            await update_cmd.finish(f"更新失败:\n{error_msg}")
            return
            
        if "Already up to date" in output or "已经是最新" in output:
            await update_cmd.finish("当前已是最新版本。")
            return
            
        await update_cmd.send(f"更新成功:\n{output}\n注意：.env 和 bots.json 不会被覆盖。\n请手动重启机器人以应用更改。")
        
    except Exception as e:
        logger.error(f"Update failed: {e}")
        await update_cmd.finish(f"更新过程中发生错误: {e}")

@add_bot_cmd.handle()
async def handle_add_bot(event: GroupMessageEvent, args: Message = CommandArg()):
    if not is_group_enabled(event.group_id):
        return

    # Check for mentions first
    at_users = [
        int(seg.data["qq"]) 
        for seg in event.message 
        if seg.type == "at" and seg.data.get("qq") != "all"
    ]
    
    # Check for plain text argument if no mentions
    if not at_users:
        qq_str = args.extract_plain_text().strip()
        if qq_str.isdigit():
            at_users.append(int(qq_str))
    
    if not at_users:
        await add_bot_cmd.finish("请提供有效的 QQ 号或 @ 机器人。")
        return

    added_bots = []
    for qq in at_users:
        if bot_manager.add_bot(qq):
            added_bots.append(str(qq))
    
    if added_bots:
        await add_bot_cmd.finish(f"机器人 {', '.join(added_bots)} 已添加到监控列表。")
    else:
        await add_bot_cmd.finish("指定的机器人已在列表中。")

@del_bot_cmd.handle()
async def handle_del_bot(event: GroupMessageEvent, args: Message = CommandArg()):
    if not is_group_enabled(event.group_id):
        return

    # Check for mentions first
    at_users = [
        int(seg.data["qq"]) 
        for seg in event.message 
        if seg.type == "at" and seg.data.get("qq") != "all"
    ]
    
    # Check for plain text argument if no mentions
    if not at_users:
        qq_str = args.extract_plain_text().strip()
        if qq_str.isdigit():
            at_users.append(int(qq_str))
            
    if not at_users:
        await del_bot_cmd.finish("请提供有效的 QQ 号或 @ 机器人。")
        return

    removed_bots = []
    for qq in at_users:
        if bot_manager.remove_bot(qq):
            removed_bots.append(str(qq))
            
    if removed_bots:
        await del_bot_cmd.finish(f"机器人 {', '.join(removed_bots)} 已从监控列表中移除。")
    else:
        await del_bot_cmd.finish("指定的机器人不在列表中。")

@list_bots_cmd.handle()
async def handle_list_bots(event: GroupMessageEvent):
    if not is_group_enabled(event.group_id):
        return

    bots = bot_manager.get_bots()
    if bots:
        msg = "当前监控的机器人:\n" + "\n".join(str(qq) for qq in bots)
        await list_bots_cmd.finish(msg)
    else:
        await list_bots_cmd.finish("当前没有监控任何机器人。")


# --- Loop Detection Logic ---

# Store interaction history: { group_id: [ (sender_id, target_id, timestamp) ] }
interaction_history: Dict[int, List[Tuple[int, int, float]]] = defaultdict(list)

# Configuration
HISTORY_WINDOW = 240  # seconds to keep history
DETECTION_WINDOW = 30 # seconds to check for loops
INTERACTION_THRESHOLD = 2 # interactions in window to trigger ban
BAN_DURATION = 600 # seconds (10 minutes)

monitor_handler = on_message(priority=5, block=False)

@monitor_handler.handle()
async def handle_monitor(bot: Bot, event: GroupMessageEvent):
    sender_id = event.user_id
    group_id = event.group_id

    # 0. Check if group is enabled
    if not is_group_enabled(group_id):
        return

    # 1. Check if sender is a monitored bot
    if not bot_manager.is_bot(sender_id):
        return

    # 2. Check if message mentions another monitored bot
    mentioned_bots = []
    for seg in event.message:
        if seg.type == "at":
            target_qq = seg.data.get("qq")
            if target_qq and target_qq != "all" and str(target_qq).isdigit():
                target_qq_int = int(target_qq)
                if bot_manager.is_bot(target_qq_int) and target_qq_int != sender_id:
                    mentioned_bots.append(target_qq_int)

    if not mentioned_bots:
        return

    current_time = time.time()
    
    # Add interactions to history
    for target_id in mentioned_bots:
        interaction_history[group_id].append((sender_id, target_id, current_time))
        logger.info(f"Bot Interaction: {sender_id} -> {target_id} in Group {group_id}")

    # Clean up old history
    interaction_history[group_id] = [
        (s, t, ts) for s, t, ts in interaction_history[group_id]
        if current_time - ts <= HISTORY_WINDOW
    ]

    # Check for loop/spam
    # Count how many times THIS sender has interacted with ANY monitored bot in the detection window
    recent_interactions = [
        (s, t, ts) for s, t, ts in interaction_history[group_id]
        if s == sender_id and current_time - ts <= DETECTION_WINDOW
    ]

    if len(recent_interactions) >= INTERACTION_THRESHOLD:
        logger.warning(f"Loop detected for Bot {sender_id} in Group {group_id}. Interactions: {len(recent_interactions)}")
        
        # Mute the sender
        try:
            await bot.set_group_ban(
                group_id=group_id,
                user_id=sender_id,
                duration=BAN_DURATION
            )
            await monitor_handler.send(f"检测到机器人互怼（{len(recent_interactions)}次交互/30秒），已禁言 {sender_id} {BAN_DURATION//60}分钟。")
            
            # Clear history for this sender to avoid repeated bans immediately after unmute (though ban prevents messages)
            # Actually, clearing history for the group might be safer to reset state
            # interaction_history[group_id].clear() 
            # Or just remove this sender's records? No, keep it simple.
            
        except Exception as e:
            logger.error(f"Failed to ban bot {sender_id}: {e}")
            await monitor_handler.send(f"尝试禁言 {sender_id} 失败，请检查权限。")
