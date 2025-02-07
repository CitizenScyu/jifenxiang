from bot.bot import PointsBot
from config import BOT_TOKEN, WEBDAV_CONFIG, DATABASE_FILE

def main():
    bot = PointsBot(BOT_TOKEN, WEBDAV_CONFIG, DATABASE_FILE)
    bot.run()

if __name__ == '__main__':
    main()