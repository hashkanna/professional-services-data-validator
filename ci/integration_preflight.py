# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Report which integration test sessions are runnable in the local environment."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class SessionCheck:
    nox_session: str
    env_vars: tuple[str, ...]
    modules: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


SESSION_CHECKS = (
    SessionCheck(
        "integration_bigquery",
        ("PROJECT_ID",),
        ("google.cloud.bigquery",),
        ("Requires BigQuery access to the configured project and public datasets.",),
    ),
    SessionCheck(
        "integration_filesystem",
        ("PROJECT_ID", "TEST_BUCKET"),
        ("gcsfs",),
        ("Requires storage object access to the configured GCS test bucket.",),
    ),
    SessionCheck(
        "integration_spanner",
        ("PROJECT_ID",),
        ("google.cloud.spanner",),
        (
            "Defaults to SPANNER_INSTANCE=span1 and SPANNER_DATABASE=pso_data_validator.",
        ),
    ),
    SessionCheck(
        "integration_postgres",
        ("PROJECT_ID", "POSTGRES_PASSWORD", "CLOUD_SQL_CONNECTION"),
        ("psycopg2",),
        ("Requires Cloud SQL proxy or equivalent local listener.",),
    ),
    SessionCheck(
        "integration_mysql",
        ("PROJECT_ID", "MYSQL_PASSWORD", "CLOUD_SQL_CONNECTION"),
        ("pymysql",),
        ("Requires Cloud SQL proxy or equivalent local listener.",),
    ),
    SessionCheck(
        "integration_sql_server",
        ("PROJECT_ID", "SQL_SERVER_PASSWORD", "CLOUD_SQL_CONNECTION"),
        ("pyodbc",),
        ("Requires ODBC driver setup plus Cloud SQL proxy or equivalent listener.",),
    ),
    SessionCheck(
        "integration_oracle",
        (
            "PROJECT_ID",
            "ORACLE_PASSWORD",
            "ORACLE_HOST",
            "POSTGRES_PASSWORD",
            "CLOUD_SQL_CONNECTION",
        ),
        ("oracledb",),
        ("Oracle tests also use Postgres/Cloud SQL for cross-backend coverage.",),
    ),
    SessionCheck(
        "integration_snowflake",
        ("PROJECT_ID", "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"),
        ("snowflake.sqlalchemy", "snowflake.connector"),
    ),
    SessionCheck(
        "integration_db2",
        ("PROJECT_ID", "DB2_HOST", "DB2_PASSWORD"),
        ("ibm_db_sa", "ibm_db"),
    ),
    SessionCheck(
        "integration_teradata",
        ("PROJECT_ID", "TERADATA_PASSWORD", "TERADATA_HOST"),
        ("teradatasql",),
    ),
    SessionCheck(
        "integration_hive",
        ("PROJECT_ID", "HIVE_HOST"),
        ("pyhive", "hdfs"),
    ),
    SessionCheck(
        "integration_impala",
        ("PROJECT_ID", "IMPALA_HOST"),
        ("impala",),
    ),
    SessionCheck(
        "integration_sybase",
        ("PROJECT_ID", "SYBASE_HOST", "SYBASE_USER", "SYBASE_PASSWORD"),
        ("pyodbc", "sqlalchemy_sybase"),
    ),
    SessionCheck(
        "integration_state",
        ("PROJECT_ID",),
        (),
        ("Requires GCS access to gs://$PROJECT_ID/state/connections/.",),
    ),
    SessionCheck(
        "integration_secrets",
        ("PROJECT_ID",),
        (),
        ("Requires Secret Manager access in the configured project.",),
    ),
)


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


def _gcloud_value(args: list[str]) -> str | None:
    if not shutil.which("gcloud"):
        return None
    try:
        result = subprocess.run(
            ["gcloud", *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _check_session(check: SessionCheck) -> dict:
    missing_env = [name for name in check.env_vars if not os.environ.get(name)]
    missing_modules = [name for name in check.modules if not _module_available(name)]
    return {
        "nox_session": check.nox_session,
        "ready": not missing_env and not missing_modules,
        "missing_env": missing_env,
        "missing_modules": missing_modules,
        "notes": list(check.notes),
    }


def build_report() -> dict:
    return {
        "gcloud": {
            "account": _gcloud_value(
                ["auth", "list", "--filter=status:ACTIVE", "--format=value(account)"]
            ),
            "project": _gcloud_value(["config", "get-value", "project"]),
        },
        "sessions": [_check_session(check) for check in SESSION_CHECKS],
    }


def print_text_report(report: dict) -> None:
    account = report["gcloud"]["account"] or "unavailable"
    project = report["gcloud"]["project"] or "unavailable"
    print(f"gcloud account: {account}")
    print(f"gcloud project: {project}")
    print()

    for session in report["sessions"]:
        status = "READY" if session["ready"] else "BLOCKED"
        print(f"{status:7} {session['nox_session']}")
        if session["missing_env"]:
            print(f"        missing env: {', '.join(session['missing_env'])}")
        if session["missing_modules"]:
            print(f"        missing modules: {', '.join(session['missing_modules'])}")
        for note in session["notes"]:
            print(f"        note: {note}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text_report(report)


if __name__ == "__main__":
    main()
