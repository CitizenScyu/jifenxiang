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
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        # 检查用户是否存在，不存在则创建
        db_user = self.db_session.query(User).filter_by(tg_id=user.id).first()
        if not db_user:
            new_user = User(
                tg_id=user.id,
                username=user.username or user.first_name,
                points=0
            )
            self.db_session.add(new_user)
            self.db_session.commit()
            
        welcome_text = (
            f"你好 {user.first_name}！\n"
            "🤖 欢迎使用积分机器人\n\n"
            "💡 功能说明：\n"
            "1. 发送消息获得积分\n"
            "2. 每日签到奖励\n"
            "3. 邀请新用户奖励\n"
            "4. 查看积分排行榜\n\n"
            "📝 快捷命令：\n"
            "「签到」- 每日签到\n"
            "「积分」- 查询积分\n"
            "「积分排行榜」- 查看排名\n\n"
            "✨ 开始使用吧！"
        )
        await update.message.reply_text(welcome_text)

    async def checkin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        result = await self.point_system.daily_checkin(user_id)
        if result:
            points, _ = await self.point_system.get_user_points(user_id)
            await update.message.reply_text(
                f"✅ 签到成功！\n"
                f"💰 获得 {Config.DAILY_CHECKIN_POINTS} 积分\n"
                f"💵 当前总积分：{int(points)}分"
            )
        else:
            await update.message.reply_text("❌ 今天已经签到过了哦！明天再来吧！")

    async def show_points(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        points, username = await self.point_system.get_user_points(user_id)
        if points is not None:
            await update.message.reply_text(
                f"👤 用户: {username}\n"
                f"💰 当前积分: {int(points)}分"
            )
        else:
            await update.message.reply_text("未找到你的积分信息，请先使用 /start 注册")

    async def show_leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page=1):
        leaderboard_text, total_pages = await self.point_system.get_points_leaderboard(page)
        
        # 创建翻页按钮
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

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.text:
            return
            
        text = update.message.text.strip()
        
        if text == "签到":
            await self.checkin(update, context)
        elif text == "积分":
            await self.show_points(update, context)
        elif text == "积分排行榜":
            await self.show_leaderboard(update, context)
        else:
            # 处理普通消息获取积分
            user_id = update.effective_user.id
            if await self.point_system.check_message_validity(update.message):
                await self.point_system.add_points(user_id, Config.POINTS_PER_MESSAGE)

    def run(self):
        # 初始化数据库
        init_db()
        
        # 启动备份系统
        self.backup_system.run()
        
        # 创建应用
        application = Application.builder().token(Config.BOT_TOKEN).build()

        # 添加处理器
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("checkin", self.checkin))
        application.add_handler(CommandHandler("points", self.show_points))
        application.add_handler(CommandHandler("leaderboard", self.show_leaderboard))
        application.add_handler(CallbackQueryHandler(self.button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # 启动机器人
        application.run_polling()

if __name__ == '__main__':
    bot = Bot()
    bot.run()
