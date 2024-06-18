import pytest
from pyspark.sql.functions import col
from testframework.dataquality.dataframe import DataFrameTester
from testframework.dataquality.tests import ValidNumericRange


@pytest.fixture(scope="module")
def sample_df(spark):
    data = [(1, "Alice", 10), (2, "Bob", 20), (3, "Cathy", 30), (4, "David", 40)]
    columns = ["id", "name", "value"]
    return spark.createDataFrame(data, columns)


@pytest.fixture(scope="module")
def duplicate_key_df(spark):
    data = [(1, "Alice", 10), (1, "Bob", 20), (3, "Cathy", 30), (4, "David", 40)]
    columns = ["id", "name", "value"]
    return spark.createDataFrame(data, columns)


def test_init(sample_df, spark):
    tester = DataFrameTester(df=sample_df, primary_key="id", spark=spark)
    assert tester.df.count() == 4
    assert tester.primary_key == ["id"]


def test_unique_columns(sample_df, spark):
    unique_df = DataFrameTester.unique_columns(sample_df)
    assert set(unique_df.columns) == {"id", "name", "value"}


def test_check_primary_key(sample_df, spark):
    tester = DataFrameTester(df=sample_df, primary_key="id", spark=spark)
    assert tester.df.count() == 4


def test_check_primary_key_error(duplicate_key_df, spark):
    with pytest.raises(ValueError):
        DataFrameTester(df=duplicate_key_df, primary_key="id", spark=spark)


def test_assert_primary_key_unique(sample_df):
    DataFrameTester.assert_primary_key_unique(sample_df, "id")


def test_assert_primary_key_unique_error(duplicate_key_df):
    with pytest.raises(ValueError):
        DataFrameTester.assert_primary_key_unique(duplicate_key_df, "id")


def test_get_primary_keys(sample_df):
    primary_keys = DataFrameTester.potential_primary_keys(sample_df)
    assert primary_keys == ["id", "name", "value"]


def test_test_method(sample_df, spark):
    tester = DataFrameTester(df=sample_df, primary_key="id", spark=spark)
    valid_numeric_range = ValidNumericRange(min_value=30)
    result_df = tester.test(col="value", test=valid_numeric_range, nullable=True)
    assert "value__ValidNumericRange" in result_df.columns
    assert result_df.filter(result_df["value__ValidNumericRange"]).count() == 2


def test_test_method_with_filter(sample_df, spark):
    tester = DataFrameTester(df=sample_df, primary_key="id", spark=spark)
    valid_numeric_range = ValidNumericRange(min_value=30)
    result_df = tester.test(
        col="value",
        test=valid_numeric_range,
        nullable=True,
        filter_rows=col("value") > 10,
    )
    assert "value__ValidNumericRange" in result_df.columns
    assert result_df.filter(result_df["value__ValidNumericRange"]).count() == 2
    assert result_df.count() == 3


def test_test_method_with_return_extra_cols(sample_df, spark):
    tester = DataFrameTester(df=sample_df, primary_key="id", spark=spark)
    valid_numeric_range = ValidNumericRange(min_value=30)
    result_df = tester.test(
        col="value", test=valid_numeric_range, nullable=True, return_extra_cols=["name"]
    )
    assert "value__ValidNumericRange" in result_df.columns
    assert "name" in result_df.columns
    assert result_df.filter(result_df["value__ValidNumericRange"]).count() == 2
    assert result_df.filter(result_df["name"].isNotNull()).count() == 4


def test_test_method_with_dummy_run(sample_df, spark):
    tester = DataFrameTester(df=sample_df, primary_key="id", spark=spark)
    valid_numeric_range = ValidNumericRange(min_value=30)
    result_df = tester.test(
        col="value", test=valid_numeric_range, nullable=True, dummy_run=True
    )
    assert "value__ValidNumericRange" in result_df.columns
    assert result_df.filter(result_df["value__ValidNumericRange"]).count() == 2
    assert "value__ValidNumericRange" not in tester.results.columns


def test_description_df(sample_df, spark):
    tester = DataFrameTester(df=sample_df, primary_key="id", spark=spark)
    tester.descriptions = {
        "test1": "Description of test 1",
        "test2": "Description of test 2",
    }
    description_df = tester.description_df
    assert set(description_df.columns) == {"test", "description"}
    assert description_df.count() == 2
    descriptions = {row["test"]: row["description"] for row in description_df.collect()}
    assert descriptions == {
        "test1": "Description of test 1",
        "test2": "Description of test 2",
    }


