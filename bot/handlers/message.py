from telegram import Update
from telegram.ext import CallbackContext

class MessageHandlers:
    def __init__(self, db):
        self.db = db

    def handle_message(self, update: Update, context: CallbackContext):
        if not update.effective_chat or not update.effective_user:
            return
            
        if update.effective_chat.type not in ['group', 'supergroup']:
            return
            
        user_id = update.effective_user.id
        group_id = update.effective_chat.id
        
        # 确保用户存在
        self.db.add_user(user_id, update.effective_user.username)
        
        # 获取群组设置
        settings = self.db.get_group_settings(group_id)
        if not settings:
            return
            
        points = 0
        
        # 处理文字消息
        if update.message.text:
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