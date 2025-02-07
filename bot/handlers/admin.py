from telegram import Update, ParseMode
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from config import SUPER_ADMIN, ALLOWED_GROUPS
import logging

logger = logging.getLogger(__name__)

def is_admin(update: Update, context: CallbackContext) -> bool:
    if not update.effective_chat.type in ['group', 'supergroup']:
        return False
    
    user = context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id
    )
    
    return user.status in ['creator', 'administrator']

def is_super_admin(user_id: int) -> bool:
    return user_id == SUPER_ADMIN

class AdminHandlers:
    def __init__(self, db):
        self.db = db

    def add_allowed_group(self, update: Update, context: CallbackContext):
        if not is_super_admin(update.effective_user.id):
            update.message.reply_text("只有超级管理员可以添加群组白名单")
            return

        try:
            group_id = int(context.args[0])
            if group_id not in ALLOWED_GROUPS:
                ALLOWED_GROUPS.append(group_id)
                self.db.set_group_settings(group_id, {'is_allowed': True})
                update.message.reply_text(f"已将群组 {group_id} 添加到白名单")
            else:
                update.message.reply_text("该群组已在白名单中")
        except (IndexError, ValueError):
            update.message.reply_text("使用方法: /addgroup <群组ID>")

    def remove_allowed_group(self, update: Update, context: CallbackContext):
        if not is_super_admin(update.effective_user.id):
            update.message.reply_text("只有超级管理员可以移除群组白名单")
            return

        try:
            group_id = int(context.args[0])
            if group_id in ALLOWED_GROUPS:
                ALLOWED_GROUPS.remove(group_id)
                self.db.set_group_settings(group_id, {'is_allowed': False})
                update.message.reply_text(f"已将群组 {group_id} 从白名单移除")
            else:
                update.message.reply_text("该群组不在白名单中")
        except (IndexError, ValueError):
            update.message.reply_text("使用方法: /removegroup <群组ID>")

    def add_points(self, update: Update, context: CallbackContext):
        if not is_admin(update, context):
            update.message.reply_text("此命令仅管理员可用")
            return

        try:
            user_id = int(context.args[0])
            points = float(context.args[1])
            
            self.db.update_points(user_id, points)
            update.message.reply_text(
                f"已为用户 {user_id} 添加 {points} 积分",
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Admin {update.effective_user.id} added {points} points to user {user_id}")
        except (IndexError, ValueError):
            update.message.reply_text("使用方法: /addpoints <用户ID> <积分>")

    def deduct_points(self, update: Update, context: CallbackContext):
        if not is_admin(update, context):
            update.message.reply_text("此命令仅管理员可用")
            return

        try:
            user_id = int(context.args[0])
            points = float(context.args[1])
            
            self.db.update_points(user_id, -points)
            update.message.reply_text(
                f"已从用户 {user_id} 扣除 {points} 积分",
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Admin {update.effective_user.id} deducted {points} points from user {user_id}")
        except (IndexError, ValueError):
            update.message.reply_text("使用方法: /deductpoints <用户ID> <积分>")

    def set_group_settings(self, update: Update, context: CallbackContext):
        if not is_admin(update, context):
            update.message.reply_text("此命令仅管理员可用")
            return

        if not self.db.is_group_allowed(update.effective_chat.id):
            update.message.reply_text("此群组不在白名单中")
            return

        try:
            setting_type = context.args[0].lower()
            value = float(context.args[1])
            
            valid_settings = {
                'min_words': '最小字数',
                'points_per_word': '每字积分',
                'points_per_media': '媒体积分',
                'daily_points': '签到积分',
                'invite_points': '邀请积分'
            }
            
            if setting_type not in valid_settings:
                update.message.reply_text(
                    "无效的设置类型\n可用设置：\n" + 
                    "\n".join([f"- {k}: {v}" for k, v in valid_settings.items()])
                )
                return
                
            group_id = update.effective_chat.id
            current_settings = self.db.get_group_settings(group_id) or {}
            current_settings[setting_type] = value
            
            self.db.set_group_settings(group_id, current_settings)
            update.message.reply_text(
                f"已更新群组设置：{valid_settings[setting_type]} = {value}",
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Admin {update.effective_user.id} updated {setting_type} to {value} in group {group_id}")
        except (IndexError, ValueError):
            update.message.reply_text(
                "使用方法: /setsetting <设置类型> <值>\n"
                "例如: /setsetting min_words 5"
            )

    def get_group_settings(self, update: Update, context: CallbackContext):
        if not is_admin(update, context):
            update.message.reply_text("此命令仅管理员可用")
            return

        group_id = update.effective_chat.id
        settings = self.db.get_group_settings(group_id)
        
        if not settings:
            update.message.reply_text("此群组暂无设置")
            return
            
        settings_text = "当前群组设置：\n"
        settings_text += f"最小字数：{settings[1]}\n"
        settings_text += f"每字积分：{settings[2]}\n"
        settings_text += f"媒体积分：{settings[3]}\n"
        settings_text += f"签到积分：{settings[4]}\n"
        settings_text += f"邀请积分：{settings[5]}\n"
        settings_text += f"白名单状态：{'已启用' if settings[6] else '未启用'}"
        
        update.message.reply_text(settings_text, parse_mode=ParseMode.HTML)