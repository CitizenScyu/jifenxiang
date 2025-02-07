import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBDAV_CONFIG = {
    'webdav_hostname': os.getenv('WEBDAV_HOST'),
    'webdav_login': os.getenv('WEBDAV_LOGIN'),
    'webdav_password': os.getenv('WEBDAV_PASSWORD')
}

# 积分设置
DEFAULT_POINTS_PER_WORD = 0.1
DEFAULT_POINTS_PER_MEDIA = 1
DEFAULT_DAILY_POINTS = 5
DEFAULT_INVITE_POINTS = 10
MIN_WORDS_FOR_POINTS = 5

# 数据库设置
DATABASE_FILE = 'bot_data.db'

# 备份设置
BACKUP_INTERVAL = 3600  # 每小时备份一次