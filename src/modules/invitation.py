import random
import string
from src.database.db import User, Invitation
from src.config.config import Config

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
        """生成邀请码"""
        user = self.db.query(User).filter_by(tg_id=user_id).first()
        if not user:
            return None
            
        if not user.invite_code:
            user.invite_code = self.generate_invite_code()
            self.db.commit()
            
        return user.invite_code
    
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
            
        new_user = self.db.query(User).filter_by(tg_id=new_user_id).first()
        if not new_user:
            return False
            
        # 记录邀请关系并立即发放奖励
        invitation = Invitation(
            inviter_id=inviter.tg_id,
            invitee_id=new_user_id,
            rewarded=True
        )
        self.db.add(invitation)
        inviter.points += Config.INVITATION_POINTS
        self.db.commit()
        return True

    async def get_invitation_count(self, user_id):
        """获取用户成功邀请的人数"""
        return self.db.query(Invitation).filter_by(
            inviter_id=user_id,
            rewarded=True
        ).count()

    async def get_inviter_info(self, user_id):
        """获取邀请人信息"""
        invitation = self.db.query(Invitation).filter_by(invitee_id=user_id).first()
        if invitation:
            inviter = self.db.query(User).filter_by(tg_id=invitation.inviter_id).first()
            return inviter
        return None
