# Copyright 2020 Google LLC
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

import datetime
import ibis
import pandas
import pytest
from ibis.backends.impala.compiler import ImpalaCompiler
from ibis.backends.postgres.compiler import PostgreSQLCompiler

from data_validation.query_builder.query_builder import CalculatedField
from third_party.ibis.ibis_addon import operations
from third_party.ibis.ibis_oracle.compiler import OracleCompiler

TABLE_DF = pandas.DataFrame([{"column": "value"}])
CLIENT = ibis.pandas.connect({"table": TABLE_DF})
WHERE_FILTER = "id > 100"
COMPILER_TABLE = ibis.table({"b": "binary", "n": "int64"}, name="t")

SECONDS_IN_A_DAY = 60 * 60 * 24

INT64_MIN = int("-9223372036854775808")


@pytest.fixture
def module_under_test():
    from third_party.ibis.ibis_addon import operations

    return operations


def test_import(module_under_test):
    assert module_under_test is not None


def _compile_sql(compiler_class, expr):
    return str(compiler_class().to_sql(expr))


def test_format_raw_sql_expr(module_under_test):
    ibis_table = CLIENT.table("table")

    filters = [operations.compile_raw_sql(ibis_table, WHERE_FILTER)]
    query = ibis_table.filter(filters)

    # Recurse to the boolean filter column expression
    raw_sql_column_expr = query.op().to_expr().op().predicates[0]
    raw_sql = operations.format_raw_sql(ibis_table.column, raw_sql_column_expr)

    assert raw_sql == WHERE_FILTER


@pytest.mark.parametrize("compiler_class", [PostgreSQLCompiler, OracleCompiler])
def test_to_char_accepts_plain_format_string(compiler_class):
    expr = COMPILER_TABLE.n.to_char("FM90.099").name("fmt")
    sql = _compile_sql(compiler_class, expr)

    assert "to_char(t0.n, 'FM90.099')" in sql


def test_calculated_field_to_char_passes_plain_format_string():
    calc_field = CalculatedField.to_char(
        {"field_alias": "fmt", "default_to_char_fmt": "FM999"}, ["n"]
    )
    expr = calc_field.compile(COMPILER_TABLE)
    sql = _compile_sql(PostgreSQLCompiler, expr)

    assert "to_char(t0.n, 'FM999')" in sql


def test_impala_binary_length_references_column():
    expr = COMPILER_TABLE.b.byte_length().name("len")
    sql = _compile_sql(ImpalaCompiler, expr)

    assert "length(t0.`b`)" in sql
    assert ":length" not in sql


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            "1970-01-01",
            0,
        ),
        (
            "1970-01-01 00:00:01",
            1,
        ),
        (
            "1970-01-02",
            SECONDS_IN_A_DAY,
        ),
        (
            "1970-02-01 00:00:01",
            (SECONDS_IN_A_DAY * 31) + 1,
        ),
        (
            "1969-12-31",
            -SECONDS_IN_A_DAY,
        ),
        (
            "1969-12-31 23:59:00",
            -60,
        ),
    ],
)
def test_string_to_epoch(module_under_test, test_input: str, expected: int):
    result = module_under_test.string_to_epoch(test_input)
    assert result == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        # Simple input.
        (
            pandas.Series(
                [
                    pandas.to_datetime("1970-01-01 00:00:10"),
                ]
            ),
            pandas.Series(
                [
                    10,
                ]
            ),
        ),
        (
            pandas.Series(
                [
                    pandas.to_datetime("1969-12-31 23:59:50"),
                ]
            ),
            pandas.Series(
                [
                    -10,
                ]
            ),
        ),
        # With NaT.
        (
            pandas.Series(
                [
                    pandas.to_datetime("1970-01-01 00:00:10"),
                    pandas.to_datetime(None),
                ]
            ),
            pandas.Series(
                [
                    10,
                    INT64_MIN // 1_000_000_000,
                ]
            ),
        ),
        # With datetime which is what happens when datetime64[ns] overflows.
        (
            pandas.Series(
                [
                    pandas.to_datetime("1970-01-01 00:00:10"),
                    datetime.date(1000, 1, 1),
                ]
            ),
            pandas.Series(
                [
                    10,
                    -30610224000,
                ]
            ),
        ),
        # With datetime and NaT.
        (
            pandas.Series(
                [
                    datetime.date(1000, 1, 1),
                    pandas.to_datetime(None),
                ]
            ),
            pandas.Series(
                [
                    -30610224000,
                    INT64_MIN // 1_000_000_000,
                ]
            ),
        ),
    ],
)
def test_execute_epoch_seconds_new(
    module_under_test, test_input: pandas.Series, expected: pandas.Series
):
    result = module_under_test.execute_epoch_seconds_new(None, test_input)
    assert list(result) == list(expected)
