import sys
from pathlib import Path
from typing import Any

from ai_service import extract_items_with_ai
from database import save_boq_with_items, save_cad_drawing
from dwg_converter import convert_dwg_to_dxf
from dxf_reader import read_dxf_file
from excel_reader import read_excel_chunks
from pdf_ai_service import extract_pdf_items_with_ai
from pdf_reader import read_pdf_file


SUPPORTED_EXTENSIONS = {
    ".xls",
    ".xlsx",
    ".pdf",
    ".dwg"
}


def validate_input_file(file_path: Path) -> None:
    """
    Vérifie que le fichier existe et que son extension
    est supportée par le programme.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"The file does not exist: {file_path}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"The selected path is not a file: {file_path}"
        )

    extension = file_path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            "The file must have a .xls, .xlsx, "
            ".pdf, or .dwg extension."
        )


def get_input_file() -> Path:
    """
    Récupère le fichier à traiter.

    Avec un chemin donné dans le terminal :

        python main.py files/my_file.xlsx
        python main.py files/my_file.pdf
        python main.py files/my_file.dwg

    Sans argument :

        python main.py

    Le programme sélectionne le fichier compatible
    modifié le plus récemment dans le dossier files.
    """

    files_folder = Path("files")

    files_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    # Un chemin a été fourni dans le terminal.
    if len(sys.argv) > 1:
        file_path = Path(sys.argv[1])

        validate_input_file(file_path)

        return file_path

    # Aucun chemin fourni :
    # rechercher dans le dossier files.
    input_files = [
        file
        for file in files_folder.iterdir()
        if file.is_file()
        and file.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not input_files:
        raise FileNotFoundError(
            "No supported file was found in the 'files' folder. "
            "Add a .xls, .xlsx, .pdf, or .dwg file."
        )

    latest_file = max(
        input_files,
        key=lambda file: file.stat().st_mtime
    )

    return latest_file


# ============================================================
# EXCEL
# ============================================================

def extract_excel_items(
    file_path: Path
) -> list[dict[str, Any]]:
    """
    Lit un fichier Excel en morceaux et utilise
    l'IA définie dans ai_service.py.
    """

    all_items: list[dict[str, Any]] = []

    print("\nReading the Excel file...")

    chunks = list(
        read_excel_chunks(file_path)
    )

    if not chunks:
        print("No readable Excel content was found.")
        return []

    print(
        f"Number of Excel chunks: {len(chunks)}"
    )

    for chunk_number, chunk in enumerate(
        chunks,
        start=1
    ):
        print(
            f"\nProcessing Excel chunk "
            f"{chunk_number}/{len(chunks)} with the AI..."
        )

        extracted_items = extract_items_with_ai(
            chunk
        )

        if not extracted_items:
            print(
                f"No items were detected in Excel chunk "
                f"{chunk_number}."
            )
            continue

        all_items.extend(
            extracted_items
        )

        print(
            f"{len(extracted_items)} item(s) detected "
            f"in Excel chunk {chunk_number}."
        )

    return all_items


# ============================================================
# PDF
# ============================================================

def create_pdf_chunks(
    rows: list[dict[str, Any]],
    group_size: int = 5
) -> list[list[dict[str, Any]]]:
    """
    Regroupe plusieurs lignes du PDF dans un même chunk.

    Exemple :
    25 lignes avec group_size = 5 donnent 5 chunks.
    """

    if group_size <= 0:
        raise ValueError(
            "PDF group size must be greater than zero."
        )

    return [
        rows[index:index + group_size]
        for index in range(
            0,
            len(rows),
            group_size
        )
    ]


def extract_pdf_items(
    file_path: Path
) -> list[dict[str, Any]]:
    """
    Lit les tableaux du PDF et utilise l'IA spécialisée
    définie dans pdf_ai_service.py.
    """

    all_items: list[dict[str, Any]] = []

    print("\nReading PDF tables...")

    pdf_rows = read_pdf_file(
        file_path
    )

    if not pdf_rows:
        raise ValueError(
            f"No table rows were found in PDF: "
            f"{file_path.name}"
        )

    print(
        f"Number of PDF rows found: "
        f"{len(pdf_rows)}"
    )

    chunks = create_pdf_chunks(
        rows=pdf_rows,
        group_size=5
    )

    print(
        f"Number of PDF chunks: "
        f"{len(chunks)}"
    )

    for chunk_number, rows in enumerate(
        chunks,
        start=1
    ):
        print(
            f"\nProcessing PDF chunk "
            f"{chunk_number}/{len(chunks)} "
            f"with the AI..."
        )

        extracted_items = (
            extract_pdf_items_with_ai(rows)
        )

        if not extracted_items:
            print(
                f"No items were detected in PDF chunk "
                f"{chunk_number}."
            )
            continue

        all_items.extend(
            extracted_items
        )

        print(
            f"{len(extracted_items)} item(s) detected "
            f"in PDF chunk {chunk_number}."
        )

    if not all_items:
        raise ValueError(
            f"The PDF was read, but no items were extracted: "
            f"{file_path.name}"
        )

    return all_items


# ============================================================
# EXCEL / PDF ROUTING
# ============================================================

def extract_all_items(
    file_path: Path
) -> list[dict[str, Any]]:
    """
    Choisit automatiquement le lecteur et l'IA
    selon l'extension du fichier.

    Cette fonction traite uniquement Excel et PDF.
    Le DWG est traité séparément.
    """

    extension = file_path.suffix.lower()

    if extension in {
        ".xls",
        ".xlsx"
    }:
        return extract_excel_items(
            file_path
        )

    if extension == ".pdf":
        return extract_pdf_items(
            file_path
        )

    raise ValueError(
        f"Unsupported item file format: "
        f"{extension}"
    )


# ============================================================
# DWG
# ============================================================

def process_dwg_file(
    file_path: Path
) -> None:
    """
    Convertit le DWG en DXF, lit les entités du DXF
    et les sauvegarde dans SQL Server.

    Cette partie reste inchangée.
    """

    print(
        "\nConverting DWG to DXF..."
    )

    dxf_file = convert_dwg_to_dxf(
        file_path
    )

    print(
        f"Converted DXF file: "
        f"{dxf_file}"
    )

    print(
        "\nReading DXF entities..."
    )

    entities = read_dxf_file(
        dxf_file
    )

    if not entities:
        print(
            "No CAD entities were found."
        )
        return

    print(
        f"Number of CAD entities found: "
        f"{len(entities)}"
    )

    drawing_id = save_cad_drawing(
        original_file=file_path,
        converted_file=dxf_file,
        entities=entities
    )

    print(
        "\n" + "=" * 60
    )

    print(
        "CAD IMPORT COMPLETED"
    )

    print(
        "=" * 60
    )

    print(
        f"Drawing ID     : "
        f"{drawing_id}"
    )

    print(
        f"Saved entities : "
        f"{len(entities)}"
    )

    print(
        f"Original file  : "
        f"{file_path.name}"
    )

    print(
        f"Converted file : "
        f"{dxf_file.name}"
    )


# ============================================================
# DISPLAY ITEMS
# ============================================================

def display_items(
    items: list[dict[str, Any]]
) -> None:
    """
    Affiche les items trouvés avant leur sauvegarde.
    """

    print(
        f"\nTotal number of items found: "
        f"{len(items)}"
    )

    for position, item in enumerate(
        items,
        start=1
    ):
        print(
            "\n" + "-" * 60
        )

        print(
            f"Item {position}"
        )

        # Compatible avec l'ancien format item_number
        # et le nouveau format item.
        item_number = (
            item.get("item")
            or item.get("item_number")
        )

        print(
            f"Item number : "
            f"{item_number}"
        )

        print(
            f"Brand       : "
            f"{item.get('brand')}"
        )

        print(
            f"Reference   : "
            f"{item.get('reference')}"
        )

        print(
            f"Description : "
            f"{item.get('description')}"
        )

        print(
            f"Quantity    : "
            f"{item.get('quantity')}"
        )

        print(
            f"Unit        : "
            f"{item.get('unit')}"
        )

        print(
            f"Unit price  : "
            f"{item.get('unit_price')}"
        )

        print(
            f"Total       : "
            f"{item.get('total')}"
        )

        print(
            f"Item type   : "
            f"{item.get('item_type')}"
        )

        specifications = item.get(
            "specifications",
            []
        )

        if not specifications:
            print(
                "Specifications: none"
            )
            continue

        print(
            "Specifications:"
        )

        for specification in specifications:
            name = specification.get(
                "name"
            )

            value = specification.get(
                "value"
            )

            unit = (
                specification.get(
                    "unit"
                )
                or ""
            )

            print(
                f"  - {name}: "
                f"{value} {unit}".rstrip()
            )


# ============================================================
# SAVE EXCEL / PDF
# ============================================================

def process_item_file(
    file_path: Path
) -> None:
    """
    Traite un fichier Excel ou PDF,
    affiche les items et les sauvegarde
    dans la base de données.
    """

    items = extract_all_items(
        file_path
    )

    # IMPORTANT :
    # avant le programme faisait simplement "return".
    # L'interface pensait alors que l'import avait réussi.
    if not items:
        raise ValueError(
            f"No items were extracted from "
            f"{file_path.name}."
        )

    display_items(
        items
    )

    print(
        "\nSaving items to database..."
    )

    boq_id = save_boq_with_items(
        boq_name=file_path.stem,
        file_name=file_path.name,
        items=items
    )

    print(
        "\n" + "=" * 60
    )

    print(
        "IMPORT COMPLETED"
    )

    print(
        "=" * 60
    )

    print(
        f"BOQ ID      : "
        f"{boq_id}"
    )

    print(
        f"Saved items : "
        f"{len(items)}"
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """
    Fonction principale du programme.
    """

    try:
        print(
            "=" * 60
        )

        print(
            "BOQ IMPORT SYSTEM"
        )

        print(
            "=" * 60
        )

        # 1. Récupérer le fichier.
        input_file = get_input_file()

        extension = (
            input_file.suffix.lower()
        )

        print(
            f"\nSelected file: "
            f"{input_file}"
        )

        print(
            f"Detected format: "
            f"{extension}"
        )

        # 2. Traitement DWG.
        if extension == ".dwg":
            process_dwg_file(
                input_file
            )
            return

        # 3. Traitement Excel ou PDF.
        if extension in {
            ".xls",
            ".xlsx",
            ".pdf"
        }:
            process_item_file(
                input_file
            )
            return

        raise ValueError(
            f"Unsupported file format: "
            f"{extension}"
        )

    except FileNotFoundError as error:
        print(
            f"\nFile error: "
            f"{error}"
        )

    except ValueError as error:
        print(
            f"\nInvalid data: "
            f"{error}"
        )

    except ConnectionError as error:
        print(
            f"\nConnection error: "
            f"{error}"
        )

    except ImportError as error:
        print(
            f"\nImport error: "
            f"{error}"
        )

    except Exception as error:
        print(
            f"\nAn unexpected error occurred: "
            f"{type(error).__name__}: "
            f"{error}"
        )


if __name__ == "__main__":
    main()