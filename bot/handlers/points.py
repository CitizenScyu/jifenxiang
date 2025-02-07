from telegram import Update, ParseMode
from telegram.ext import CallbackContext
from datetime import datetime, timedelta
import random
import string
import logging
from config import ALLOWED_GROUPS

logger = logging.getLogger(__name__)

class PointsHandlers:
    def __init__(self, db):
        self.db = db

    def check_points(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        user = self.db.get_user(user_id)
        
        if not user:
            update.message.reply_text("您还没有积分记录")
            return
            
        # 获取邀请统计
        cursor = self.db.conn.cursor()
        cursor.execute(
            'SELECT COUNT(*), SUM(points_awarded) FROM invite_history WHERE inviter_id = ?',
            (user_id,)
        )
        invite_stats = cursor.fetchone()
        
        stats_text = (
            f"👤 用户：@{user[1]}\n"
            f"💰 当前积分：{user[2]:.1f}\n"
            f"📅 注册时间：{user[6]}\n"
            f"🤝 成功邀请：{invite_stats[0] or 0} 人\n"
            f"✨ 邀请获得：{invite_stats[1] or 0} 积分"
        )
        
        update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)

    def daily_checkin(self, update: Update, context: CallbackContext):
        if not update.effective_chat.type in ['group', 'supergroup']:
            update.message.reply_text("请在群组中使用此命令")
            return
            
        if not self.db.is_group_allowed(update.effective_chat.id):
            update.message.reply_text("此群组不在白名单中")
            return
            
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
        
        update.message.reply_text(
            f"✅ 签到成功！\n💰 获得 {daily_points} 积分",
            parse_mode=ParseMode.HTML
        )
        logger.info(f"User {user_id} checked in and got {daily_points} points")

    def generate_invite(self, update: Update, context: CallbackContext):
        if not update.effective_chat.type in ['group', 'supergroup']:
            update.message.reply_text("请在群组中使用此命令")
            return
            
        if not self.db.is_group_allowed(update.effective_chat.id):
            update.message.reply_text("此群组不在白名单中")
            return
            
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
            
        # 获取群组信息
        chat = context.bot.get_chat(update.effective_chat.id)
        if not chat.username:
            update.message.reply_text("此群组未设置公开链接，无法生成邀请链接")
            return
            
        invite_link = f"https://t.me/{chat.username}?start={invite_code}"
        
        # 获取邀请统计
        cursor = self.db.conn.cursor()
        cursor.execute(
            'SELECT COUNT(*), SUM(points_awarded) FROM invite_history WHERE inviter_id = ?',
            (user_id,)
        )
        invite_stats = cursor.fetchone()
        
        settings = self.db.get_group_settings(update.effective_chat.id)
        invite_points = settings[5] if settings else 10
        
        update_message = (
            f"🔗 您的邀请链接：\n{invite_link}\n\n"
            f"📊 邀请统计：\n"
            f"👥 已邀请：{invite_stats[0] or 0} 人\n"
            f"💰 获得积分：{invite_stats[1] or 0}\n"
            f"✨ 每邀请一人可得：{invite_points} 积分"
        )
        
        update.message.reply_text(update_message, parse_mode=ParseMode.HTML)

    def handle_start_command(self, update: Update, context: CallbackContext):
        if len(context.args) == 1:
            invite_code = context.args[0]
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE invite_code = ?', (invite_code,))
            inviter = cursor.fetchone()
            
            if inviter:
                inviter_id = inviter[0]
                invited_id = update.effective_user.id
                
                # 检查是否已经被邀请过
                cursor.execute(
                    'SELECT * FROM invite_history WHERE invited_id = ?',
                    (invited_id,)
                )
                if not cursor.fetchone():
                    # 记录邀请
                    settings = self.db.get_group_settings(update.effective_chat.id)
                    invite_points = settings[5] if settings else 10
                    
                    cursor.execute(
                        'INSERT INTO invite_history (inviter_id, invited_id, group_id, points_awarded) VALUES (?, ?, ?, ?)',
                        (inviter_id, invited_id, update.effective_chat.id, invite_points)
                    )
                    self.db.update_points(inviter_id, invite_points)
                    self.db.conn.commit()
                    
                    logger.info(f"User {invited_id} was invited by {inviter_id} and awarded {invite_points} points")