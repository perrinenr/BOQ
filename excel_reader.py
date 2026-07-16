from pathlib import Path
from typing import Any, Generator

import pandas as pd


# Maximum number of rows sent to the AI at one time.
DEFAULT_CHUNK_SIZE = 20


def clean_cell_value(value: Any) -> Any:
    """
    Cleans a value coming from an Excel cell.

    Examples:
        NaN        -> None
        "  Cable " -> "Cable"
        10.0       -> 10
    """

    if pd.isna(value):
        return None

    if isinstance(value, str):
        cleaned_value = value.strip()

        if not cleaned_value:
            return None

        return cleaned_value

    # Converts 10.0 into 10, but keeps 10.5 unchanged.
    if isinstance(value, float) and value.is_integer():
        return int(value)

    return value


def clean_column_name(column: Any, position: int) -> str:
    """
    Cleans a column name.

    If a column does not have a name, an automatic name is created.

    Example:
        " Description " -> "Description"
        empty column    -> "Column_3"
    """

    if column is None or pd.isna(column):
        return f"Column_{position}"

    column_name = str(column).strip()

    if not column_name or column_name.lower().startswith("unnamed"):
        return f"Column_{position}"

    return column_name


def make_unique_column_names(columns: list[Any]) -> list[str]:
    """
    Makes column names unique.

    Example:
        Description
        Description

    becomes:
        Description
        Description_2
    """

    unique_columns: list[str] = []
    occurrences: dict[str, int] = {}

    for position, column in enumerate(columns, start=1):
        cleaned_name = clean_column_name(column, position)

        occurrences[cleaned_name] = (
            occurrences.get(cleaned_name, 0) + 1
        )

        occurrence_number = occurrences[cleaned_name]

        if occurrence_number == 1:
            unique_columns.append(cleaned_name)
        else:
            unique_columns.append(
                f"{cleaned_name}_{occurrence_number}"
            )

    return unique_columns


def row_has_useful_data(row: dict[str, Any]) -> bool:
    """
    Checks whether a row contains at least one real value.
    """

    return any(
        value is not None
        and str(value).strip() != ""
        for value in row.values()
    )


def dataframe_to_rows(
    dataframe: pd.DataFrame,
    sheet_name: str
) -> list[dict[str, Any]]:
    """
    Converts an Excel sheet into a list of dictionaries.

    Each dictionary represents one Excel row.
    """

    if dataframe.empty:
        return []

    dataframe = dataframe.copy()

    dataframe.columns = make_unique_column_names(
        list(dataframe.columns)
    )

    rows: list[dict[str, Any]] = []

    for excel_row_number, (_, pandas_row) in enumerate(
        dataframe.iterrows(),
        start=2
    ):
        cleaned_row: dict[str, Any] = {}

        for column_name, value in pandas_row.items():
            cleaned_row[column_name] = clean_cell_value(value)

        if not row_has_useful_data(cleaned_row):
            continue

        # Information added to help the AI understand
        # where the row came from.
        cleaned_row["_sheet_name"] = sheet_name
        cleaned_row["_excel_row"] = excel_row_number

        rows.append(cleaned_row)

    return rows


def create_chunks(
    rows: list[dict[str, Any]],
    chunk_size: int
) -> Generator[list[dict[str, Any]], None, None]:
    """
    Splits a list of rows into several smaller chunks.

    Example with 45 rows and chunk_size = 20:

        chunk 1: rows 1 to 20
        chunk 2: rows 21 to 40
        chunk 3: rows 41 to 45
    """

    if chunk_size <= 0:
        raise ValueError(
            "The chunk size must be greater than zero."
        )

    for start_position in range(0, len(rows), chunk_size):
        end_position = start_position + chunk_size

        yield rows[start_position:end_position]


def read_excel_chunks(
    file_path: Path | str,
    chunk_size: int = DEFAULT_CHUNK_SIZE
) -> Generator[list[dict[str, Any]], None, None]:
    """
    Reads all sheets from an Excel file and returns the data
    in small chunks.

    This function is called from main.py using:

        chunks = read_excel_chunks(file_path)
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"The Excel file does not exist: {file_path}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"The provided path is not a file: {file_path}"
        )

    if file_path.suffix.lower() not in {".xls", ".xlsx"}:
        raise ValueError(
            "The file must be in .xls or .xlsx format."
        )

    if chunk_size <= 0:
        raise ValueError(
            "The chunk size must be greater than zero."
        )

    try:
        # sheet_name=None means: read all sheets.
        sheets = pd.read_excel(
            file_path,
            sheet_name=None,
            dtype=object
        )

    except ImportError as error:
        raise ImportError(
            "A required library for reading Excel files is missing. "
            "Install pandas, openpyxl, and xlrd."
        ) from error

    except Exception as error:
        raise RuntimeError(
            f"Unable to read the Excel file: {error}"
        ) from error

    if not sheets:
        raise ValueError(
            "The Excel file does not contain any sheets."
        )

    useful_rows_found = False

    for sheet_name, dataframe in sheets.items():
        rows = dataframe_to_rows(
            dataframe=dataframe,
            sheet_name=str(sheet_name)
        )

        if not rows:
            print(
                f"Sheet ignored because it is empty: {sheet_name}"
            )
            continue

        useful_rows_found = True

        print(
            f"Sheet detected: {sheet_name} "
            f"({len(rows)} useful row(s))"
        )

        for chunk in create_chunks(
            rows=rows,
            chunk_size=chunk_size
        ):
            yield chunk

    if not useful_rows_found:
        raise ValueError(
            "No useful data was found in the Excel file."
        )


def preview_excel(
    file_path: Path | str,
    maximum_rows: int = 5
) -> None:
    """
    Displays a few rows to test the Excel file reading process.

    You can run:

        python excel_reader.py "files/my_boq.xlsx"
    """

    displayed_rows = 0

    for chunk_number, chunk in enumerate(
        read_excel_chunks(file_path),
        start=1
    ):
        print("\n" + "=" * 60)
        print(f"Chunk number {chunk_number}")
        print("=" * 60)

        for row in chunk:
            print(row)

            displayed_rows += 1

            if displayed_rows >= maximum_rows:
                return


if __name__ == "__main__":
    import sys

    try:
        if len(sys.argv) < 2:
            print(
                'Usage: python excel_reader.py '
                '"files/my_boq.xlsx"'
            )
        else:
            preview_excel(sys.argv[1])

    except Exception as error:
        print(f"Error: {error}")
