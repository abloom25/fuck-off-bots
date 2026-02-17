from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.log import logger
import time
from typing import Dict, List, Tuple
from collections import defaultdict

from .data_manager import bot_manager

# --- Command Handlers ---

add_bot_cmd = on_command("add_bot", permission=SUPERUSER, priority=10, block=True)
del_bot_cmd = on_command("del_bot", permission=SUPERUSER, priority=10, block=True)
list_bots_cmd = on_command("list_bots", permission=SUPERUSER, priority=10, block=True)

@add_bot_cmd.handle()
async def handle_add_bot(event: GroupMessageEvent, args: Message = CommandArg()):
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
        await add_bot_cmd.finish("Please provide a valid QQ number or @ the bot.")
        return

    added_bots = []
    for qq in at_users:
        if bot_manager.add_bot(qq):
            added_bots.append(str(qq))
    
    if added_bots:
        await add_bot_cmd.finish(f"Bot(s) {', '.join(added_bots)} added to monitoring list.")
    else:
        await add_bot_cmd.finish("Specified bot(s) are already in the list.")

@del_bot_cmd.handle()
async def handle_del_bot(event: GroupMessageEvent, args: Message = CommandArg()):
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
        await del_bot_cmd.finish("Please provide a valid QQ number or @ the bot.")
        return

    removed_bots = []
    for qq in at_users:
        if bot_manager.remove_bot(qq):
            removed_bots.append(str(qq))
            
    if removed_bots:
        await del_bot_cmd.finish(f"Bot(s) {', '.join(removed_bots)} removed from monitoring list.")
    else:
        await del_bot_cmd.finish("Specified bot(s) were not in the list.")

@list_bots_cmd.handle()
async def handle_list_bots():
    bots = bot_manager.get_bots()
    if bots:
        msg = "Monitored Bots:\n" + "\n".join(str(qq) for qq in bots)
        await list_bots_cmd.finish(msg)
    else:
        await list_bots_cmd.finish("No bots are currently monitored.")


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
