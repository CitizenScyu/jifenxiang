import logging
import sys
import os
import pytz
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, JobQueue
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config.config import Config
from modules.points import PointSystem
from modules.invitation import InvitationSystem
from modules.lottery import LotterySystem
from database.db import init_db, get_session, User
from backup import DatabaseBackup

# 确保日志目录存在
os.makedirs('logs', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

# 文件处理器
file_handler = logging.FileHandler('logs/bot.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# 控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# 获取根logger
logger = logging.getLogger()
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 获取应用logger
logger = logging.getLogger(__name__)

class Bot:
    def __init__(self):
        self.db_session = get_session()
        self.point_system = PointSystem(self.db_session)
        self.invitation_system = InvitationSystem(self.db_session)
        self.lottery_system = LotterySystem(self.db_session)
        self.backup_system = DatabaseBackup()

    def check_group_allowed(self, chat_id, username=None):
        chat_id_str = str(chat_id)
        
        for allowed in Config.ALLOWED_GROUPS:
            allowed = allowed.strip()
            if not allowed:
                continue
                
            if allowed.lstrip('-').isdigit() and chat_id_str == allowed:
                return True
                
            if username and allowed.startswith('@') and username == allowed[1:]:
                return True
        
        return False

    def ensure_user_exists(self, user):
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

    async def checkin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理签到"""
        try:
            if update.message.chat.type in ['group', 'supergroup']:
                chat_id = update.message.chat.id
                chat_username = update.message.chat.username
                if not self.check_group_allowed(chat_id, chat_username):
                    await update.message.reply_text("⚠️ 此群组未经授权，机器人无法使用。")
                    return
            
            user = update.effective_user
            result = await self.point_system.process_checkin(user.id)
            await update.message.reply_text(result)
        except Exception as e:
            logger.error(f"Error in checkin: {str(e)}", exc_info=True)
            await update.message.reply_text("签到时出现错误，请稍后重试。")

    async def show_leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示积分排行榜"""
        try:
            if update.message.chat.type in ['group', 'supergroup']:
                chat_id = update.message.chat.id
                chat_username = update.message.chat.username
                if not self.check_group_allowed(chat_id, chat_username):
                    await update.message.reply_text("⚠️ 此群组未经授权，机器人无法使用。")
                    return
            
            leaderboard = await self.point_system.get_leaderboard()
            text = "🏆 积分排行榜\n\n"
            for i, (username, points) in enumerate(leaderboard, 1):
                text += f"{i}. {username}: {points} 积分\n"
            await update.message.reply_text(text)
        except Exception as e:
            logger.error(f"Error in show_leaderboard: {str(e)}", exc_info=True)
            await update.message.reply_text("获取排行榜时出现错误，请稍后重试。")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理按钮回调"""
        try:
            query = update.callback_query
            await query.answer()
            
            data = query.data
            if data.startswith('join_lottery_'):
                lottery_id = int(data.split('_')[2])
                result = await self.lottery_system.join_lottery(lottery_id, query.from_user.id)
                await query.message.reply_text(result)
            
        except Exception as e:
            logger.error(f"Error in button_callback: {str(e)}", exc_info=True)
            if update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text("处理操作时出现错误，请稍后重试。")

    async def show_invite_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Received invite command from user {update.effective_user.id}")
        try:
            if update.message.chat.type in ['group', 'supergroup']:
                chat_id = update.message.chat.id
                chat_username = update.message.chat.username
                logger.info(f"Processing invite command in chat {chat_id} ({chat_username})")
                
                if not self.check_group_allowed(chat_id, chat_username):
                    logger.warning(f"Unauthorized chat: {chat_id}")
                    await update.message.reply_text("⚠️ 此群组未经授权，机器人无法使用。")
                    return
            
            user = update.effective_user
            self.ensure_user_exists(user)
            
            invite_code = await self.invitation_system.generate_invite_link(user.id)
            invite_count = await self.invitation_system.get_invitation_count(user.id)
            
            bot_username = context.bot.username
            invite_link = f"https://t.me/{bot_username}?start={invite_code}"
            
            await update.message.reply_text(
                f"👤 用户：{user.username or user.first_name}\n\n"
                f"🔗 邀请链接：\n{invite_link}\n\n"
                f"📊 邀请统计：\n"
                f"✨ 成功邀请：{invite_count} 人\n"
                f"💰 获得奖励：{invite_count * Config.INVITATION_POINTS} 积分\n\n"
                f"💡 说明：\n"
                f"• 每成功邀请一人奖励 {Config.INVITATION_POINTS} 积分\n"
                f"• 每个新用户只能被邀请一次\n"
                f"• 邀请成功后立即发放奖励"
            )
            logger.info(f"Successfully sent invite info to user {user.id}")
        except Exception as e:
            logger.error(f"Error in show_invite_link: {str(e)}", exc_info=True)
            await update.message.reply_text("生成邀请链接时出现错误，请稍后重试。")

    async def show_lotteries(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示当前进行中的抽奖"""
        try:
            if update.message.chat.type in ['group', 'supergroup']:
                chat_id = update.message.chat.id
                chat_username = update.message.chat.username
                if not self.check_group_allowed(chat_id, chat_username):
                    await update.message.reply_text("⚠️ 此群组未经授权，机器人无法使用。")
                    return
            
            lotteries = await self.lottery_system.list_active_lotteries()
            if not lotteries:
                await update.message.reply_text("🎲 当前没有进行中的抽奖活动")
                return
                
            text = "🎲 进行中的抽奖活动：\n\n"
            for lottery in lotteries:
                info = await self.lottery_system.get_lottery_info(lottery.id)
                text += (
                    f"🏷️ {info['title']}\n"
                    f"📝 {info['description']}\n"
                    f"💰 需要积分：{info['points_required']}\n"
                    f"👥 最少参与人数：{info['min_participants']}\n"
                    f"🎯 当前参与人数：{info['current_participants']}\n"
                    f"🏆 获奖名额：{info['winners_count']}\n"
                )
                if info['keyword']:
                    text += f"🔑 参与口令：{info['keyword']}\n"
                if info['end_time']:
                    text += f"⏰ 结束时间：{info['end_time'].strftime('%Y-%m-%d %H:%M')}\n"
                text += "\n"
                
            await update.message.reply_text(text)
        except Exception as e:
            logger.error(f"Error in show_lotteries: {str(e)}", exc_info=True)
            await update.message.reply_text("获取抽奖列表时出现错误，请稍后重试。")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        logger.info(f"Received start command from user {update.effective_user.id}")
        try:
            if update.message.chat.type in ['group', 'supergroup']:
                chat_id = update.message.chat.id
                chat_username = update.message.chat.username
                if not self.check_group_allowed(chat_id, chat_username):
                    await update.message.reply_text("⚠️ 此群组未经授权，机器人无法使用。")
                    return
            
            user = update.effective_user
            self.ensure_user_exists(user)
            
            args = context.args
            if args and len(args[0]) == 8:  # 邀请码长度为8
                invite_code = args[0]
                success = await self.invitation_system.process_invitation(invite_code, user.id)
                if success:
                    inviter_id = await self.invitation_system.get_inviter_by_code(invite_code)
                    await self.point_system.add_points(inviter_id, Config.INVITATION_POINTS)
                    await update.message.reply_text(
                        f"🎉 欢迎加入！您已通过邀请链接注册成功\n"
                        f"💫 邀请者获得 {Config.INVITATION_POINTS} 积分奖励"
                    )
                    return
            
            # 默认欢迎信息
            await update.message.reply_text(
                f"👋 欢迎使用积分抽奖机器人！\n\n"
                f"🎮 主要功能：\n"
                f"• /points - 查看积分\n"
                f"• /invite - 生成邀请链接\n"
                f"• /lotteries - 查看抽奖活动\n"
                f"• /mylotteries - 查看我的抽奖\n\n"
                f"💡 温馨提示：\n"
                f"• 通过邀请好友可以获得积分奖励\n"
                f"• 积分可以参与抽奖活动"
            )
            logger.info(f"Successfully processed start command for user {user.id}")
        except Exception as e:
            logger.error(f"Error in start command: {str(e)}", exc_info=True)
            await update.message.reply_text("处理命令时出现错误，请稍后重试。")

    async def show_points(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示用户积分"""
        logger.info(f"Received points command from user {update.effective_user.id}")
        try:
            if update.message.chat.type in ['group', 'supergroup']:
                chat_id = update.message.chat.id
                chat_username = update.message.chat.username
                if not self.check_group_allowed(chat_id, chat_username):
                    await update.message.reply_text("⚠️ 此群组未经授权，机器人无法使用。")
                    return
            
            user = update.effective_user
            db_user = self.ensure_user_exists(user)
            
            points = await self.point_system.get_points(user.id)
            await update.message.reply_text(
                f"👤 用户：{user.username or user.first_name}\n"
                f"💰 当前积分：{points}\n\n"
                f"💡 获取更多积分：\n"
                f"• 邀请好友加入可获得 {Config.INVITATION_POINTS} 积分\n"
                f"• 使用 /invite 生成邀请链接"
            )
            logger.info(f"Successfully sent points info to user {user.id}")
        except Exception as e:
            logger.error(f"Error in show_points: {str(e)}", exc_info=True)
            await update.message.reply_text("查询积分时出现错误，请稍后重试。")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理普通消息"""
        try:
            if update.message.chat.type in ['group', 'supergroup']:
                chat_id = update.message.chat.id
                chat_username = update.message.chat.username
                if not self.check_group_allowed(chat_id, chat_username):
                    return
            
            user = update.effective_user
            self.ensure_user_exists(user)
            
            if update.message.text:
                text = update.message.text.strip()
                
                if text == "签到":
                    await self.checkin(update, context)
                elif text == "积分":
                    await self.show_points(update, context)
                elif text == "积分排行榜":
                    await self.show_leaderboard(update, context)
                elif text == "抽奖":
                    await self.show_lotteries(update, context)
                else:
                    # 检查是否是抽奖关键词
                    result, message = await self.lottery_system.check_keyword_lottery(update.message)
                    if result:
                        await update.message.reply_text(message)
                    elif await self.point_system.check_message_validity(update.message):
                        await self.point_system.add_points(update.effective_user.id, Config.POINTS_PER_MESSAGE)
            elif update.message.sticker:
                await self.point_system.add_points(update.effective_user.id, Config.POINTS_PER_STICKER)
        except Exception as e:
            logger.error(f"Error in handle_message: {str(e)}", exc_info=True)
            await update.message.reply_text("处理消息时出现错误，请稍后重试。")

    def run(self):
        try:
            logger.info("Initializing bot...")
            init_db()
            logger.info("Database initialized")
            self.backup_system.run()
            logger.info("Backup system started")
            
            logger.info("Building application...")
            # 创建 application 时不使用默认的 job_queue
            application = (
                Application.builder()
                .token(Config.BOT_TOKEN)
                .job_queue(None)  # 禁用默认的 job_queue
                .build()
            )
            logger.info("Application built successfully")
            
            # 添加处理器
            logger.info("Adding handlers...")
            application.add_handler(CommandHandler("start", self.start))
            application.add_handler(CommandHandler("checkin", self.checkin))
            application.add_handler(CommandHandler("points", self.show_points))
            application.add_handler(CommandHandler("leaderboard", self.show_leaderboard))
            application.add_handler(CommandHandler("invite", self.show_invite_link))
            application.add_handler(CommandHandler("lottery", self.show_lotteries))
            application.add_handler(CallbackQueryHandler(self.button_callback))
            application.add_handler(MessageHandler((filters.Sticker.ALL | filters.TEXT) & ~filters.COMMAND, self.handle_message))
            logger.info("Handlers added successfully")

            logger.info("Bot is starting...")
            application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}", exc_info=True)
            import traceback
            logger.error(traceback.format_exc())
            import time
            time.sleep(10)

if __name__ == '__main__':
    bot = Bot()
    bot.run()
