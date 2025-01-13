import logging
import asyncio
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
from database.db import get_session, Base, engine

# 配置日志
logging.basicConfig(
    filename='logs/backup.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class DatabaseBackup:
    def __init__(self):
        self.db_session = get_session()
        self.scheduler = AsyncIOScheduler()  # 移除时区配置
        
    def backup_database(self):
        """备份数据库"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = 'backups'
            os.makedirs(backup_dir, exist_ok=True)
            
            # 导出数据库结构
            with open(f'{backup_dir}/schema_{timestamp}.sql', 'w') as f:
                for table in Base.metadata.sorted_tables:
                    f.write(str(table.compile(engine)) + ';\n')
            
            logger.info(f"Database backup completed: schema_{timestamp}.sql")
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            
    def run(self):
        """启动定时备份任务"""
        try:
            # 每天凌晨3点进行备份
            self.scheduler.add_job(
                self.backup_database,
                'cron',
                hour=3,
                minute=0
            )
            
            self.scheduler.start()
            logger.info("Backup scheduler started")
        except Exception as e:
            logger.error(f"Failed to start backup scheduler: {str(e)}")
