.PHONY: install lint test typecheck security check

install:
	python -m pip install -e '.[dev]'

lint:
	ruff check .

test:
	pytest -q

typecheck:
	mypy src tests

security:
	bandit -q -r src

check: lint typecheck security test
