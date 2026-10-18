.PHONY: install lint test typecheck security migration-check shell-check check

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
	bandit -q -r src apps

migration-check:
	python scripts/check_migration_sync.py

shell-check:
	bash -n scripts/backup_postgres.sh scripts/restore_postgres.sh

check: lint typecheck security test migration-check shell-check
