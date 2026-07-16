import sys
from pathlib import Path
from typing import Any

from ai_service import extract_items_with_ai
from database import save_boq_with_items
from excel_reader import read_excel_chunks


SUPPORTED_EXTENSIONS = {".xls", ".xlsx"}


def validate_excel_file(file_path: Path) -> None:
    """
    Checks that the file exists and that it is a valid Excel file.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"The file does not exist: {file_path}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"The provided path is not a file: {file_path}"
        )

    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            "The file must have a .xls or .xlsx extension."
        )


def get_excel_file() -> Path:
    """
    Selects the Excel file to process.

    Option 1:
        python main.py "files/my_boq.xlsx"

    Option 2:
        python main.py

    In the second option, the program automatically selects
    the most recently modified Excel file in the files folder.
    """

    files_folder = Path("files")

    # Creates the files folder if it does not exist.
    files_folder.mkdir(parents=True, exist_ok=True)

    # If a file path is provided in the terminal.
    if len(sys.argv) > 1:
        file_path = Path(sys.argv[1])

        validate_excel_file(file_path)

        return file_path

    # Searches for all Excel files inside the files folder.
    excel_files = [
        file
        for file in files_folder.iterdir()
        if file.is_file()
        and file.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not excel_files:
        raise FileNotFoundError(
            "No Excel file was found in the 'files' folder. "
            "Add a .xls or .xlsx file to this folder."
        )

    # Selects the most recently modified file.
    latest_file = max(
        excel_files,
        key=lambda file: file.stat().st_mtime
    )

    return latest_file


def extract_all_items(file_path: Path) -> list[dict[str, Any]]:
    """
    Reads the Excel file in chunks and sends each chunk to the AI.

    Returns a list containing all detected items.
    """

    all_items: list[dict[str, Any]] = []

    print("\nReading the Excel file...")

    chunks = read_excel_chunks(file_path)

    for chunk_number, chunk in enumerate(chunks, start=1):
        print(
            f"Processing chunk {chunk_number} with the AI..."
        )

        extracted_items = extract_items_with_ai(chunk)

        if not extracted_items:
            print(
                f"No items were detected in chunk {chunk_number}."
            )
            continue

        all_items.extend(extracted_items)

        print(
            f"{len(extracted_items)} item(s) detected "
            f"in chunk {chunk_number}."
        )

    return all_items


def display_items(items: list[dict[str, Any]]) -> None:
    """
    Displays the detected items before saving them.
    """

    print(f"\nTotal number of items found: {len(items)}")

    for position, item in enumerate(items, start=1):
        print("\n" + "-" * 50)
        print(f"Item {position}")
        print(f"Item number   : {item.get('item_number')}")
        print(f"Description   : {item.get('description')}")
        print(f"Quantity      : {item.get('quantity')}")
        print(f"Unit          : {item.get('unit')}")
        print(f"Item type     : {item.get('item_type')}")

        specifications = item.get("specifications", [])

        if specifications:
            print("Specifications:")

            for specification in specifications:
                name = specification.get("name")
                value = specification.get("value")
                unit = specification.get("unit") or ""

                print(
                    f"  - {name}: {value} {unit}".rstrip()
                )
        else:
            print("Specifications: none")


def main() -> None:
    """
    Main function of the program.
    """

    try:
        print("=" * 60)
        print("BOQ IMPORT SYSTEM")
        print("=" * 60)

        # 1. Find the Excel file.
        excel_file = get_excel_file()

        print(f"\nSelected file: {excel_file}")

        # 2. Read the Excel file and extract items using AI.
        items = extract_all_items(excel_file)

        if not items:
            print("\nNo items were found.")
            return

        # 3. Display the result.
        display_items(items)

        # 4. Save the BOQ, its items, and their specifications.
        boq_id = save_boq_with_items(
            boq_name=excel_file.stem,
            file_name=excel_file.name,
            items=items
        )

        print("\n" + "=" * 60)
        print("IMPORT COMPLETED")
        print("=" * 60)
        print(f"BOQ ID: {boq_id}")
        print(f"Saved items: {len(items)}")

    except FileNotFoundError as error:
        print(f"\nFile error: {error}")

    except ValueError as error:
        print(f"\nInvalid data: {error}")

    except ConnectionError as error:
        print(f"\nConnection error: {error}")

    except Exception as error:
        print(f"\nAn unexpected error occurred: {error}")


if __name__ == "__main__":
    main()
