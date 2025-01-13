import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    DATABASE_URL = os.getenv('DATABASE_URL')
    ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS').split(',')]
    
    # 群组白名单，支持多种格式
    ALLOWED_GROUPS = os.getenv('ALLOWED_GROUPS', '').split(',')
    
    # WebDAV配置
    WEBDAV_HOST = os.getenv('WEBDAV_HOST')
    WEBDAV_USERNAME = os.getenv('WEBDAV_USERNAME')
    WEBDAV_PASSWORD = os.getenv('WEBDAV_PASSWORD')
    
    # 积分设置
    MIN_TEXT_LENGTH = 5  # 最少字数限制
    POINTS_PER_MESSAGE = 1  # 每条消息积分
    POINTS_PER_IMAGE = 1  # 每张图片积分
    POINTS_PER_STICKER = 1  # 每个贴纸积分
    DAILY_CHECKIN_POINTS = 5  # 每日签到积分
    INVITATION_POINTS = 100  # 邀请新用户积分
