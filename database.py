import json
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pyodbc
from dotenv import load_dotenv


# Charge les variables du fichier .env.
load_dotenv()


def get_database_connection() -> pyodbc.Connection:
    """
    Crée et retourne une connexion à SQL Server.

    Les informations de connexion sont récupérées
    depuis le fichier .env.
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

    # Connexion avec un username et un password SQL Server.
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

    # Connexion avec le compte Windows.
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
    Convertit une quantité en Decimal avant de
    l'insérer dans SQL Server.

    Exemples :
        10       -> Decimal("10")
        12.5     -> Decimal("12.5")
        "125"    -> Decimal("125")
        None     -> None
    """

    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

        # Accepte par exemple "12,5".
        value = value.replace(",", ".")

    try:
        return Decimal(str(value))

    except (InvalidOperation, ValueError, TypeError):
        return None


def clean_text(value: Any) -> str | None:
    """
    Convertit une valeur en texte propre.

    Retourne None lorsque la valeur est vide.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def clean_item_number(value: Any) -> str | None:
    """
    Nettoie le numéro d'un item.

    Les valeurs numériques sont arrondies
    à deux décimales.

    Exemples :
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
    Insère un BOQ dans la table BOQs et retourne son ID.
    """

    cursor.execute(
        """
        INSERT INTO BOQs
        (
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
    Insère un item dans la table Items et retourne son ID.
    """

    cursor.execute(
        """
        INSERT INTO Items
        (
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
        clean_text(item.get("item_type"))
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
    Insère une spécification technique liée à un item.
    """

    spec_name = clean_text(
        specification.get("name")
    )

    spec_value = clean_text(
        specification.get("value")
    )

    spec_unit = clean_text(
        specification.get("unit")
    )

    # Une spécification sans nom ou sans valeur
    # n'est pas enregistrée.
    if not spec_name or not spec_value:
        return

    cursor.execute(
        """
        INSERT INTO ItemSpecifications
        (
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
    Enregistre un BOQ, ses items et leurs spécifications.

    Cette fonction est utilisée pour Excel et PDF.
    """

    if not items:
        raise ValueError(
            "The item list is empty."
        )

    connection: pyodbc.Connection | None = None

    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        # 1. Enregistrer le fichier BOQ.
        boq_id = insert_boq(
            cursor=cursor,
            boq_name=boq_name,
            file_name=file_name
        )

        # 2. Enregistrer tous les items.
        for item_position, item in enumerate(
            items,
            start=1
        ):
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

            # 3. Enregistrer les spécifications.
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

        connection.commit()

        return boq_id

    except Exception:
        if connection is not None:
            connection.rollback()

        raise

    finally:
        if connection is not None:
            connection.close()


def save_cad_drawing(
    original_file: Path,
    converted_file: Path,
    entities: list[dict[str, Any]]
) -> int:
    """
    Enregistre le dessin CAD et toutes ses entités.

    Le fichier DWG original est enregistré dans CADDrawings.
    Le fichier DXF converti est également enregistré.
    Les entités sont enregistrées dans CADEntities.
    """

    if not entities:
        raise ValueError(
            "The CAD entity list is empty."
        )

    connection: pyodbc.Connection | None = None

    try:
        # Correction importante :
        # on utilise la vraie fonction de connexion.
        connection = get_database_connection()
        cursor = connection.cursor()

        # 1. Enregistrer le dessin.
        cursor.execute(
            """
            INSERT INTO CADDrawings
            (
                OriginalFileName,
                ConvertedFileName
            )
            OUTPUT INSERTED.Id
            VALUES (?, ?);
            """,
            original_file.name,
            converted_file.name
        )

        row = cursor.fetchone()

        if row is None:
            raise RuntimeError(
                "Unable to retrieve the CAD drawing ID."
            )

        drawing_id = int(row[0])

        # 2. Enregistrer chaque entité du DXF.
        for entity_position, entity in enumerate(
            entities,
            start=1
        ):
            if not isinstance(entity, dict):
                print(
                    f"Warning: CAD entity "
                    f"{entity_position} was ignored."
                )
                continue

            entity_type = clean_text(
                entity.get("entity_type")
            )

            layer_name = clean_text(
                entity.get("layer")
            )

            text_value = clean_text(
                entity.get("text")
            )

            block_name = clean_text(
                entity.get("block_name")
            )

            if not entity_type:
                entity_type = "UNKNOWN"

            # Les autres données sont enregistrées en JSON.
            remaining_data = {
                key: value
                for key, value in entity.items()
                if key not in {
                    "entity_type",
                    "layer",
                    "text",
                    "block_name"
                }
            }

            try:
                data_json = json.dumps(
                    remaining_data,
                    ensure_ascii=False,
                    default=str
                )

            except (TypeError, ValueError):
                data_json = "{}"

            cursor.execute(
                """
                INSERT INTO CADEntities
                (
                    DrawingId,
                    EntityType,
                    LayerName,
                    TextValue,
                    BlockName,
                    DataJson
                )
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                drawing_id,
                entity_type,
                layer_name,
                text_value,
                block_name,
                data_json
            )

        connection.commit()

        return drawing_id

    except Exception:
        if connection is not None:
            connection.rollback()

        raise

    finally:
        if connection is not None:
            connection.close()


def test_database_connection() -> None:
    """
    Teste uniquement la connexion à SQL Server.

    Commande :
        python database.py
    """

    connection: pyodbc.Connection | None = None

    try:
        connection = get_database_connection()

        cursor = connection.cursor()

        cursor.execute(
            "SELECT DB_NAME();"
        )

        row = cursor.fetchone()

        database_name = (
            row[0]
            if row
            else "unknown"
        )

        print("SQL Server connection successful.")
        print(f"Database in use: {database_name}")

    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    try:
        test_database_connection()

    except Exception as error:
        print(
            f"Error: {type(error).__name__}: {error}"
        )