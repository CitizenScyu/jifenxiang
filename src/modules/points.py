from datetime import datetime
from sqlalchemy import desc
from database.db import User
from config.config import Config
from math import ceil

class PointSystem:
    def __init__(self, db_session):
        self.db = db_session
        
async def add_points(self, user_id, points):
    user = self.db.query(User).filter_by(tg_id=user_id).first()
    if user:
        user.points = float(user.points) + float(points)  # 确保类型转换
        self.db.commit()
        return True
    return False
    
    async def check_message_validity(self, message):
        if len(message.text) >= Config.MIN_TEXT_LENGTH:
            return True
        return False
        
    async def daily_checkin(self, user_id):
        user = self.db.query(User).filter_by(tg_id=user_id).first()
        if not user:
            return False
            
        today = datetime.now().strftime('%Y-%m-%d')
        
        if user.last_checkin != today:
            user.points += Config.DAILY_CHECKIN_POINTS
            user.last_checkin = today
            self.db.commit()
            return True
        return False

    async def get_user_points(self, user_id):
        user = self.db.query(User).filter_by(tg_id=user_id).first()
        if user:
            return user.points, user.username
        return None, None
        
    async def get_points_leaderboard(self, page=1, per_page=20):
        total_users = self.db.query(User).count()
        total_pages = ceil(total_users / per_page)
        
        users = self.db.query(User)\
            .order_by(desc(User.points))\
            .offset((page - 1) * per_page)\
            .limit(per_page)\
            .all()
            
        leaderboard_text = "📊 积分排行榜\n\n"
        start_rank = (page - 1) * per_page + 1
        
        for i, user in enumerate(users):
            rank = start_rank + i
            rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
            username = user.username or "未设置用户名"
            leaderboard_text += f"{rank_emoji} {username}: {round(float(user.points))}分\n"
            
        leaderboard_text += f"\n第 {page}/{total_pages} 页"
        
        return leaderboard_text, total_pages
