$ErrorActionPreference = 'Stop'

# Use this only when upgrading an existing PostgreSQL volume created before
# logiq_dataset was added. It does not delete or recreate any existing data.
$datasetPassword = if ($env:DATASET_DB_PASSWORD) { $env:DATASET_DB_PASSWORD } else { 'logiq-dataset-dev-only' }
$roleExists = (docker compose exec -T postgres psql -U logiq_admin -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='logiq_dataset'").Trim()
if ($roleExists -ne '1') {
    docker compose exec -T postgres psql -U logiq_admin -d postgres -v "dataset_password=$datasetPassword" -c "CREATE ROLE logiq_dataset LOGIN PASSWORD :'dataset_password';"
}

$dbExists = (docker compose exec -T postgres psql -U logiq_admin -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='logiq_dataset'").Trim()
if ($dbExists -ne '1') {
    docker compose exec -T postgres psql -U logiq_admin -d postgres -c "CREATE DATABASE logiq_dataset OWNER logiq_dataset;"
}

Write-Host 'Dataset database and role are provisioned. Existing volumes and data were preserved.'
