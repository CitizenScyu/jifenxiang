from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config.config import Config

# 创建模块级别的 engine
engine = create_engine(Config.DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(engine)
    return engine

def get_session():
    """获取数据库会话"""
    return SessionLocal()

class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(Integer, unique=True, index=True)
    username = Column(String)
    points = Column(Integer, default=0)
    last_checkin = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    invitations = relationship("Invitation", back_populates="inviter")
    lottery_participations = relationship("LotteryParticipation", back_populates="user")

class Invitation(Base):
    """邀请记录表"""
    __tablename__ = "invitations"
    
    id = Column(Integer, primary_key=True, index=True)
    inviter_id = Column(Integer, ForeignKey("users.tg_id"))
    invitee_id = Column(Integer, unique=True)
    invite_code = Column(String(8), unique=True)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    used_at = Column(DateTime, nullable=True)
    
    # 关系
    inviter = relationship("User", back_populates="invitations")

class Lottery(Base):
    """抽奖活动表"""
    __tablename__ = "lotteries"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    points_required = Column(Integer)
    min_participants = Column(Integer)
    winners_count = Column(Integer)
    keyword = Column(String, nullable=True)
    end_time = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    participations = relationship("LotteryParticipation", back_populates="lottery")

class LotteryParticipation(Base):
    """抽奖参与记录表"""
    __tablename__ = "lottery_participations"
    
    id = Column(Integer, primary_key=True, index=True)
    lottery_id = Column(Integer, ForeignKey("lotteries.id"))
    user_id = Column(Integer, ForeignKey("users.tg_id"))
    is_winner = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    lottery = relationship("Lottery", back_populates="participations")
    user = relationship("User", back_populates="lottery_participations")
