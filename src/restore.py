import os
from webdav3.client import Client
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/restore.log'
)

class DatabaseRestore:
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

    def restore_latest_backup(self):
        """恢复最新的备份"""
        try:
            # 获取所有备份文件
            files = self.client.list(self.remote_path)
            db_files = [f for f in files if f.endswith('.db')]
            
            if not db_files:
                logging.error("No backup files found!")
                return False
                
            # 获取最新的备份文件
            latest_backup = sorted(db_files)[-1]
            
            # 如果当前数据库存在，创建备份
            if os.path.exists(self.db_path):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"bot_local_backup_{timestamp}.db"
                os.rename(self.db_path, backup_name)
                logging.info(f"Created local backup: {backup_name}")
            
            # 下载最新备份
            self.client.download(
                remote_path=self.remote_path + latest_backup,
                local_path=self.db_path
            )
            
            logging.info(f"Successfully restored from backup: {latest_backup}")
            return True
            
        except Exception as e:
            logging.error(f"Restore failed: {str(e)}")
            return False

    def restore_specific_backup(self, backup_name):
        """恢复指定的备份文件"""
        try:
            remote_file = self.remote_path + backup_name
            
            if not self.client.check(remote_file):
                logging.error(f"Backup file not found: {backup_name}")
                return False
            
            # 备份当前数据库
            if os.path.exists(self.db_path):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"bot_local_backup_{timestamp}.db"
                os.rename(self.db_path, backup_name)
                logging.info(f"Created local backup: {backup_name}")
            
            # 下载指定备份
            self.client.download(
                remote_path=remote_file,
                local_path=self.db_path
            )
            
            logging.info(f"Successfully restored from specific backup: {backup_name}")
            return True
            
        except Exception as e:
            logging.error(f"Restore failed: {str(e)}")
            return False

    def list_available_backups(self):
        """列出所有可用的备份"""
        try:
            files = self.client.list(self.remote_path)
            db_files = [f for f in files if f.endswith('.db')]
            return sorted(db_files)
        except Exception as e:
            logging.error(f"Failed to list backups: {str(e)}")
            return []

def main():
    """主函数，用于命令行恢复"""
    restore = DatabaseRestore()
    
    print("Available backups:")
    backups = restore.list_available_backups()
    
    if not backups:
        print("No backups found!")
        return
        
    print("\nAvailable options:")
    print("1. Restore latest backup")
    print("2. Choose specific backup")
    
    choice = input("\nEnter your choice (1 or 2): ")
    
    if choice == "1":
        if restore.restore_latest_backup():
            print("Successfully restored latest backup!")
        else:
            print("Restore failed!")
    elif choice == "2":
        print("\nAvailable backups:")
        for i, backup in enumerate(backups, 1):
            print(f"{i}. {backup}")
            
        backup_choice = int(input("\nEnter backup number: ")) - 1
        if 0 <= backup_choice < len(backups):
            if restore.restore_specific_backup(backups[backup_choice]):
                print("Successfully restored backup!")
            else:
                print("Restore failed!")
        else:
            print("Invalid choice!")
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()
