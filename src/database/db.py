from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.config import Config

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True)
    username = Column(String)
    points = Column(Float, default=0)
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
