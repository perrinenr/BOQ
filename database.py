import os
from decimal import Decimal, InvalidOperation
from typing import Any

import pyodbc
from dotenv import load_dotenv


# Loads the variables contained in the .env file.
load_dotenv()


def get_database_connection() -> pyodbc.Connection:
    """
    Creates and returns a connection to SQL Server.

    The connection information is retrieved from the .env file.
    """

    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    username = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    driver = os.getenv(
        "DB_DRIVER",
        "ODBC Driver 18 for SQL Server"
    )

    if not server:
        raise ValueError(
            "DB_SERVER is missing from the .env file."
        )

    if not database:
        raise ValueError(
            "DB_NAME is missing from the .env file."
        )

    # Connection using SQL Server authentication.
    if username and password:
        connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
        )

    # Connection using Windows authentication.
    else:
        connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
        )

    try:
        return pyodbc.connect(
            connection_string,
            timeout=30
        )

    except pyodbc.Error as error:
        raise ConnectionError(
            "Unable to connect to SQL Server. "
            f"Details: {error}"
        ) from error


def convert_quantity(value: Any) -> Decimal | None:
    """
    Converts a quantity into Decimal before inserting it
    into the database.

    Examples:
        10       -> Decimal('10')
        12.5     -> Decimal('12.5')
        "125"    -> Decimal('125')
        None     -> None
    """

    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

        # Allows values such as "12,5" to be converted into "12.5".
        value = value.replace(",", ".")

    try:
        return Decimal(str(value))

    except (InvalidOperation, ValueError, TypeError):
        return None


def clean_text(value: Any) -> str | None:
    """
    Converts a value into clean text.

    Returns None when the value is empty.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def clean_item_number(value: Any) -> str | None:
    """
    Converts an item number into clean text.

    Numeric values are formatted with two decimal places.

    Examples:
        1651.12 -> "1651.12"
        5       -> "5.00"
        "A-25"  -> "A-25"
        None    -> None
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        number = float(text)
        return f"{number:.2f}"

    except ValueError:
        return text


def insert_boq(
    cursor: pyodbc.Cursor,
    boq_name: str,
    file_name: str | None
) -> int:
    """
    Inserts a BOQ into the BOQs table and returns its ID.
    """

    cursor.execute(
        """
        INSERT INTO BOQs (
            Name,
            FileName
        )
        OUTPUT INSERTED.Id
        VALUES (?, ?);
        """,
        clean_text(boq_name),
        clean_text(file_name)
    )

    row = cursor.fetchone()

    if row is None:
        raise RuntimeError(
            "Unable to retrieve the BOQ ID."
        )

    return int(row[0])


def insert_item(
    cursor: pyodbc.Cursor,
    boq_id: int,
    item: dict[str, Any]
) -> int:
    """
    Inserts an item into the Items table and returns its ID.
    """

    cursor.execute(
        """
        INSERT INTO Items (
            BOQId,
            ItemNumber,
            Description,
            Quantity,
            Unit,
            ItemType
        )
        OUTPUT INSERTED.Id
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        boq_id,
        clean_item_number(item.get("item_number")),
        clean_text(item.get("description"))
        or "Unknown description",
        convert_quantity(item.get("quantity")),
        clean_text(item.get("unit")),
        clean_text(item.get("item_type")),
    )

    row = cursor.fetchone()

    if row is None:
        raise RuntimeError(
            "Unable to retrieve the item ID."
        )

    return int(row[0])


def insert_specification(
    cursor: pyodbc.Cursor,
    item_id: int,
    specification: dict[str, Any]
) -> None:
    """
    Inserts a technical specification related to an item.
    """

    spec_name = clean_text(specification.get("name"))
    spec_value = clean_text(specification.get("value"))
    spec_unit = clean_text(specification.get("unit"))

    # A specification without a name or value is not saved.
    if not spec_name or not spec_value:
        return

    cursor.execute(
        """
        INSERT INTO ItemSpecifications (
            ItemId,
            SpecName,
            SpecValue,
            SpecUnit
        )
        VALUES (?, ?, ?, ?);
        """,
        item_id,
        spec_name,
        spec_value,
        spec_unit
    )


def save_boq_with_items(
    boq_name: str,
    file_name: str | None,
    items: list[dict[str, Any]]
) -> int:
    """
    Saves a BOQ, its items, and their technical specifications.

    This function is called from main.py.

    It returns the ID of the created BOQ.
    """

    if not items:
        raise ValueError(
            "The item list is empty."
        )

    connection: pyodbc.Connection | None = None

    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        # 1. Save the BOQ file.
        boq_id = insert_boq(
            cursor=cursor,
            boq_name=boq_name,
            file_name=file_name
        )

        # 2. Save all items.
        for item_position, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Item number {item_position} "
                    "is not a valid dictionary."
                )

            item_id = insert_item(
                cursor=cursor,
                boq_id=boq_id,
                item=item
            )

            # 3. Save the item's technical specifications.
            specifications = item.get(
                "specifications",
                []
            )

            if specifications is None:
                specifications = []

            if not isinstance(specifications, list):
                raise ValueError(
                    f"The specifications of item "
                    f"{item_position} must be a list."
                )

            for specification in specifications:
                if not isinstance(specification, dict):
                    continue

                insert_specification(
                    cursor=cursor,
                    item_id=item_id,
                    specification=specification
                )

        # Confirms all database insertions.
        connection.commit()

        return boq_id

    except Exception:
        # Cancels the entire import if an error occurs.
        if connection is not None:
            connection.rollback()

        raise

    finally:
        if connection is not None:
            connection.close()


def test_database_connection() -> None:
    """
    Tests only the SQL Server connection.

    You can run:
        python database.py
    """

    connection: pyodbc.Connection | None = None

    try:
        connection = get_database_connection()

        cursor = connection.cursor()
        cursor.execute("SELECT DB_NAME();")

        row = cursor.fetchone()
        database_name = row[0] if row else "unknown"

        print("SQL Server connection successful.")
        print(f"Database in use: {database_name}")

    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    try:
        test_database_connection()

    except Exception as error:
        print(f"Error: {error}")