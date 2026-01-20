dev:
	./venv/bin/uvicorn app.main:app --reload
update:
	@cd ~/tink-tr && git pull && rm -f ~/Makefile && ln -s ~/tink-tr/Makefile ~/Makefile
acc:
	@git pull
	@[ -d venv ] || python3 -m venv venv
	@[ -f /tmp/t_tech_investments-0.3.3-py3-none-any.whl ] || wget -q -O /tmp/t_tech_investments-0.3.3-py3-none-any.whl https://files.pythonhosted.org/packages/89/41/ca4f7b8985c74035744313af8af999d82e5793f8f3fc676b7580dadc9653/t_tech_investments-0.3.3-py3-none-any.whl
	@./venv/bin/pip install -q /tmp/t_tech_investments-0.3.3-py3-none-any.whl
	@./venv/bin/pip install -q -r requirements.txt
	@./venv/bin/python m.py
run:
	@echo "Запуск бота..."
	@killall screen || true
	@cd ~/tink-tr && git pull
	@cd ~/tink-tr && ./venv/bin/pip install -q -r requirements.txt
	@screen -dmS tink-tr bash -c "cd ~/tink-tr && ./venv/bin/uvicorn app.main:app --port 80 --host 0.0.0.0"
	@echo "Бот запущен"