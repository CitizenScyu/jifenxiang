BOT_TOKEN=你的机器人token
WEBDAV_HOST=你的WebDAV服务器地址
WEBDAV_LOGIN=WebDAV用户名
WEBDAV_PASSWORD=WebDAV密码
ADMIN_IDS=123456,789012  # 管理员的Telegram ID，多个管理员用逗号分隔
SUPER_ADMIN=123456  # 超级管理员ID，可以添加其他管理员
ALLOWED_GROUPS=-1002095853019  # 允许使用机器人的群组ID，多个群组用逗号分隔


pip install -r requirements.txt


python run.py
