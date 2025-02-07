from webdav3.client import Client
import json
import os
from datetime import datetime

class WebDAVBackup:
    def __init__(self, config, database):
        self.client = Client(config)
        self.database = database
        
    def backup(self):
        try:
            # 导出数据
            data = self.database.export_data()
            
            # 创建备份文件名
            filename = f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            
            # 保存到本地临时文件
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 上传到WebDAV
            self.client.upload_sync(remote_path=f'/backups/{filename}', local_path=filename)
            
            # 删除本地临时文件
            os.remove(filename)
            
            return True
        except Exception as e:
            print(f"Backup failed: {str(e)}")
            return False
            
    def restore(self):
        try:
            # 获取最新的备份文件
            files = self.client.list('backups/')
            backup_files = [f for f in files if f.endswith('.json')]
            
            if not backup_files:
                return False
                
            latest_backup = max(backup_files)
            
            # 下载最新的备份文件
            self.client.download_sync(
                remote_path=f'/backups/{latest_backup}',
                local_path='restore.json'
            )
            
            # 读取并恢复数据
            with open('restore.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.database.import_data(data)
            
            # 删除临时文件
            os.remove('restore.json')
            
            return True
        except Exception as e:
            print(f"Restore failed: {str(e)}")
            return False