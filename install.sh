#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 打印信息函数
print_message() {
    echo -e "${GREEN}[INFO] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# 检查并安装基础依赖
install_basic_dependencies() {
    print_message "检查并安装基础依赖..."
    apt-get update
    apt-get install -y curl wget git software-properties-common apt-transport-https ca-certificates gnupg
}

# 检查并安装 Python 环境
install_python() {
    print_message "检查 Python 环境..."
    apt-get install -y python3 python3-pip python3-venv
}

# 检查并安装 Supervisor
install_supervisor() {
    print_message "检查 Supervisor..."
    apt-get install -y supervisor
    systemctl enable supervisor
    systemctl start supervisor
}

# 检查系统要求
check_system() {
    if [ "$EUID" -ne 0 ]; then 
        print_error "请使用root权限运行此脚本"
        print_error "请使用: sudo bash install.sh"
        exit 1
    fi
    
    if [ ! -f /etc/debian_version ]; then
        print_error "此脚本只支持Debian/Ubuntu系统"
        exit 1
    fi
}

# 配置防火墙
configure_firewall() {
    print_message "配置防火墙..."
    apt-get install -y ufw
    ufw allow ssh
    ufw allow 80/tcp
    ufw allow 443/tcp
    echo "y" | ufw enable
}

# 安装依赖包
install_dependencies() {
    print_message "安装项目依赖..."
    source ${WORK_DIR}/venv/bin/activate
    pip3 install --upgrade pip
    pip3 install python-telegram-bot==20.6
    pip3 install sqlalchemy==2.0.23
    pip3 install aiosqlite==0.19.0
    pip3 install python-dotenv==1.0.0
    pip3 install webdavclient3==3.14.6
    pip3 install schedule==1.2.0
}

# 创建日志目录和文件
setup_logging() {
    print_message "设置日志系统..."
    mkdir -p ${WORK_DIR}/logs
    touch ${WORK_DIR}/logs/bot.log
    touch ${WORK_DIR}/logs/backup.log
    touch ${WORK_DIR}/logs/error.log
    chmod 644 ${WORK_DIR}/logs/*.log
}

# 主安装函数
main() {
    print_message "开始安装 Telegram Points Bot..."
    
    # 检查系统
    check_system
    install_basic_dependencies
    install_python
    install_supervisor
    configure_firewall
    
    # 获取用户输入
    read -p "请输入Telegram Bot Token: " BOT_TOKEN
    read -p "请输入管理员ID: " ADMIN_ID
    read -p "请输入WebDAV地址: " WEBDAV_HOST
    read -p "请输入WebDAV用户名: " WEBDAV_USERNAME
    read -p "请输入WebDAV密码: " WEBDAV_PASSWORD
    read -p "请输入允许使用的群组ID或用户名(多个用逗号分隔): " ALLOWED_GROUPS
    
    # 创建工作目录
    WORK_DIR="/opt/tg_bot"
    print_message "创建工作目录..."
    mkdir -p $WORK_DIR
    cd $WORK_DIR
    
    # 创建虚拟环境
    print_message "创建Python虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate

    # 下载源代码
    print_message "下载源代码..."
    if [ ! "$(ls -A ${WORK_DIR})" ]; then
        git clone https://github.com/CitizenScyu/jifenxiang.git .
    else
        # 如果目录不为空，只复制src目录内容
        cp -r src/* ${WORK_DIR}/
    fi
    
    setup_logging
    install_dependencies
    
    # 创建配置文件
    print_message "创建配置文件..."
    cat > .env << EOL
BOT_TOKEN=${BOT_TOKEN}
DATABASE_URL=sqlite:///bot.db
ADMIN_IDS=${ADMIN_ID}

# WebDAV配置
WEBDAV_HOST=${WEBDAV_HOST}
WEBDAV_USERNAME=${WEBDAV_USERNAME}
WEBDAV_PASSWORD=${WEBDAV_PASSWORD}

# 群组白名单
ALLOWED_GROUPS=${ALLOWED_GROUPS}
EOL
    
    # 配置supervisor
    print_message "配置supervisor..."
    cat > /etc/supervisor/conf.d/tg_bot.conf << EOL
[program:tg_bot]
directory=${WORK_DIR}
command=${WORK_DIR}/venv/bin/python ${WORK_DIR}/src/main.py
autostart=true
autorestart=true
stderr_logfile=${WORK_DIR}/logs/err.log
stdout_logfile=${WORK_DIR}/logs/out.log
user=root
environment=PATH="${WORK_DIR}/venv/bin"
EOL
    
    # 设置权限
    chown -R root:root ${WORK_DIR}
    chmod -R 755 ${WORK_DIR}
    chmod 600 ${WORK_DIR}/.env
    
    # 创建管理脚本
    cat > manage.sh << EOL
#!/bin/bash
case "\$1" in
    start)
        supervisorctl start tg_bot
        ;;
    stop)
        supervisorctl stop tg_bot
        ;;
    restart)
        supervisorctl restart tg_bot
        ;;
    status)
        supervisorctl status tg_bot
        ;;
    logs)
        tail -f ${WORK_DIR}/logs/out.log
        ;;
    errors)
        tail -f ${WORK_DIR}/logs/err.log
        ;;
    backup)
        ${WORK_DIR}/venv/bin/python ${WORK_DIR}/src/backup.py
        ;;
    restore)
        ${WORK_DIR}/venv/bin/python ${WORK_DIR}/src/restore.py
        ;;
    update)
        cd ${WORK_DIR}
        git pull
        supervisorctl restart tg_bot
        ;;
    *)
        echo "Usage: \$0 {start|stop|restart|status|logs|errors|backup|restore|update}"
        exit 1
        ;;
esac
EOL

    chmod +x manage.sh
    
    # 启动服务
    print_message "启动服务..."
    supervisorctl reread
    supervisorctl update
    supervisorctl restart tg_bot
    
    # 检查服务状态
    sleep 5
    if supervisorctl status tg_bot | grep -q RUNNING; then
        print_message "✅ 安装成功！机器人已经启动。"
        print_message "📝 使用以下命令管理机器人："
        print_message "./manage.sh start    - 启动机器人"
        print_message "./manage.sh stop     - 停止机器人"
        print_message "./manage.sh restart  - 重启机器人"
        print_message "./manage.sh status   - 查看状态"
        print_message "./manage.sh logs     - 查看日志"
        print_message "./manage.sh errors   - 查看错误日志"
        print_message "./manage.sh backup   - 手动备份"
        print_message "./manage.sh restore  - 恢复数据"
        print_message "./manage.sh update   - 更新代码"
        
        print_message "\n💡 提示："
        print_message "1. 所有日志文件位于 ${WORK_DIR}/logs/ 目录"
        print_message "2. 配置文件位于 ${WORK_DIR}/.env"
        print_message "3. 数据库文件位于 ${WORK_DIR}/bot.db"
    else
        print_error "❌ 启动失败，请检查日志文件"
        print_error "tail -f ${WORK_DIR}/logs/err.log"
    fi
}

# 运行主函数
main
