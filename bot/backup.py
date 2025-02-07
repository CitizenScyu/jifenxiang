from webdav3.client import Client
import json
import os
from datetime import datetime
import logging

class WebDAVBackup:
    def __init__(self, config, database):
        self.client = Client(config)
        self.database = database
        self.logger = logging.getLogger(__name__)
        
        # 确保备份目录存在
        try:
            if not self.client.check('backups'):
                self.client.mkdir('backups')
        except Exception as e:
            self.logger.error(f"Failed to create backup directory: {str(e)}")
        
    def backup(self):
        try:
            # 导出数据
            data = self.database.export_data()
            
            # 创建备份文件名
            filename = f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            local_path = f'temp_{filename}'
            
            # 保存到本地临时文件
            with open(local_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 上传到WebDAV
            self.client.upload_sync(remote_path=f'backups/{filename}', local_path=local_path)
            
            # 删除本地临时文件
            os.remove(local_path)
            
            # 清理旧备份（保留最近10个）
            self._cleanup_old_backups()
            
            self.logger.info(f"Backup completed: {filename}")
            return True
        except Exception as e:
            self.logger.error(f"Backup failed: {str(e)}")
            return False
            
    def restore(self):
        try:
            # 获取最新的备份文件
            files = [f for f in self.client.list('backups/') if f.endswith('.json')]
            
            if not files:
                self.logger.warning("No backup files found")
                return False
                
            # 按文件名排序（包含时间戳）
            latest_backup = sorted(files)[-1]
            local_path = 'restore_temp.json'
            
            # 下载最新的备份文件
            self.client.download_sync(
                remote_path=f'backups/{latest_backup}',
                local_path=local_path
            )
            
            # 读取并恢复数据
            with open(local_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.database.import_data(data)
            
            # 删除临时文件
            os.remove(local_path)
            
            self.logger.info(f"Restore completed from: {latest_backup}")
            return True
        except Exception as e:
            self.logger.error(f"Restore failed: {str(e)}")
            return False
            
    def _cleanup_old_backups(self, keep_count=10):
        try:
            files = [f for f in self.client.list('backups/') if f.endswith('.json')]
            if len(files) > keep_count:
                # 按时间排序
                files.sort()
                # 删除旧文件
                for file in files[:-keep_count]:
                    self.client.clean(f'backups/{file}')
                    self.logger.info(f"Deleted old backup: {file}")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")