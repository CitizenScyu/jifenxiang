from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from datetime import datetime, timedelta
import random
import logging
from .admin import is_admin
from config import ALLOWED_GROUPS, MAX_LOTTERY_DURATION, MAX_WINNERS

logger = logging.getLogger(__name__)

class LotteryHandlers:
    def __init__(self, db):
        self.db = db
        self.pending_lottery = {}  # 存储正在创建的抽奖信息

    def start_lottery_setup(self, update: Update, context: CallbackContext):
        # 检查是否在群组中
        if update.effective_chat.type in ['group', 'supergroup']:
            if not is_admin(update, context):
                update.message.reply_text("只有管理员可以创建抽奖")
                return
                
            if not self.db.is_group_allowed(update.effective_chat.id):
                update.message.reply_text("此群组不在白名单中")
                return
                
            # 存储群组ID
            self.pending_lottery[update.effective_user.id] = {
                'step': 'prize_description',
                'group_id': update.effective_chat.id
            }
            
            # 发送私聊链接
            bot_username = context.bot.username
            deep_link = f"https://t.me/{bot_username}?start=lottery"
            
            update.message.reply_text(
                "🎉 请点击下方链接私聊我设置抽奖\n"
                f"{deep_link}"
            )
            return
            
        # 如果已经在私聊中
        if update.effective_user.id not in self.pending_lottery:
            update.message.reply_text("请先在群组中使用 /setlottery 命令")
            return
            
        update.message.reply_text("请输入奖品描述")

    def handle_start_command(self, update: Update, context: CallbackContext):
        """处理 /start lottery 命令"""
        if not context.args or context.args[0] != 'lottery':
            return False
            
        if update.effective_user.id not in self.pending_lottery:
            update.message.reply_text("请先在群组中使用 /setlottery 命令")
            return True
            
        update.message.reply_text("请输入奖品描述")
        return True

    def handle_lottery_setup(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        if user_id not in self.pending_lottery:
            return False

        lottery_info = self.pending_lottery[user_id]
        message_text = update.message.text

        if lottery_info['step'] == 'prize_description':
            lottery_info['prize_description'] = message_text
            lottery_info['step'] = 'winners_count'
            update.message.reply_text(
                "请输入获奖人数\n"
                f"（最大{MAX_WINNERS}人）"
            )
            return True

        elif lottery_info['step'] == 'winners_count':
            try:
                winners_count = int(message_text)
                if winners_count <= 0 or winners_count > MAX_WINNERS:
                    update.message.reply_text(f"获奖人数必须在1-{MAX_WINNERS}之间")
                    return True
                lottery_info['winners_count'] = winners_count
                lottery_info['step'] = 'lottery_type'
                
                keyboard = [
                    [InlineKeyboardButton("积分抽奖", callback_data='lottery_type_points')],
                    [InlineKeyboardButton("口令抽奖", callback_data='lottery_type_keyword')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text("请选择抽奖类型：", reply_markup=reply_markup)
            except ValueError:
                update.message.reply_text("请输入有效的数字")
            return True

        elif lottery_info['step'] == 'points_required':
            try:
                points = int(message_text)
                if points < 0:
                    update.message.reply_text("积分不能为负数")
                    return True
                lottery_info['points_required'] = points
                lottery_info['step'] = 'duration'
                update.message.reply_text(
                    "请输入抽奖持续时间（小时）\n"
                    f"（最大{MAX_LOTTERY_DURATION}小时）"
                )
            except ValueError:
                update.message.reply_text("请输入有效的数字")
            return True

        elif lottery_info['step'] == 'keyword':
            lottery_info['keyword'] = message_text
            lottery_info['step'] = 'duration'
            update.message.reply_text(
                "请输入抽奖持续时间（小时）\n"
                f"（最大{MAX_LOTTERY_DURATION}小时）"
            )
            return True

        elif lottery_info['step'] == 'duration':
            try:
                duration = int(message_text)
                if duration <= 0 or duration > MAX_LOTTERY_DURATION:
                    update.message.reply_text(f"持续时间必须在1-{MAX_LOTTERY_DURATION}小时之间")
                    return True
                    
                end_time = datetime.now() + timedelta(hours=duration)
                
                # 创建抽奖
                lottery_id = self.db.create_lottery(
                    lottery_info['group_id'],
                    user_id,
                    lottery_info.get('points_required', 0),
                    lottery_info.get('keyword', ''),
                    end_time,
                    0,  # max_participants
                    lottery_info['winners_count'],
                    lottery_info['prize_description']
                )

                # 在群组中发布抽奖信息
                lottery_text = (
                    f"🎉 新抽奖活动 #{lottery_id}\n\n"
                    f"🎁 奖品：{lottery_info['prize_description']}\n"
                    f"👥 获奖人数：{lottery_info['winners_count']}\n"
                    f"⏰ 结束时间：{end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                
                if lottery_info.get('points_required', 0) > 0:
                    lottery_text += f"💰 参与所需积分：{lottery_info['points_required']}\n"
                    lottery_text += "使用 /joinlottery 参与抽奖"
                else:
                    lottery_text += f"🔑 参与口令：{lottery_info['keyword']}\n"
                    lottery_text += "发送口令即可参与抽奖"

                context.bot.send_message(
                    lottery_info['group_id'],
                    lottery_text,
                    parse_mode=ParseMode.HTML
                )

                del self.pending_lottery[user_id]
                update.message.reply_text("✅ 抽奖创建成功！")
                logger.info(f"Admin {user_id} created lottery #{lottery_id}")
            except ValueError:
                update.message.reply_text("请输入有效的数字")
            return True

        return False

    def handle_callback_query(self, update: Update, context: CallbackContext):
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id not in self.pending_lottery:
            query.answer("抽奖设置已过期")
            return
            
        lottery_info = self.pending_lottery[user_id]
        
        if query.data == 'lottery_type_points':
            lottery_info['step'] = 'points_required'
            query.edit_message_text("请输入参与所需积分")
        elif query.data == 'lottery_type_keyword':
            lottery_info['step'] = 'keyword'
            query.edit_message_text("请输入参与口令")
            
        query.answer()

    def join_lottery(self, update: Update, context: CallbackContext):
        if not update.effective_chat.type in ['group', 'supergroup']:
            update.message.reply_text("请在群组中使用此命令")
            return
            
        try:
            lottery_id = int(context.args[0])
        except (IndexError, ValueError):
            update.message.reply_text("使用方法: /joinlottery <抽奖ID>")
            return
            
        lottery = self.db.get_lottery(lottery_id)
        if not lottery:
            update.message.reply_text("找不到该抽奖")
            return
            
        if lottery[7] != 'active':
            update.message.reply_text("该抽奖已结束")
            return
            
        if lottery[1] != update.effective_chat.id:
            update.message.reply_text("该抽奖不属于此群组")
            return
            
        user = self.db.get_user(update.effective_user.id)
        if not user:
            update.message.reply_text("请先发送消息以创建账户")
            return
            
        if lottery[3] > 0:  # 积分抽奖
            if user[2] < lottery[3]:
                update.message.reply_text("您的积分不足以参与此抽奖")
                return
                
            # 扣除积分
            self.db.update_points(update.effective_user.id, -lottery[3])
            
        # 加入抽奖
        if self.db.join_lottery(lottery_id, update.effective_user.id, update.effective_user.username):
            update.message.reply_text("✅ 成功参与抽奖！")
            logger.info(f"User {update.effective_user.id} joined lottery #{lottery_id}")
        else:
            update.message.reply_text("您已经参与过此抽奖")
            if lottery[3] > 0:  # 如果是积分抽奖，退还积分
                self.db.update_points(update.effective_user.id, lottery[3])