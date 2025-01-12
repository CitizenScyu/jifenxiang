import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config.config import Config
from modules.points import PointSystem
from modules.invitation import InvitationSystem
from database.db import init_db, get_session, User
from backup import DatabaseBackup

# 设置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='logs/bot.log'
)

class Bot:
    def __init__(self):
        self.db_session = get_session()
        self.point_system = PointSystem(self.db_session)
        self.invitation_system = InvitationSystem(self.db_session)
        self.backup_system = DatabaseBackup()
        
    def check_group_allowed(self, chat_id, username=None):
        """检查群组是否在白名单中"""
        chat_id_str = str(chat_id)
        
        for allowed in Config.ALLOWED_GROUPS:
            allowed = allowed.strip()
            if not allowed:  # 跳过空值
                continue
                
            # 检查数字ID（包括带负号的）
            if allowed.lstrip('-').isdigit() and chat_id_str == allowed:
                return True
                
            # 检查用户名格式（@开头）
            if username and allowed.startswith('@') and username == allowed[1:]:
                return True
        
        return False
        
    def ensure_user_exists(self, user):
        """确保用户存在于数据库中"""
        db_user = self.db_session.query(User).filter_by(tg_id=user.id).first()
        if not db_user:
            new_user = User(
                tg_id=user.id,
                username=user.username or user.first_name,
                points=0
            )
            self.db_session.add(new_user)
            self.db_session.commit()
        return db_user or new_user

    async def show_invite_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示用户的邀请链接和邀请统计"""
        if update.message.chat.type in ['group', 'supergroup']:
            chat_id = update.message.chat.id
            chat_username = update.message.chat.username
            if not self.check_group_allowed(chat_id, chat_username):
                await update.message.reply_text("⚠️ 此群组未经授权，机器人无法使用。")
                return
        
        user = update.effective_user
        self.ensure_user_exists(user)
        
        invite_link = await self.invitation_system.generate_invite_link(user.id)
        invite_count = await self.invitation_system.get_invitation_count(user.id)
        
        await update.message.reply_text(
            f"👤 用户：{user.username or user.first_name}\n\n"
            f"🔗 邀请链接：\n"
            f"https://t.me/{context.bot.username}?start={invite_link}\n\n"
            f"📊 邀请统计：\n"
            f"✨ 成功邀请：{invite_count} 人\n"
            f"💰 获得奖励：{invite_count * Config.INVITATION_POINTS} 积分\n\n"
            f"💡 说明：\n"
            f"• 每成功邀请一人奖励 {Config.INVITATION_POINTS} 积分\n"
            f"• 每个新用户只能被邀请一次\n"
            f"• 邀请成功后立即发放奖励"
        )
