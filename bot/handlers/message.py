from telegram import Update
from telegram.ext import CallbackContext
import logging
from config import ALLOWED_GROUPS

logger = logging.getLogger(__name__)

class MessageHandlers:
    def __init__(self, db):
        self.db = db

    def handle_message(self, update: Update, context: CallbackContext):
        if not update.effective_chat or not update.effective_user:
            return
            
        if update.effective_chat.type not in ['group', 'supergroup']:
            return
            
        if not self.db.is_group_allowed(update.effective_chat.id):
            return
            
        user_id = update.effective_user.id
        group_id = update.effective_chat.id
        username = update.effective_user.username
        
        # 确保用户存在
        self.db.add_user(user_id, username)
        
        # 获取群组设置
        settings = self.db.get_group_settings(group_id)
        if not settings:
            return
            
        # 初始化积分
        points = 0
        
        # 处理文字消息
        if update.message.text:
            # 检查是否是抽奖口令
            active_lotteries = self.db.get_active_lotteries(group_id)
            for lottery in active_lotteries:
                if lottery[4] and update.message.text.strip() == lottery[4]:
                    # 是抽奖口令，加入抽奖
                    if self.db.join_lottery(lottery[0], user_id, username):
                        update.message.reply_text("✅ 成功参与抽奖！")
                        logger.info(f"User {user_id} joined lottery #{lottery[0]} by keyword")
                    else:
                        update.message.reply_text("您已经参与过此抽奖")
                    return
                    
            # 计算消息积分
            words = len(update.message.text)
            if words >= settings[1]:  # min_words
                points = words * settings[2]  # points_per_word
                
        # 处理媒体消息
        elif any([
            update.message.photo,
            update.message.video,
            update.message.document,
            update.message.sticker
        ]):
            points = settings[3]  # points_per_media
            
        if points > 0:
            self.db.update_points(user_id, points)
            self.db.update_user_message_time(user_id)
            logger.info(f"User {user_id} earned {points} points in group {group_id}")