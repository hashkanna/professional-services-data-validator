# Ibis 7.1 Migration Validation

This note records the review stack and the local validation gates used for the
Ibis 7.1 migration.

## Branch Stack

Each branch is stacked on the branch above it in this list.

| Branch | Purpose |
| --- | --- |
| `kanna/ibis-7-1-core` | Bump to `ibis-framework==7.1.0` and patch core compatibility imports. |
| `kanna/ibis-7-1-bigquery-addon-tests` | Update BigQuery addon operation expectations for Ibis 7 SQL output. |
| `kanna/ibis-7-1-bigquery-project-dataset` | Split BigQuery project and dataset handling for Ibis 7 table lookup. |
| `kanna/ibis-7-1-compiler-hardening` | Harden custom compiler operations across supported SQL backends. |
| `kanna/ibis-7-1-compiler-matrix` | Add compile-only matrix coverage and integration preflight reporting. |
| `kanna/ibis-7-1-bigquery-gcs` | Fix BigQuery temporal compilation and validate live BigQuery/GCS paths. |
| `kanna/ibis-7-1-filesystem-fixtures` | Parameterize filesystem GCS fixtures with `TEST_BUCKET` or `PROJECT_ID`. |
| `kanna/ibis-7-1-snowflake` | Add targeted integration preflight filtering for Snowflake validation. |
| `kanna/ibis-7-1-docker-dbs` | Validate focused MySQL/Postgres Docker-backed system tests. |
| `kanna/ibis-7-1-docs-and-pr-notes` | Document validation commands, evidence, and remaining backend scope. |
| `kanna/ibis-7-1-snowflake-live-validation` | Validate live Snowflake fixtures and patch Ibis 7 Snowflake reflection. |
| `kanna/ibis-7-1-additional-backend-validation` | Validate Cloud Spanner, Cloud SQL SQL Server, and Hive/Dataproc live paths. |
| `kanna/ibis-7-1-hive-partition-validation` | Validate Hive partition generation on a multi-node Dataproc cluster. |

## Local Environment

Create and install the local environment:

```bash
python3 -m venv venv
venv/bin/python -m pip install --upgrade pip
venv/bin/python -m pip install .
```

Optional Snowflake validation requires:

```bash
venv/bin/python -m pip install snowflake-sqlalchemy snowflake-connector-python
```

Optional Hive validation requires:

```bash
venv/bin/python -m pip install PyHive hdfs
```

Optional local SQL Server validation requires `pyodbc` plus an ODBC driver. The
local validation run used Homebrew `unixodbc` and `freetds`, with FreeTDS
registered as `ODBC Driver 17 for SQL Server`.

## Core Gates

Run unit tests:

```bash
TZ=UTC venv/bin/python -m pytest tests/unit -q
```

Run formatting checks:

```bash
black --check \
  data_validation \
  third_party/ibis \
  tests/unit/ibis_addon \
  tests/system/data_sources \
  ci/integration_preflight.py
git diff --check
```

Run integration preflight:

```bash
PROJECT_ID=tpu-research-cloud-490704 \
TEST_BUCKET=tpu-research-cloud-490704 \
TZ=UTC \
venv/bin/python ci/integration_preflight.py
```

To inspect one integration target:

```bash
PROJECT_ID=tpu-research-cloud-490704 \
venv/bin/python ci/integration_preflight.py --session integration_snowflake
```

## BigQuery And GCS

Expected environment:

```bash
export PROJECT_ID=tpu-research-cloud-490704
export TEST_BUCKET=tpu-research-cloud-490704
```

Seed the BigQuery fixture dataset when needed:

```bash
bq --project_id="$PROJECT_ID" mk --dataset --location=US "$PROJECT_ID:pso_data_validator"
bq --project_id="$PROJECT_ID" query --use_legacy_sql=false < tests/resources/bigquery_test_tables.sql
```

Run the focused BigQuery/GCS validation gate:

```bash
PROJECT_ID="$PROJECT_ID" TEST_BUCKET="$TEST_BUCKET" TZ=UTC \
venv/bin/python -m pytest tests/system/data_sources/test_bigquery.py -q \
  -k 'count_validator or grouped_count_validator or timestamp_aggs or cli_store_yaml_then_run_gcs or cli_store_yaml_then_run_directory_gcs or generate_partitions or bigquery_dry_run or schema_validation_core_types or schema_validation_bool or column_validation_core_types or row_validation_core_types or custom_query_validation_core_types or row_validation_many_columns or custom_query_row_validation_many_columns or schema_validation_reserved_words or column_validation_reserved_words or row_validation_reserved_words or row_validation_comp_fields_reserved_words or generate_and_run_partitions or bq_result_handler or raw_query_dvt_row_types'
```

Run the GCS state manager gate:

