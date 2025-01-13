from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, UniqueConstraint, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config.config import Config

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True)
    username = Column(String)
    points = Column(Float, default=0.0)
    invite_code = Column(String, unique=True)
    last_checkin = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<User(tg_id={self.tg_id}, username={self.username}, points={self.points})>"

class Invitation(Base):
    __tablename__ = 'invitations'
    
    id = Column(Integer, primary_key=True)
    inviter_id = Column(Integer)
    invitee_id = Column(Integer, unique=True)  # 确保每个用户只能被邀请一次
    rewarded = Column(Boolean, default=True)  # 是否已发放奖励
    
    __table_args__ = (
        UniqueConstraint('inviter_id', 'invitee_id', name='unique_invitation'),
    )
    
    def __repr__(self):
        return f"<Invitation(inviter_id={self.inviter_id}, invitee_id={self.invitee_id}, rewarded={self.rewarded})>"

class Lottery(Base):
    __tablename__ = 'lotteries'
    
    id = Column(Integer, primary_key=True)
    title = Column(String)  # 抽奖标题
    description = Column(String)  # 抽奖描述
    creator_id = Column(Integer)  # 创建者ID
    points_required = Column(Integer, default=0)  # 参与所需积分
    winners_count = Column(Integer)  # 中奖人数
    min_participants = Column(Integer, default=0)  # 最少参与人数
    keyword = Column(String, nullable=True)  # 关键词(如果是关键词抽奖)
    status = Column(String, default='active')  # active, completed, cancelled
    end_time = Column(DateTime, nullable=True)  # 结束时间
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Lottery(id={self.id}, title={self.title}, status={self.status})>"

class LotteryParticipant(Base):
    __tablename__ = 'lottery_participants'
    
    id = Column(Integer, primary_key=True)
    lottery_id = Column(Integer)
    user_id = Column(Integer)
    joined_at = Column(DateTime, default=datetime.now)
    is_winner = Column(Boolean, default=False)
    
    __table_args__ = (
        UniqueConstraint('lottery_id', 'user_id', name='unique_lottery_participant'),
    )
    
    def __repr__(self):
        return f"<LotteryParticipant(lottery_id={self.lottery_id}, user_id={self.user_id}, is_winner={self.is_winner})>"

def init_db():
    """初始化数据库，创建所有表"""
    engine = create_engine(Config.DATABASE_URL)
    Base.metadata.create_all(engine)
    return engine

def get_session():
    """获取数据库会话"""
    engine = create_engine(Config.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()
