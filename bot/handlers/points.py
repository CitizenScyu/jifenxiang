from telegram import Update
from telegram.ext import CallbackContext
from datetime import datetime, timedelta
import random
import string

class PointsHandlers:
    def __init__(self, db):
        self.db = db

    def check_points(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        user = self.db.get_user(user_id)
        
        if user:
            update.message.reply_text(f"您当前的积分为: {user[2]}")
        else:
            update.message.reply_text("您还没有积分记录")

    def daily_checkin(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        group_id = update.effective_chat.id
        
        user = self.db.get_user(user_id)
        if not user:
            update.message.reply_text("请先发送消息以创建账户")
            return
            
        last_checkin = user[3]
        if last_checkin:
            last_checkin = datetime.strptime(last_checkin, '%Y-%m-%d').date()
            if last_checkin == datetime.now().date():
                update.message.reply_text("您今天已经签到过了")
                return
        
        settings = self.db.get_group_settings(group_id)
        daily_points = settings[4] if settings else 5
        
        self.db.update_points(user_id, daily_points)
        cursor = self.db.conn.cursor()
        cursor.execute(
            'UPDATE users SET last_checkin = ? WHERE user_id = ?',
            (datetime.now().date().isoformat(), user_id)
        )
        self.db.conn.commit()
        
        update.message.reply_text(f"签到成功！获得 {daily_points} 积分")

    def generate_invite(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        user = self.db.get_user(user_id)
        
        if not user:
            update.message.reply_text("请先发送消息以创建账户")
            return
            
        if not user[4]:  # 如果没有邀请码
            invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            cursor = self.db.conn.cursor()
            cursor.execute(
                'UPDATE users SET invite_code = ? WHERE user_id = ?',
                (invite_code, user_id)
            )
            self.db.conn.commit()
        else:
            invite_code = user[4]
            
        invite_link = f"https://t.me/{context.bot.username}?start={invite_code}"
        
        # 获取邀请统计
        cursor = self.db.conn.cursor()
        cursor.execute(
            'SELECT COUNT(*), SUM(points_awarded) FROM invite_history WHERE inviter_id = ?',
            (user_id,)
        )
        invite_stats = cursor.fetchone()
        
        update_message = f"您的邀请链接：{invite_link}\n"
        update_message += f"已成功邀请：{invite_stats[0] or 0} 人\n"
        update_message += f"获得邀请积分：{invite_stats[1] or 0}"
        
        update.message.reply_text(update_message)