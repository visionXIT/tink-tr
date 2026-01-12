#!/bin/bash
echo "Запуск бота..."
killall screen || true
cd ~/tink-tr
git pull
screen -dmS tink-tr bash -c "cd ~/tink-tr && source venv/bin/activate && make start"
echo "Бот запущен"