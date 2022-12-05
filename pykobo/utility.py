import pandas as pd


def clean_df(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """
    Given a Pandas DataFrame and a list of columns
    only keep the columns of the DataFrame that are in the list
    """

    return df[columns]


def lowercase_columns_name(df: pd.DataFrame) -> None:
    """
    Lowercase the name of all columns of the DataFrame 'df'
    """
    df.columns = df.columns.str.lower()


def lowercase_column_values(df: pd.DataFrame, column: str) -> None:
    """
    Lowercase the values of the column 'column' in the DataFramce 'df'
    """
    df[column] = df[column].str.lower()


def capitalize_column_values(df: pd.DataFrame, column: str) -> None:
    """
    Capitalize the values of the column 'column' in the DataFramce 'df'
    """
    df[column] = df[column].str.capitalize()


def trim_columns_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Trim whitespace from ends of each value across all series in dataframe
    Source: https://stackoverflow.com/questions/40950310/strip-trim-all-strings-of-a-dataframe
    """

    def trim_ws(x):
        return x.strip() if isinstance(x, str) else x

    def trim_pt(x):
        return x.strip(".") if isinstance(x, str) else x

    df_temp = df.applymap(trim_ws)
    return df_temp.applymap(trim_pt)


def reconcile_columns(
    df: pd.DataFrame, col1: str, col2: str, new_column: str, criteria=float("nan")
) -> None:
    """
    Given a DF, reconcile its 2 columns `col1` and `col2` into a new column `new_column`, as follow:
        if `col1` is null get the values from `col2` into `new_column`
        if `col1` is not null get the values from `col1` into `new_column`
    This means that `col1` is considered more important than `col2`
    Then delete columns `col1` and `col2`
    """

    # `_temp` is a temporary name for `new_column`

    if pd.isna(criteria):
        df.loc[(df[col1].isnull()), "_temp"] = df[col2]

        df.loc[(df[col1].notnull()), "_temp"] = df[col1]
    elif type(criteria) == str:
        df.loc[(df[col1] == criteria), "_temp"] = df[col2]

        df.loc[(df[col1] != criteria), "_temp"] = df[col1]
    else:
        raise TypeError(
            f"The argument `criteria` is of type: `{type(criteria)}`. It should be of type `<class 'str'>` or equal to `NaN`"
        )

    # Delete the 2 columns
    df.drop(columns=[col1, col2], inplace=True)

    # Rename column `_temp` to `new_column`
    df.rename(columns={"_temp": new_column}, inplace=True)


def reconcile_columns_append(
    df: pd.DataFrame, col1: str, col2: str, new_column: str, to_replace: str
) -> None:
    """TODO
    XXX: See if can merge this function and the one above into 1
    """

    # If the column is not of type str we convert it
    # This can happen for columns that are empty and were
    # not in the JSON object so we created empty column containing NaN
    if df[col1].dtype != "object":
        df[col1] = df[col1].astype(str)

    selection = df[col1].str.contains(to_replace, na=False)
    for index, row in df.loc[selection].iterrows():
        df.loc[index, col1] = row[col1].replace(to_replace, row[col2])

    df["_temp"] = df[col1]

    # Delete the 2 columns
    df.drop(columns=[col1, col2], inplace=True)

    # Rename column `_temp` to `new_column`
    df.rename(columns={"_temp": new_column}, inplace=True)


def fix_typos(df: pd.DataFrame, column: str, typos: list) -> None:
    for typo in typos:
        df.loc[df[column] == typo[0], column] = typo[1]


def fillna(df: pd.DataFrame, column: str) -> None:
    df[column] = df[column].fillna(0)


def convert_toint(df: pd.DataFrame, column) -> None:
    df[column] = df[column].astype(int)
