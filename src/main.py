import logging
import sys
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
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
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Start command received from user {update.effective_user.id}")
        user = update.effective_user
        self.ensure_user_exists(user)
        
        if context.args and len(context.args) > 0:
            invite_code = context.args[0]
            if await self.invitation_system.process_invitation(invite_code, user.id):
                inviter = await self.invitation_system.get_inviter_info(user.id)
                if inviter:
                    await update.message.reply_text(
                        f"✨ 欢迎加入！\n"
                        f"👤 你已被用户 {inviter.username} 成功邀请\n"
                        f"💰 邀请人获得 {Config.INVITATION_POINTS} 积分奖励"
                    )
        
        welcome_text = (
            "🤖 积分机器人使用说明\n\n"
            "💡 功能说明：\n"
            "1. 发送消息获得积分\n"
            "2. 发送贴纸获得积分\n"
            "3. 每日签到奖励\n"
            "4. 邀请新用户奖励\n"
            "5. 查看积分排行榜\n"
            "6. 参与抽奖活动\n\n"
            "📝 快捷命令：\n"
            "「签到」- 每日签到\n"
            "「积分」- 查询积分\n"
            "「积分排行榜」- 查看排名\n"
            "「抽奖」- 查看抽奖\n"
            "/invite - 获取邀请链接\n"
            "/lottery - 查看抽奖活动\n\n"
            "✨ 在授权的群组内直接使用以上功能即可！"
        )
        await update.message.reply_text(welcome_text)

    async def checkin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.chat.type in ['group', 'supergroup']:
            chat_id = update.message.chat.id
            chat_username = update.message.chat.username
            if not self.check_group_allowed(chat_id, chat_username):
                await update.message.reply_text("⚠️ 此群组未经授权，机器人无法使用。")
                return
        else:
            await update.message.reply_text("请在授权的群组内使用机器人功能！")
            return

        user = update.effective_user
        self.ensure_user_exists(user)
        
        result = await self.point_system.daily_checkin(user.id)
        if result:
            points, _ = await self.point_system.get_user_points(user.id)
            await update.message.reply_text(
                f"✅ 签到成功！\n"
                f"💰 获得 {Config.DAILY_CHECKIN_POINTS} 积分\n"
                f"💵 当前总积分：{int(points)}分"
            )
        else:
            await update.message.reply_text("❌ 今天已经签到过了哦！明天再来吧！")

    async def show_points(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.chat.type in ['group', 'supergroup']:
            chat_id = update.message.chat.id
            chat_username = update.message.chat.username
            if not self.check_group_allowed(chat_id, chat_username):
                await update.message.reply_text("⚠️ 此群组未经授权，机器人无法使用。")
                return
        else:
            await update.message.reply_text("请在授权的群组内使用机器人功能！")
            return

        user = update.effective_user
        self.ensure_user_exists(user)
        
        points, username = await self.point_system.get_user_points(user.id)
        if points is not None:
            await update.message.reply_text(
                f"👤 用户: {username}\n"
                f"💰 当前积分: {round(float(points))}分"
            )
        else:
            await update.message.reply_text("未找到你的积分信息")

    async def show_leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page=1):
        if update.message.chat.type in ['group', 'supergroup']:
            chat_id = update.message.chat.id
            chat_username = update.message.chat.username
            if not self.check_group_allowed(chat_id, chat_username):
                await update.message.reply_text("⚠️ 此群组未经授权，机器人无法使用。")
                return
        else:
            await update.message.reply_text("请在授权的群组内使用机器人功能！")
            return

        leaderboard_text, total_pages = await self.point_system.get_points_leaderboard(page)
        
        keyboard = []
        if total_pages > 1:
            buttons = []
            if page > 1:
                buttons.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"leaderboard_{page-1}"))
            if page < total_pages:
                buttons.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"leaderboard_{page+1}"))
            keyboard.append(buttons)
            
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        await update.message.reply_text(leaderboard_text, reply_markup=reply_markup)

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

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("leaderboard_"):
            page = int(query.data.split("_")[1])
            leaderboard_text, total_pages = await self.point_system.get_points_leaderboard(page)
            
            keyboard = []
            if total_pages > 1:
                buttons = []
                if page > 1:
                    buttons.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"leaderboard_{page-1}"))
                if page < total_pages:
                    buttons.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"leaderboard_{page+1}"))
                keyboard.append(buttons)
                
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            await query.message.edit_text(leaderboard_text, reply_markup=reply_markup)
        elif query.data.startswith('join_lottery_'):
            lottery_id = int(query.data.split('_')[2])
            result = await self.lottery_system.join_lottery(lottery_id, query.from_user.id)
            await query.message.reply_text(result)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
            
        if update.message.chat.type in ['group', 'supergroup']:
            chat_id = update.message.chat.id
            chat_username = update.message.chat.username
            
            if not self.check_group_allowed(chat_id, chat_username):
                await update.message.reply_text("⚠️ 此群组未经授权，机器人无法使用。")
                return
            
            user = update.effective_user
            self.ensure_user_exists(user)
        else:
            await update.message.reply_text("请在授权的群组内使用机器人功能！")
            return
        
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

    def run(self):
        while True:
            try:
                logger.info("Initializing bot...")
                init_db()
                self.backup_system.run()
                
                application = Application.builder().token(Config.BOT_TOKEN).build()
                
                # 添加处理器
                application.add_handler(CommandHandler("start", self.start))
                application.add_handler(CommandHandler("checkin", self.checkin))
                application.add_handler(CommandHandler("points", self.show_points))
                application.add_handler(CommandHandler("leaderboard", self.show_leaderboard))
                application.add_handler(CommandHandler("invite", self.show_invite_link))
                application.add_handler(CommandHandler("lottery", self.show_lotteries))
                application.add_handler(CallbackQueryHandler(self.button_callback))
                application.add_handler(MessageHandler((filters.Sticker.ALL | filters.TEXT) & ~filters.COMMAND, self.handle_message))

                logger.info("Bot is starting...")
                application.run_polling(timeout=30, drop_pending_updates=True)
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}", exc_info=True)
                import time
                time.sleep(10)  # 等待10秒后重试

if __name__ == '__main__':
    bot = Bot()
    bot.run()
