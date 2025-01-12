import os
import time
import shutil
from datetime import datetime
from webdav3.client import Client
import logging
import threading
import schedule
from config.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/backup.log'
)

class DatabaseBackup:
    def __init__(self):
        # WebDAV配置
        self.webdav_options = {
            'webdav_hostname': os.getenv('WEBDAV_HOST'),
            'webdav_login': os.getenv('WEBDAV_USERNAME'),
            'webdav_password': os.getenv('WEBDAV_PASSWORD')
        }
        self.client = Client(self.webdav_options)
        self.remote_path = "/tg_bot_backup/"
        self.db_path = "bot.db"
        
    def backup_database(self):
        try:
            # 确保远程目录存在
            if not self.client.check(self.remote_path):
                self.client.mkdir(self.remote_path)

            # 创建临时备份文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"bot_backup_{timestamp}.db"
            
            # 复制数据库文件
            shutil.copy2(self.db_path, backup_filename)
            
            # 上传到WebDAV
            self.client.upload(
                remote_path=self.remote_path + backup_filename,
                local_path=backup_filename
            )
            
            # 删除临时文件
            os.remove(backup_filename)
            
            # 只保留最近24小时的备份
            self.cleanup_old_backups()
            
            logging.info(f"Database backup successful: {backup_filename}")
            
        except Exception as e:
            logging.error(f"Backup failed: {str(e)}")
    
    def cleanup_old_backups(self):
        try:
            # 获取所有备份文件
            files = self.client.list(self.remote_path)
            current_time = time.time()
            
            # 删除24小时前的备份
            for file in files:
                if file.endswith('.db'):
                    file_path = self.remote_path + file
                    file_info = self.client.info(file_path)
                    file_time = file_info['modified']
                    
                    # 如果文件超过24小时
                    if (current_time - file_time) > 86400:
                        self.client.clean(file_path)
                        logging.info(f"Deleted old backup: {file}")
                        
        except Exception as e:
            logging.error(f"Cleanup failed: {str(e)}")

    def start_backup_schedule(self):
        schedule.every(1).minutes.do(self.backup_database)
        
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    def run(self):
        # 在新线程中运行备份调度
        backup_thread = threading.Thread(target=self.start_backup_schedule)
        backup_thread.daemon = True
        backup_thread.start()
        logging.info("Backup system started")
