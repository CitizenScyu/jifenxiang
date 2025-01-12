import random
import string
from database.db import User, Invitation
from config.config import Config

class InvitationSystem:
    def __init__(self, db_session):
        self.db = db_session
    
    def generate_invite_code(self):
        """生成唯一的邀请码"""
        while True:
            code = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            if not self.db.query(User).filter_by(invite_code=code).first():
                return code
    
    async def generate_invite_link(self, user_id):
        """为用户生成邀请链接"""
        user = self.db.query(User).filter_by(tg_id=user_id).first()
        if not user:
            return None
            
        if not user.invite_code:
            user.invite_code = self.generate_invite_code()
            self.db.commit()
            
        return f"https://t.me/你的机器人用户名?start={user.invite_code}"
    
    async def process_invitation(self, inviter_code, new_user_id):
        """处理邀请"""
        if not inviter_code:
            return False
            
        inviter = self.db.query(User).filter_by(invite_code=inviter_code).first()
        if not inviter or inviter.tg_id == new_user_id:
            return False
            
        # 检查是否已经被邀请过
        existing_invitation = self.db.query(Invitation).filter_by(invitee_id=new_user_id).first()
        if existing_invitation:
            return False
            
        # 创建邀请记录
        invitation = Invitation(inviter_id=inviter.tg_id, invitee_id=new_user_id)
        self.db.add(invitation)
        
        # 给邀请人加分
        inviter.points += Config.INVITATION_POINTS
        self.db.commit()
        
        return True
        
    async def get_invitation_count(self, user_id):
        """获取用户邀请的人数"""
        return self.db.query(Invitation).filter_by(inviter_id=user_id).count()
