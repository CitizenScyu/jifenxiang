from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from .handlers.admin import AdminHandlers
from .handlers.points import PointsHandlers
from .handlers.lottery import LotteryHandlers
from .handlers.message import MessageHandlers
from .database import Database
from .backup import WebDAVBackup
import threading
import time
import logging

logger = logging.getLogger(__name__)

class PointsBot:
    def __init__(self, token, webdav_config, db_file):
        self.updater = Updater(token=token, use_context=True)
        self.dp = self.updater.dispatcher
        
        # 初始化数据库
        self.db = Database(db_file)
        
        # 初始化备份
        self.backup = WebDAVBackup(webdav_config, self.db)
        
        # 初始化处理器
        self.admin_handlers = AdminHandlers(self.db)
        self.points_handlers = PointsHandlers(self.db)
        self.lottery_handlers = LotteryHandlers(self.db)
        self.message_handlers = MessageHandlers(self.db)
        
        self.setup_handlers()
        self.start_backup_thread()
        
        logger.info("Bot initialized successfully")

    def setup_handlers(self):
        # 管理员命令
        self.dp.add_handler(CommandHandler("addgroup", self.admin_handlers.add_allowed_group))
        self.dp.add_handler(CommandHandler("removegroup", self.admin_handlers.remove_allowed_group))
        self.dp.add_handler(CommandHandler("addpoints", self.admin_handlers.add_points))
        self.dp.add_handler(CommandHandler("deductpoints", self.admin_handlers.deduct_points))
        self.dp.add_handler(CommandHandler("setsetting", self.admin_handlers.set_group_settings))
        self.dp.add_handler(CommandHandler("settings", self.admin_handlers.get_group_settings))
        
        # 积分相关命令
        self.dp.add_handler(CommandHandler("points", self.points_handlers.check_points))
        self.dp.add_handler(CommandHandler("daily", self.points_handlers.daily_checkin))
        self.dp.add_handler(CommandHandler("invite", self.points_handlers.generate_invite))
        
        # 抽奖命令
        self.dp.add_handler(CommandHandler("setlottery", self.lottery_handlers.start_lottery_setup))
        self.dp.add_handler(CommandHandler("joinlottery", self.lottery_handlers.join_lottery))
        self.dp.add_handler(CallbackQueryHandler(self.lottery_handlers.handle_callback_query))
        
        # Start命令处理
        start_handler = CommandHandler("start", self.handle_start)
        self.dp.add_handler(start_handler)
        
        # 消息处理
        self.dp.add_handler(MessageHandler(
            Filters.text & ~Filters.command & ~Filters.private,
            self.message_handlers.handle_message
        ))
        
        # 媒体消息处理
        self.dp.add_handler(MessageHandler(
            (Filters.photo | Filters.video | Filters.document | Filters.sticker) & ~Filters.private,
            self.message_handlers.handle_message
        ))
        
        # 私聊消息处理
        self.dp.add_handler(MessageHandler(
            Filters.private & Filters.text & ~Filters.command,
            self.handle_private_message
        ))
        
        logger.info("Handlers setup completed")

    def handle_start(self, update: Update, context: CallbackContext):
        """处理 /start 命令"""
        # 处理抽奖设置的deep link
        if context.args and context.args[0] == 'lottery':
            return self.lottery_handlers.handle_start_command(update, context)
            
        # 处理邀请链接
        if context.args:
            return self.points_handlers.handle_start_command(update, context)
            
        # 普通的start命令
        update.message.reply_text(
            "👋 欢迎使用积分抽奖机器人！\n\n"
            "🔸 群组命令：\n"
            "/points - 查看积分\n"
            "/daily - 每日签到\n"
            "/invite - 生成邀请链接\n"
            "/joinlottery - 参与抽奖\n\n"
            "🔸 管理员命令：\n"
            "/setlottery - 创建抽奖\n"
            "/settings - 查看群组设置\n"
            "/setsetting - 修改群组设置\n"
            "/addpoints - 添加积分\n"
            "/deductpoints - 扣除积分"
        )

    def handle_private_message(self, update: Update, context: CallbackContext):
        """处理私聊消息"""
        # 处理抽奖设置
        if self.lottery_handlers.handle_lottery_setup(update, context):
            return

    def start_backup_thread(self):
        """启动备份线程"""
        def backup_task():
            while True:
                try:
                    self.backup.backup()
                    logger.info("Backup completed successfully")
                except Exception as e:
                    logger.error(f"Backup failed: {str(e)}")
                time.sleep(3600)  # 每小时备份一次
                
        thread = threading.Thread(target=backup_task)
        thread.daemon = True
        thread.start()
        logger.info("Backup thread started")

    def run(self):
        """运行机器人"""
        # 恢复数据
        try:
            self.backup.restore()
            logger.info("Data restored successfully")
        except Exception as e:
            logger.error(f"Data restore failed: {str(e)}")
        
        # 启动机器人
        self.updater.start_polling()
        logger.info("Bot started polling")
        self.updater.idle()