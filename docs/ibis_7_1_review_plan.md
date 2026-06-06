# Ibis 7.1 Review Plan

This plan packages the Ibis 7.1 migration stack for review without touching the
upstream repository.

## Fork-Only PR Strategy

Use PRs inside `hashkanna/professional-services-data-validator` first. Do not
open PRs against `GoogleCloudPlatform/professional-services-data-validator`
until the stack has been reviewed and explicitly approved for upstream.

The fork's `develop` branch should be updated or replaced before opening the
first PR because it is not currently the same commit as `upstream/develop`.
The safest approach is:

1. Create a fork base branch at `upstream/develop`, for example
   `kanna/ibis-7-1-review-base`.
2. Open the first fork-only PR from `kanna/ibis-7-1-core` into
   `kanna/ibis-7-1-review-base`.
3. Open each later PR against the previous branch in the stack.
4. Keep every PR in the fork until the team is ready to retarget or recreate
   the reviewed stack upstream.

## Stack

| Order | Branch | Suggested PR title | Base branch |
| --- | --- | --- | --- |
| 1 | `kanna/ibis-7-1-core` | Migrate compatibility layer to Ibis 7.1 | `kanna/ibis-7-1-review-base` |
| 2 | `kanna/ibis-7-1-bigquery-addon-tests` | Update BigQuery addon expectations for Ibis 7.1 | `kanna/ibis-7-1-core` |
| 3 | `kanna/ibis-7-1-bigquery-project-dataset` | Split BigQuery project and dataset table lookup | `kanna/ibis-7-1-bigquery-addon-tests` |
| 4 | `kanna/ibis-7-1-compiler-hardening` | Harden custom compiler operations for Ibis 7.1 | `kanna/ibis-7-1-bigquery-project-dataset` |
| 5 | `kanna/ibis-7-1-compiler-matrix` | Add Ibis 7.1 compiler matrix and integration preflight | `kanna/ibis-7-1-compiler-hardening` |
| 6 | `kanna/ibis-7-1-bigquery-gcs` | Validate BigQuery and GCS paths on Ibis 7.1 | `kanna/ibis-7-1-compiler-matrix` |
| 7 | `kanna/ibis-7-1-filesystem-fixtures` | Parameterize filesystem GCS fixtures | `kanna/ibis-7-1-bigquery-gcs` |
| 8 | `kanna/ibis-7-1-snowflake` | Add targeted Snowflake integration preflight | `kanna/ibis-7-1-filesystem-fixtures` |
| 9 | `kanna/ibis-7-1-docker-dbs` | Validate MySQL and Postgres fixtures on Ibis 7.1 | `kanna/ibis-7-1-snowflake` |
| 10 | `kanna/ibis-7-1-docs-and-pr-notes` | Document Ibis 7.1 validation evidence | `kanna/ibis-7-1-docker-dbs` |
| 11 | `kanna/ibis-7-1-snowflake-live-validation` | Validate live Snowflake path on Ibis 7.1 | `kanna/ibis-7-1-docs-and-pr-notes` |
| 12 | `kanna/ibis-7-1-additional-backend-validation` | Validate Spanner, SQL Server, and Hive paths | `kanna/ibis-7-1-snowflake-live-validation` |
| 13 | `kanna/ibis-7-1-hive-partition-validation` | Validate Hive partition generation on Dataproc | `kanna/ibis-7-1-additional-backend-validation` |

## Review Notes

Keep the first review pass focused on code migration and validated behavior:

- Ibis 7.1 dependency and compatibility updates.
- Custom compiler behavior for BigQuery, Snowflake, SQL Server, Spanner, Hive,
  MySQL, and Postgres paths.
- Table/schema lookup changes that remove Ibis 6 assumptions.
- Integration preflight and focused live backend evidence.

Avoid expanding review scope into a full backend certification effort. Remaining
enterprise backend validation still depends on separate infrastructure for
Oracle, Teradata, DB2, Impala, Sybase, and Redshift.

## Validation Summary

Detailed commands and evidence are recorded in
`docs/ibis_7_1_migration_validation.md`. The high-signal completed coverage is:

| Area | Evidence |
| --- | --- |
| Unit suite | `411 passed, 10 skipped` |
| BigQuery/GCS | Focused system subset and GCS state manager passed |
| Filesystem GCS | System tests passed |
| MySQL/Postgres | Focused Docker-backed subsets passed |
| Snowflake | Preflight, fixture seed, and focused live subset passed |
| Cloud Spanner | Fixture seed and focused live subset passed |
| SQL Server | Cloud SQL fixture seed and focused live subset passed |
| Hive | Focused subset and multi-node partition generation passed |

## Suggested PR Body Template

```text
## Summary
- ...

## Validation
- ...

## Notes
- This PR is part of the Ibis 7.1 migration stack.
- This PR is opened against the fork for review only; upstream is untouched.
```
