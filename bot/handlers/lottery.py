from telegram import Update
from telegram.ext import CallbackContext
from datetime import datetime, timedelta
import random
from .admin import is_admin

class LotteryHandlers:
    def __init__(self, db):
        self.db = db

    def create_lottery(self, update: Update, context: CallbackContext):
        if not is_admin(update, context):
            update.message.reply_text("此命令仅管理员可用")
            return

        try:
            # /createlottery <积分> <人数> <小时> <获奖人数> [口令]
            points = int(context.args[0])
            max_participants = int(context.args[1]) if len(context.args) > 1 else 0
            hours = int(context.args[2])
            winners_count = int(context.args[3])
            keyword = ' '.join(context.args[4:]) if len(context.args) > 4 else None
            
            end_time = datetime.now() + timedelta(hours=hours)
            
            lottery_id = self.db.create_lottery(
                update.effective_chat.id,
                update.effective_user.id,
                points,
                keyword,
                end_time,
                max_participants,
                winners_count
            )
            
            msg = f"抽奖已创建！\n"
            msg += f"需要积分：{points}\n"
            if max_participants > 0:
                msg += f"最大参与人数：{max_participants}\n"
            msg += f"结束时间：{end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            if keyword:
                msg += f"参与口令：{keyword}\n"
            msg += f"获奖人数：{winners_count}"
            
            update.message.reply_text(msg)
            
        except (IndexError, ValueError):
            update.message.reply_text(
                "使用方法: /createlottery <积分> <人数> <小时> <获奖人数> [口令]\n"
                "示例：/createlottery 100 50 24 3 幸运"
            )

    def join_lottery(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        group_id = update.effective_chat.id
        
        active_lotteries = self.db.get_active_lotteries(group_id)
        
        if not active_lotteries:
            update.message.reply_text("当前没有进行中的抽奖")
            return
            
        for lottery in active_lotteries:
            lottery_id = lottery[0]
            points_required = lottery[3]
            keyword = lottery[4]
            
            if keyword and update.message.text != keyword:
                continue
                
            user = self.db.get_user(user_id)
            if not user or user[2] < points_required:
                update.message.reply_text("您的积分不足以参与此抽奖")
                return
                
            try:
                self.db.join_lottery(lottery_id, user_id)
                self.db.update_points(user_id, -points_required)
                update.message.reply_text("成功参与抽奖！")
            except Exception as e:
                update.message.reply_text("您已经参与过此抽奖")

    def force_draw(self, update: Update, context: CallbackContext):
        if not is_admin(update, context):
            update.message.reply_text("此命令仅管理员可用")
            return

        try:
            lottery_id = int(context.args[0])
            
            cursor = self.db.conn.cursor()
            cursor.execute(
                'SELECT * FROM lottery_participants WHERE lottery_id = ?',
                (lottery_id,)
            )
            participants = cursor.fetchall()
            
            cursor.execute('SELECT * FROM lotteries WHERE id = ?', (lottery_id,))
            lottery = cursor.fetchone()
            
            if not lottery or lottery[7] != 'active':
                update.message.reply_text("无效的抽奖ID或抽奖已结束")
                return
                
            winners = random.sample(participants, min(len(participants), lottery[8]))
            
            winner_text = "抽奖结果：\n"
            for winner in winners:
                winner_text += f"用户ID: {winner[1]}\n"
                
            cursor.execute(
                'UPDATE lotteries SET status = "completed" WHERE id = ?',
                (lottery_id,)
            )
            self.db.conn.commit()
            
            update.message.reply_text(winner_text)
            
        except (IndexError, ValueError):
            update.message.reply_text("使用方法: /forcedraw <抽奖ID>")