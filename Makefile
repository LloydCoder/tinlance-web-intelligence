.PHONY: install lint test typecheck security migration-check shell-check evaluation-check consumer-check evidence-pack readiness-check ga-contract-check check

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
	python scripts/evaluate_twi.py --dataset benchmarks/twi/v1/cases.json --results benchmarks/twi/v1/sample_results.json --thresholds benchmarks/twi/v1/thresholds.json --now 2026-10-19T12:00:00Z --json-out /tmp/twi-evaluation.json --markdown-out /tmp/twi-evaluation.md

consumer-check:
	python scripts/validate_consumer_contracts.py --matrix contracts/consumer-matrix.json

evidence-pack:
	python scripts/build_w15_evidence_pack.py --gates docs/readiness/w15-gates.json --output dist/w15-evidence-pack.json

readiness-check: evidence-pack
	python scripts/validate_w15_evidence_pack.py --pack dist/w15-evidence-pack.json --revision "$$(git rev-parse HEAD)"

ga-contract-check:
	python scripts/validate_ga_v1_contract.py

check: lint typecheck security test migration-check shell-check evaluation-check consumer-check readiness-check ga-contract-check
