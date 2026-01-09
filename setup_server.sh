#!/bin/bash

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

print_error() {
    echo -e "${RED}❌  $1${NC}"
}

clear
echo -e "${GREEN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║        УСТАНОВКА бота НА СЕРВЕР                        ║"
echo "║                                                            ║"
echo "║   Этот скрипт поможет вам установить и настроить          ║"
echo "║   бота на вашем сервере                     ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

echo "Введите IP адрес сервера и нажмите ENTER:"
read -r SERVER_IP

if [ -z "$SERVER_IP" ]; then
    print_error "IP адрес не может быть пустым!"
    exit 1
fi

echo ""
echo "Введите пароль от сервера и нажмите ENTER:"
read -r SERVER_PASSWORD

if [ -z "$SERVER_PASSWORD" ]; then
    print_error "Пароль не может быть пустым!"
    exit 1
fi

echo "Обновление начато..."

if ! command -v sshpass &> /dev/null; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install sshpass 2>/dev/null || brew install hudochenkov/sshpass/sshpass
    else
        sudo apt install -y sshpass
    fi
fi

# нет подключения по ssh ключу
sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no root@$SERVER_IP << 'ENDSSH'

set -e

GREEN='\033[0;32m'
NC='\033[0m'
sudo truncate -s 0 /var/log/btmp.1
sudo truncate -s 0 /var/log/syslog
journalctl --vacuum-size=1M
sudo apt clean
sudo rm -f /var/log/*.gz /var/log/*.1 /var/log/*.2 /var/log/*.old
cd ~
if [ -d "tink-tr" ]; then
    cd tink-tr
    git pull
else
    git clone https://github.com/visionXIT/tink-tr.git
    cd tink-tr
fi

cd ~/tink-tr
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt

# убиваем все screen, так как на сервере они используются только для запуска бота. Вначале останавливаем все предыдущие сессии
pkill screen 2>/dev/null || true
killall screen
sleep 1

cd ~/tink-tr
source venv/bin/activate
screen -dmS tink-tr bash -c "cd ~/tink-tr && source venv/bin/activate && make start"
sleep 2

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║           🎉 УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО! 🎉              ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║      Приложение запущено и работает в фоновом режиме      ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

ENDSSH

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║                    ✅ ГОТОВО! ✅                           ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║         Приложение успешно установлено на сервер          ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
