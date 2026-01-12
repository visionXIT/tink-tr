start:
	@git pull
	@source venv/bin/activate
	@uvicorn app.main:app --port 80 --host 0.0.0.0
dev:
	uvicorn app.main:app --reload
acc:
	@git pull
	@python m.py
run:
	@echo "Запуск бота..."
	@killall screen || true
	@cd ~/tink-tr && git pull
	@screen -dmS tink-tr bash -c "cd ~/tink-tr && make start"
	@echo "Бот запущен"