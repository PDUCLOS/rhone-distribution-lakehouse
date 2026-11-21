# Snowflake credentials, read by the Makefile (never commit .env)
-include .env
export

PY ?= .venv/bin/python
DBT ?= .venv/bin/dbt
TARGET ?= dev
DBT_ARGS = --profiles-dir . --target $(TARGET)
DATE ?= $(shell date -v-1d +%Y-%m-%d 2>/dev/null || date -d yesterday +%Y-%m-%d)

.PHONY: pg-start pg-stop setup generate postgres extract-backfill extract-day bronze dev snowflake-push snowflake-build docs

setup:             ## venv + dependencies
	uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
	test -f profiles.yml || cp profiles.example.yml profiles.yml

generate:          ## Simulate the ERP (Parquet + anomaly manifest). SCALE=10 for 10x
	$(PY) generator/generate_erp.py --scale $(or $(SCALE),1)
	cp data/generated/anomaly_manifest.csv seeds/anomaly_manifest.csv

postgres:          ## Load the ERP into PostgreSQL (database rhone_erp)
	createdb rhone_erp 2>/dev/null || true
	$(PY) generator/load_postgres.py

extract-backfill:  ## Nightly-extract format, whole history in one batch
	$(PY) generator/extract_daily.py --backfill

extract-day:       ## One nightly batch: make extract-day DATE=2026-10-29
	$(PY) generator/extract_daily.py --date $(DATE)

bronze:            ## Local stand-in for COPY INTO: landing -> DuckDB bronze
	$(PY) generator/load_bronze_duckdb.py

dev: bronze        ## Full local build: bronze -> silver -> gold + all tests
	$(DBT) build $(DBT_ARGS)

snowflake-push:    ## Upload batches to the stage and COPY into bronze
	$(PY) generator/push_to_snowflake.py

snowflake-build:   ## dbt on Snowflake (policies attached by post-hooks)
	$(DBT) build --profiles-dir . --target snowflake

docs:              ## Static docs site with the lineage graph
	$(DBT) docs generate --static $(DBT_ARGS)

pg-start:          ## Start the local PostgreSQL (this Mac needs an explicit locale)

	LC_ALL=fr_FR.UTF-8 LANG=fr_FR.UTF-8 pg_ctl -D /opt/homebrew/var/postgresql@16 -l logs/postgres.log start



pg-stop:           ## Stop it

	pg_ctl -D /opt/homebrew/var/postgresql@16 stop
