start:
	source venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --port 80 --host 0.0.0.0
dev:
	uvicorn app.main:app --reload
acc:
	python m.py