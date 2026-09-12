.PHONY: l3-smoke l3-migration-smoke l3-clean l3-preflight l3-preflight-final l3-final-probe l3-verify test reader-api public-api mcp-smoke brief-worker brief-enqueue-public infra-up infra-status infra-down migrate

test:
	python -m pytest -c pytest.ini tests

l3-smoke:
	python scripts/l3_smoke.py

l3-migration-smoke:
	python scripts/l3_migration_smoke.py

l3-clean:
	python scripts/l3_clean.py

l3-preflight:
	python scripts/l3_preflight.py

l3-preflight-final:
	python scripts/l3_preflight.py --final

l3-final-probe:
	python scripts/l3_final_probe.py

l3-verify:
	python scripts/l3_verify.py

reader-api:
	python scripts/run_reader_api.py

public-api:
	python scripts/run_public_api.py

mcp-smoke:
	python scripts/run_mcp_server.py

brief-worker:
	arq jobs.WorkerSettings

brief-enqueue-public:
	python scripts/enqueue_brief.py --type public

infra-up:
	docker compose up -d postgres redis

infra-status:
	docker compose ps postgres redis

infra-down:
	docker compose down

migrate:
	alembic -c db/alembic.ini upgrade head
