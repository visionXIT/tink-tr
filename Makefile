start:
	@git pull
	@./venv/bin/uvicorn app.main:app --port 80 --host 0.0.0.0
dev:
	./venv/bin/uvicorn app.main:app --reload
acc:
	@git pull
	@./venv/bin/python m.py
run:
	@echo "Запуск бота..."
	@killall screen || true
	@cd ~/tink-tr && git pull
	@screen -dmS tink-tr bash -c "cd ~/tink-tr && make start"
	@echo "Бот запущен"