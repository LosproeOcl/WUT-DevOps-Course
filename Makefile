.PHONY: data train train-lstm train-bert test lint coverage serve docker-build docker-run

PY = .venv/Scripts/python.exe

data:
	$(PY) -m ml.data_pipeline

train:
	$(PY) -m ml.train --data-version v2 --mode tuned

train-lstm:
	$(PY) -m ml.train_lstm --data-version v2

train-bert:
	$(PY) -m ml.train_bert --data-dir data --epochs 3

test:
	$(PY) -m pytest

coverage:
	$(PY) -m pytest --cov=app --cov=ml --cov-report=term-missing

lint:
	$(PY) -m ruff check app ml tests scripts

serve:
	$(PY) -m uvicorn app.main:app --reload

docker-build:
	docker build -t absa-app .

docker-run:
	docker run -p 8000:8000 absa-app