def test_add_custom_test_result(sample_df, spark):
    tester = DataFrameTester(df=sample_df, primary_key="id", spark=spark)
    custom_test_data = [(1, True), (2, False), (3, True), (4, False)]
    custom_test_columns = ["id", "custom_test"]
    custom_test_result = spark.createDataFrame(custom_test_data, custom_test_columns)

    updated_results = tester.add_custom_test_result(
        result=custom_test_result,
        name="custom_test",
        description="This is a custom test",
        fillna_value=False,
    )

    assert "custom_test" in updated_results.columns
    assert tester.descriptions["custom_test"] == "This is a custom test"
    assert updated_results.filter(col("custom_test")).count() == 2
    assert updated_results.filter(~col("custom_test")).count() == 2


def test_add_custom_test_result_return_extra_cols(sample_df, spark):
    tester = DataFrameTester(df=sample_df, primary_key="id", spark=spark)
    custom_test_data = [(1, True), (2, False), (3, True), (4, False)]
    custom_test_columns = ["id", "custom_test"]
    custom_test_result = spark.createDataFrame(custom_test_data, custom_test_columns)

    updated_results = tester.add_custom_test_result(
        result=custom_test_result,
        name="custom_test",
        description="This is a custom test",
        return_extra_cols=["name"],
    )

    assert "custom_test" in updated_results.columns
    assert "name" in updated_results.columns
    assert updated_results.filter(col("custom_test")).count() == 2
    assert updated_results.filter(updated_results["name"].isNotNull()).count() == 4


def test_add_custom_test_result_duplicate_primary_key(sample_df, spark):
    tester = DataFrameTester(df=sample_df, primary_key="id", spark=spark)
    invalid_test_data = [(1, True), (2, False), (1, True), (4, False)]
    invalid_test_columns = ["id", "invalid_test"]
    invalid_test_result = spark.createDataFrame(invalid_test_data, invalid_test_columns)

    with pytest.raises(
        ValueError, match="primary_key .* is not unique in test_result DataFrame"
    ):
        tester.add_custom_test_result(result=invalid_test_result, name="invalid_test")


def test_add_custom_test_result_invalid_result_type(sample_df, spark):
    tester = DataFrameTester(df=sample_df, primary_key="id", spark=spark)
    with pytest.raises(TypeError, match="test_result should be a pyspark DataFrame"):
        tester.add_custom_test_result(result=[(1, True)], name="custom_test")


def test_add_custom_test_result_primary_key_not_found(sample_df, spark):
    tester = DataFrameTester(df=sample_df, primary_key="id", spark=spark)
    invalid_test_result = spark.createDataFrame(
        [(1, True)], ["wrong_key", "custom_test"]
    )

    with pytest.raises(ValueError, match="primary_key 'id' not found in DataFrame"):
        tester.add_custom_test_result(result=invalid_test_result, name="custom_test")


def test_add_custom_test_result_column_not_found(sample_df, spark):
    tester = DataFrameTester(df=sample_df, primary_key="id", spark=spark)
    invalid_test_data = [(1, True), (2, False), (3, True), (4, False)]
    invalid_test_columns = ["id", "custom_test"]
    invalid_test_result = spark.createDataFrame(invalid_test_data, invalid_test_columns)

    with pytest.raises(
        ValueError,
        match="A column with test_name 'missing_test' not found in test_result DataFrame",
    ):
        tester.add_custom_test_result(result=invalid_test_result, name="missing_test")


def test_add_custom_test_result_invalid_description_type(sample_df, spark):
    tester = DataFrameTester(df=sample_df, primary_key="id", spark=spark)
    invalid_test_data = [(1, True), (2, False), (3, True), (4, False)]
    invalid_test_columns = ["id", "custom_test"]
    invalid_test_result = spark.createDataFrame(invalid_test_data, invalid_test_columns)

    with pytest.raises(TypeError, match="test_description must be of type string"):
        tester.add_custom_test_result(
            result=invalid_test_result, name="custom_test", description=123
        )
