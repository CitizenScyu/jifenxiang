from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler

def is_admin(update: Update, context: CallbackContext) -> bool:
    if not update.effective_chat.type in ['group', 'supergroup']:
        return False
    
    user = context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id
    )
    
    return user.status in ['creator', 'administrator']

class AdminHandlers:
    def __init__(self, db):
        self.db = db

    def add_points(self, update: Update, context: CallbackContext):
        if not is_admin(update, context):
            update.message.reply_text("此命令仅管理员可用")
            return

        try:
            user_id = int(context.args[0])
            points = float(context.args[1])
            
            self.db.update_points(user_id, points)
            update.message.reply_text(f"已为用户 {user_id} 添加 {points} 积分")
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
            update.message.reply_text(f"已从用户 {user_id} 扣除 {points} 积分")
        except (IndexError, ValueError):
            update.message.reply_text("使用方法: /deductpoints <用户ID> <积分>")

    def set_group_settings(self, update: Update, context: CallbackContext):
        if not is_admin(update, context):
            update.message.reply_text("此命令仅管理员可用")
            return

        try:
            setting_type = context.args[0]
            value = float(context.args[1])
            
            group_id = update.effective_chat.id
            settings = self.db.get_group_settings(group_id) or {}
            
            if setting_type in ['min_words', 'points_per_word', 'points_per_media', 'daily_points', 'invite_points']:
                settings[setting_type] = value
                self.db.set_group_settings(group_id, settings)
                update.message.reply_text(f"已更新群组设置: {setting_type} = {value}")
            else:
                update.message.reply_text("无效的设置类型")
        except (IndexError, ValueError):
            update.message.reply_text(
                "使用方法: /set_setting <设置类型> <值>\n"
                "可用设置类型: min_words, points_per_word, points_per_media, daily_points, invite_points"
            )