```bash
PROJECT_ID="$PROJECT_ID" TZ=UTC \
venv/bin/python -m pytest tests/system/test_state_manager.py -q
```

## Filesystem GCS Fixtures

The filesystem tests use `TEST_BUCKET` or `PROJECT_ID` for this path:

```text
gs://$TEST_BUCKET/file_connection/
```

The fixture files are:

```text
file_connection/csv/entries.csv
file_connection/json/entries.json
file_connection/orc/entries.orc
file_connection/parquet/entries.parquet
```

Run:

```bash
PROJECT_ID="$PROJECT_ID" TEST_BUCKET="$TEST_BUCKET" TZ=UTC \
venv/bin/python -m pytest tests/system/data_sources/test_filesystem.py -q
```

## Docker MySQL And Postgres

Start local containers:

```bash
docker run -d --name dvt-ibis71-postgres \
  -e POSTGRES_PASSWORD=dvtpass \
  -e POSTGRES_DB=guestbook \
  -p 55432:5432 \
  postgres:15

docker run -d --name dvt-ibis71-mysql \
  -e MYSQL_ROOT_PASSWORD=rootpass \
  -e MYSQL_DATABASE=pso_data_validator \
  -e MYSQL_USER=dvt \
  -e MYSQL_PASSWORD=dvtpass \
  -p 33306:3306 \
  mysql:8.0
```

Load fixtures:

```bash
docker cp tests/resources/postgresql_test_tables.sql dvt-ibis71-postgres:/tmp/postgresql_test_tables.sql
docker exec dvt-ibis71-postgres \
  psql -U postgres -d guestbook -f /tmp/postgresql_test_tables.sql

docker exec -i dvt-ibis71-mysql \
  mysql -f -uroot -prootpass < tests/resources/mysql_test_tables.sql
```

Run focused Docker-backed validation:

```bash
PROJECT_ID="$PROJECT_ID" \
POSTGRES_HOST=localhost \
POSTGRES_PORT=55432 \
POSTGRES_PASSWORD=dvtpass \
POSTGRES_DATABASE=guestbook \
TZ=UTC \
venv/bin/python -m pytest tests/system/data_sources/test_postgres.py -q --no-cloud-sql \
  -k 'postgres_count or schema_validation_pg_types or column_validation_pg_types or row_validation_pg_types or generate_partitions'

PROJECT_ID="$PROJECT_ID" \
MYSQL_HOST=localhost \
MYSQL_PORT=33306 \
MYSQL_USER=dvt \
MYSQL_PASSWORD=dvtpass \
TZ=UTC \
venv/bin/python -m pytest tests/system/data_sources/test_mysql.py -q \
  -k 'mysql_count_invalid_host or mysql_dry_run or schema_validation_core_types or column_validation_core_types or row_validation_core_types or generate_partitions'
```

Remove local containers:

```bash
docker rm -f dvt-ibis71-postgres dvt-ibis71-mysql
```

## Snowflake

The Snowflake tests require:

```bash
export PROJECT_ID=tpu-research-cloud-490704
export SNOWFLAKE_ACCOUNT=...
export SNOWFLAKE_USER=...
export SNOWFLAKE_PASSWORD=...
export SNOWFLAKE_DATABASE=pso_data_validator/public
```

Run preflight:

```bash
PROJECT_ID="$PROJECT_ID" \
SNOWFLAKE_ACCOUNT="$SNOWFLAKE_ACCOUNT" \
SNOWFLAKE_USER="$SNOWFLAKE_USER" \
SNOWFLAKE_PASSWORD="$SNOWFLAKE_PASSWORD" \
venv/bin/python ci/integration_preflight.py --session integration_snowflake
```

Run a focused Snowflake subset:

```bash
PROJECT_ID="$PROJECT_ID" \
SNOWFLAKE_ACCOUNT="$SNOWFLAKE_ACCOUNT" \
SNOWFLAKE_USER="$SNOWFLAKE_USER" \
SNOWFLAKE_PASSWORD="$SNOWFLAKE_PASSWORD" \
SNOWFLAKE_DATABASE="${SNOWFLAKE_DATABASE:-pso_data_validator/public}" \
TZ=UTC \
venv/bin/python -m pytest tests/system/data_sources/test_snowflake.py -q \
  -k 'count_validator or schema_validation_core_types or column_validation_core_types or row_validation_core_types'
```

## Cloud Spanner

Run a focused Cloud Spanner subset after creating a Spanner instance/database
from `third_party/ibis/ibis_cloud_spanner/tests/ddl.sql` and loading
`third_party/ibis/ibis_cloud_spanner/tests/dml.sql`:

