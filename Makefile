.PHONY: install lint test typecheck security migration-check shell-check evaluation-check check

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

evaluation-check:
	python scripts/evaluate_twi.py --dataset benchmarks/twi/v1/cases.json --results benchmarks/twi/v1/sample_results.json --now 2026-10-19T12:00:00Z --json-out /tmp/twi-evaluation.json --markdown-out /tmp/twi-evaluation.md

check: lint typecheck security test migration-check shell-check evaluation-check
