from datetime import datetime
from database.db import Lottery, LotteryParticipation, User
import random
import asyncio
from config.config import Config

class LotterySystem:
    def __init__(self, db_session):
        self.db = db_session
        
    async def create_lottery(self, creator_id, title, description, winners_count, 
                           points_required=0, min_participants=0, keyword=None, 
                           end_time=None):
        """创建新抽奖"""
        # 检查创建者是否是管理员
        if creator_id not in Config.ADMIN_IDS:
            return False, "只有管理员可以创建抽奖"
            
        lottery = Lottery(
            title=title,
            description=description,
            creator_id=creator_id,
            winners_count=winners_count,
            points_required=points_required,
            min_participants=min_participants,
            keyword=keyword,
            end_time=end_time
        )
        self.db.add(lottery)
        self.db.commit()
        return True, lottery
        
    async def join_lottery(self, lottery_id, user_id):
        """参加抽奖"""
        lottery = self.db.query(Lottery).filter_by(id=lottery_id).first()
        if not lottery:
            return False, "抽奖不存在"
            
        if lottery.status != 'active':
            return False, "抽奖已结束"
            
        # 检查是否已参加
        if self.db.query(LotteryParticipant).filter_by(
            lottery_id=lottery_id, user_id=user_id).first():
            return False, "你已经参加过这个抽奖了"
            
        # 如果需要积分，检查并扣除积分
        if lottery.points_required > 0:
            user = self.db.query(User).filter_by(tg_id=user_id).first()
            if not user or user.points < lottery.points_required:
                return False, f"积分不足，需要{lottery.points_required}积分"
            user.points -= lottery.points_required
            
        participant = LotteryParticipant(
            lottery_id=lottery_id,
            user_id=user_id
        )
        self.db.add(participant)
        self.db.commit()
        return True, "成功参加抽奖！"
        
    async def draw_lottery(self, lottery_id, admin_id):
        """开奖"""
        if admin_id not in Config.ADMIN_IDS:
            return False, "只有管理员可以开奖"
            
        lottery = self.db.query(Lottery).filter_by(id=lottery_id).first()
        if not lottery:
            return False, "抽奖不存在"
            
        if lottery.status != 'active':
            return False, "抽奖已结束"
            
        participants = self.db.query(LotteryParticipant).filter_by(
            lottery_id=lottery_id).all()
            
        if len(participants) < lottery.min_participants:
            return False, f"参与人数不足，需要至少{lottery.min_participants}人参加"
            
        # 随机抽取获奖者
        winners = random.sample(participants, 
                              min(lottery.winners_count, len(participants)))
        
        # 更新获奖状态
        winner_info = []
        for winner in winners:
            winner.is_winner = True
            user = self.db.query(User).filter_by(tg_id=winner.user_id).first()
            if user:
                winner_info.append(user.username or str(user.tg_id))
            
        lottery.status = 'completed'
        self.db.commit()
        
        return True, winner_info

    async def get_lottery_info(self, lottery_id):
        """获取抽奖信息"""
        lottery = self.db.query(Lottery).filter_by(id=lottery_id).first()
        if not lottery:
            return None
            
        participants_count = self.db.query(LotteryParticipant).filter_by(
            lottery_id=lottery_id).count()
            
        info = {
            'title': lottery.title,
            'description': lottery.description,
            'points_required': lottery.points_required,
            'winners_count': lottery.winners_count,
            'min_participants': lottery.min_participants,
            'current_participants': participants_count,
            'status': lottery.status,
            'keyword': lottery.keyword,
            'end_time': lottery.end_time
        }
        return info

    async def list_active_lotteries(self):
        """列出所有进行中的抽奖"""
        lotteries = self.db.query(Lottery).filter_by(status='active').all()
        return lotteries

    async def check_keyword_lottery(self, message):
        """检查关键词并参与抽奖"""
        text = message.text.strip()
        user_id = message.from_user.id
        
        lottery = self.db.query(Lottery).filter(
            Lottery.status == 'active',
            Lottery.keyword != None,
            Lottery.keyword == text
        ).first()
        
        if lottery:
            return await self.join_lottery(lottery.id, user_id)
        return None, None

    async def auto_draw_checker(self):
        """检查并执行自动开奖"""
        while True:
            try:
                now = datetime.now()
                lotteries = self.db.query(Lottery).filter(
                    Lottery.status == 'active',
                    Lottery.end_time != None,
                    Lottery.end_time <= now
                ).all()
                
                for lottery in lotteries:
                    await self.draw_lottery(lottery.id, lottery.creator_id)
                    
            except Exception as e:
                print(f"Auto draw checker error: {str(e)}")
                
            await asyncio.sleep(60)  # 每分钟检查一次
