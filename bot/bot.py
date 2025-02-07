from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from .handlers.admin import AdminHandlers
from .handlers.points import PointsHandlers
from .handlers.lottery import LotteryHandlers
from .handlers.message import MessageHandlers
from .database import Database
from .backup import WebDAVBackup
import threading
import time

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

    def setup_handlers(self):
        # 管理员命令
        self.dp.add_handler(CommandHandler("addpoints", self.admin_handlers.add_points))
        self.dp.add_handler(CommandHandler("deductpoints", self.admin_handlers.deduct_points))
        self.dp.add_handler(CommandHandler("setsetting", self.admin_handlers.set_group_settings))
        
        # 积分相关命令
        self.dp.add_handler(CommandHandler("points", self.points_handlers.check_points))
        self.dp.add_handler(CommandHandler("daily", self.points_handlers.daily_checkin))
        self.dp.add_handler(CommandHandler("invite", self.points_handlers.generate_invite))
        
        # 抽奖命令
        self.dp.add_handler(CommandHandler("createlottery", self.lottery_handlers.create_lottery))
        self.dp.add_handler(CommandHandler("joinlottery", self.lottery_handlers.join_lottery))
        self.dp.add_handler(CommandHandler("forcedraw", self.lottery_handlers.force_draw))
        
        # 消息处理
        self.dp.add_handler(MessageHandler(
            Filters.text | Filters.photo | Filters.video | Filters.document | Filters.sticker,
            self.message_handlers.handle_message
        ))

    def start_backup_thread(self):
        def backup_task():
            while True:
                self.backup.backup()
                time.sleep(3600)  # 每小时备份一次
                
        thread = threading.Thread(target=backup_task)
        thread.daemon = True
        thread.start()

    def run(self):
        # 恢复数据
        self.backup.restore()
        
        # 启动机器人
        self.updater.start_polling()
        self.updater.idle()