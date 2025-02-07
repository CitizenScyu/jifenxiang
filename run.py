from bot.bot import PointsBot
from config import BOT_TOKEN, WEBDAV_CONFIG, DATABASE_FILE
import logging

# 设置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    try:
        bot = PointsBot(BOT_TOKEN, WEBDAV_CONFIG, DATABASE_FILE)
        logging.info("Bot started successfully")
        bot.run()
    except Exception as e:
        logging.error(f"Error starting bot: {str(e)}")

if __name__ == '__main__':
    main()