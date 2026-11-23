#!/bin/sh
set -eu
# Local-development bootstrap. Replace these credentials before any shared deployment.
: "${DATASET_DB_PASSWORD:=logiq-dataset-dev-only}"
psql --username "$POSTGRES_USER" --dbname postgres --set=dataset_password="$DATASET_DB_PASSWORD" <<'SQL'
CREATE ROLE logiq_core LOGIN PASSWORD 'logiq-core-dev-only';
CREATE ROLE logiq_identity LOGIN PASSWORD 'logiq-identity-dev-only';
CREATE ROLE logiq_dataset LOGIN PASSWORD :'dataset_password';
CREATE DATABASE logiq_core OWNER logiq_core;
CREATE DATABASE logiq_identity OWNER logiq_identity;
CREATE DATABASE logiq_dataset OWNER logiq_dataset;
SQL