```bash
PROJECT_ID="$PROJECT_ID" \
SPANNER_INSTANCE="$SPANNER_INSTANCE" \
SPANNER_DATABASE="${SPANNER_DATABASE:-pso_data_validator}" \
TZ=UTC \
venv/bin/python -m pytest tests/system/data_sources/test_spanner.py -q \
  -k 'count_validator or grouped_count_validator or schema_validation_core_types or column_validation_core_types or row_validation_core_types or row_validation_binary_pk_to_bigquery or row_validation_comp_fields_binary_values_to_bigquery or custom_query_validation_core_types or raw_query_dvt_row_types'
```

## Cloud SQL SQL Server

Run a focused SQL Server subset after loading
`tests/resources/sqlserver_test_tables.sql` and
`tests/system/data_sources/deploy_cloudsql/mssql_data.sql`:

```bash
PROJECT_ID="$PROJECT_ID" \
SQL_SERVER_HOST="$SQL_SERVER_HOST" \
SQL_SERVER_PORT="${SQL_SERVER_PORT:-1433}" \
SQL_SERVER_USER="${SQL_SERVER_USER:-sqlserver}" \
SQL_SERVER_PASSWORD="$SQL_SERVER_PASSWORD" \
SQL_SERVER_DATABASE="${SQL_SERVER_DATABASE:-guestbook}" \
TZ=UTC \
venv/bin/python -m pytest tests/system/data_sources/test_sql_server.py -q --no-cloud-sql \
  -k 'sql_server_count or sql_server_row or schema_validation_core_types or column_validation_core_types or row_validation_core_types or generate_partitions'
```

## Hive

The live Hive validation used temporary Dataproc clusters and an IAP SSH tunnel
from `localhost:10000` to HiveServer2 on the Dataproc master. The fixture was
loaded from `tests/resources/hive_test_tables.sql`.

Run a focused Hive subset:

```bash
PROJECT_ID="$PROJECT_ID" \
HIVE_HOST=127.0.0.1 \
HIVE_DATABASE=default \
TZ=UTC \
venv/bin/python -m pytest \
  tests/system/data_sources/test_hive.py::test_count_validator \
  tests/system/data_sources/test_hive.py::test_schema_validation_bool \
  tests/system/data_sources/test_hive.py::test_schema_validation_core_types_to_bigquery \
  tests/system/data_sources/test_hive.py::test_raw_query_dvt_row_types \
  tests/system/data_sources/test_hive.py::test_row_validation_hash_bool_to_bigquery \
  -q --tb=short
```

Run the Hive partition generation check on a multi-node Dataproc cluster. The
single-node cluster did not complete this check in a reasonable window.

```bash
PROJECT_ID="$PROJECT_ID" \
HIVE_HOST=127.0.0.1 \
HIVE_DATABASE=pso_data_validator \
TZ=UTC \
venv/bin/python -m pytest tests/system/data_sources/test_hive.py::test_generate_partitions \
  -vv -s --tb=short --timeout=600
```

## Current Evidence

The following gates were run locally on the stack:

| Gate | Result |
| --- | --- |
| Unit suite | `411 passed, 10 skipped` |
| BigQuery/GCS focused system subset | `22 passed, 20 deselected` |
| GCS state manager | `6 passed` |
| Filesystem GCS system tests | `8 passed` |
| Docker MySQL focused subset | `10 passed, 1 skipped` |
| Docker Postgres focused subset | `5 passed, 1 skipped` |
| Snowflake preflight with PAT auth | `READY integration_snowflake` |
| Snowflake fixture seed | `DVT_CORE_TYPES` seeded with 3 rows; 14 tables present in `PSO_DATA_VALIDATOR.PUBLIC` |
| Snowflake focused system subset | `8 passed, 27 deselected` |
| Cloud Spanner fixture seed | 18 DML statements executed; `dvt_core_types` seeded with 3 rows |
| Cloud Spanner focused system subset | `11 passed, 5 deselected` |
| Cloud SQL SQL Server fixture seed | `dvt_core_types` seeded with 3 rows; `entries` seeded with 7 rows |
| Cloud SQL SQL Server focused system subset | `12 passed, 1 skipped, 36 deselected` |
| Hive/Dataproc fixture seed | `dvt_core_types` seeded with 3 rows; `test_generate_partitions_v2` seeded with 32 rows |
| Hive/Dataproc focused system subset | `5 passed` |
| Hive/Dataproc partition generation on 3-node cluster | `1 passed` in `427.98s` |
| Temporary GCP resources | Cloud Spanner instance, Cloud SQL SQL Server instance, Dataproc cluster, and Dataproc staging bucket deleted after validation |

## Remaining Live Backend Scope

The migration has unit, compile-only, BigQuery/GCS, filesystem/GCS, MySQL,
Postgres, Snowflake, Cloud Spanner, SQL Server, and focused Hive coverage.
Additional end-to-end backend validation still depends on available credentials
or specialized infrastructure for Oracle, Teradata, DB2, Impala, Sybase, and
Redshift.
