dev:
	./venv/bin/uvicorn app.main:app --reload
update:
	@cd ~/tink-tr && git pull && rm -f ~/Makefile && ln -s ~/tink-tr/Makefile ~/Makefile
acc:
	@cd ~/tink-tr && git pull
	@cd ~/tink-tr && [ -d venv ] || python3 -m venv venv
	@cd ~/tink-tr && ./venv/bin/pip install -q -r requirements.txt
	@cd ~/tink-tr && ./venv/bin/python m.py
run:
	@echo "Запуск бота..."
	@killall screen || true
	@cd ~/tink-tr && git pull
	@cd ~/tink-tr && ./venv/bin/pip install -q -r requirements.txt
	@screen -dmS tink-tr bash -c "cd ~/tink-tr && ./venv/bin/uvicorn app.main:app --port 80 --host 0.0.0.0"
	@echo "Бот запущен"