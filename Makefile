.PHONY: install lint test typecheck security check

install:
	python -m pip install -r requirements-dev.txt
	python -m pip install --no-deps -e .

lint:
	ruff check .

test:
	pytest -q

typecheck:
	mypy src tests

security:
	bandit -q -r src

check: lint typecheck security test
