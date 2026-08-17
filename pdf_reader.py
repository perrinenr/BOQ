from pathlib import Path
from typing import Any

import pdfplumber


def clean_text(value: Any) -> str | None:
    """
    Nettoie une cellule extraite du PDF.
    """

    if value is None:
        return None

    text = str(value).replace("\n", " ").strip()

    if not text:
        return None

    return " ".join(text.split())


def normalize_header(header: str | None) -> str | None:
    """
    Nettoie et normalise légèrement le nom d'une colonne
    sans changer son sens.

    Exemple :
        "Product\nCode" -> "Product Code"
    """

    if header is None:
        return None

    header = clean_text(header)

    if not header:
        return None

    return header


def is_empty_row(row: list[str | None]) -> bool:
    """
    Retourne True si toute la ligne est vide.
    """

    return not any(
        value
        for value in row
        if value is not None
    )


def looks_like_header(row: list[str | None]) -> bool:
    """
    Vérifie si une ligne ressemble à un en-tête de tableau.
    """

    values = {
        str(value).strip().lower()
        for value in row
        if value
    }

    known_headers = {
        "type",
        "item",
        "item number",
        "item no",
        "item no.",
        "brand",
        "manufacturer",
        "product code",
        "productcode",
        "reference",
        "ref",
        "ref.",
        "description",
        "image",
        "location",
        "lamp",
        "model",
        "model number",
    }

    matches = values.intersection(
        known_headers
    )

    return len(matches) >= 2


def make_row_dictionary(
    headers: list[str | None],
    values: list[str | None],
    page_number: int,
    table_number: int
) -> dict[str, Any]:
    """
    Transforme une ligne PDF en dictionnaire :

    Exemple :

    headers:
        Type | Brand | Product Code | Description

    values:
        L01 | i-LèD | C00127 | LED strip

    devient :

    {
        "page": 2,
        "table": 1,
        "Type": "L01",
        "Brand": "i-LèD",
        "Product Code": "C00127",
        "Description": "LED strip"
    }
    """

    row: dict[str, Any] = {
        "page": page_number,
        "table": table_number
    }

    for index, value in enumerate(
        values
    ):
        if index >= len(headers):
            continue

        header = headers[index]

        if not header:
            continue

        # Ignorer complètement la colonne Image.
        if header.strip().lower() == "image":
            continue

        row[header] = value

    return row


def read_pdf_file(
    file_path: Path
) -> list[dict[str, Any]]:
    """
    Lit tous les tableaux de toutes les pages du PDF.

    La première ligne utile du tableau est conservée
    comme noms de colonnes.

    Ainsi l'IA reçoit par exemple :

    {
        "Type": "L01",
        "Brand": "i-LèD / Linealight",
        "Product Code": "C00127CCWDI",
        "Description": "...",
        "Location": "Facade"
    }

    au lieu de recevoir simplement :

    {
        "cells": [...]
    }

    Cela permet notamment de comprendre clairement :

        Product Code -> reference
        Brand -> brand
        Type -> item_number
    """

    rows: list[dict[str, Any]] = []

    with pdfplumber.open(file_path) as pdf:

        total_pages = len(
            pdf.pages
        )

        print(
            f"PDF contains "
            f"{total_pages} page(s)."
        )

        for page_number, page in enumerate(
            pdf.pages,
            start=1
        ):
            print(
                f"Reading PDF page "
                f"{page_number}/{total_pages}..."
            )

            tables = page.extract_tables()

            if not tables:
                print(
                    f"Warning: no table detected "
                    f"on page {page_number}."
                )
                continue

            print(
                f"{len(tables)} table(s) detected "
                f"on page {page_number}."
            )

            for table_number, table in enumerate(
                tables,
                start=1
            ):
                if not table:
                    continue

                print(
                    f"Reading table "
                    f"{table_number} "
                    f"on page {page_number}..."
                )

                # ---------------------------------------------
                # Nettoyer toutes les lignes du tableau
                # ---------------------------------------------

                cleaned_table: list[
                    list[str | None]
                ] = []

                for raw_row in table:

                    if not raw_row:
                        continue

                    cleaned_row = [
                        clean_text(cell)
                        for cell in raw_row
                    ]

                    if is_empty_row(
                        cleaned_row
                    ):
                        continue

                    cleaned_table.append(
                        cleaned_row
                    )

                if not cleaned_table:
                    continue

                # ---------------------------------------------
                # Trouver la ligne d'en-tête
                # ---------------------------------------------

                header_index = None

                for index, row in enumerate(
                    cleaned_table
                ):
                    if looks_like_header(row):
                        header_index = index
                        break

                if header_index is None:
                    print(
                        f"Warning: no recognizable "
                        f"header found in table "
                        f"{table_number} "
                        f"on page {page_number}."
                    )
                    continue

                headers = [
                    normalize_header(header)
                    for header
                    in cleaned_table[
                        header_index
                    ]
                ]

                print(
                    f"Headers detected: "
                    f"{headers}"
                )

                # ---------------------------------------------
                # Toutes les lignes après l'en-tête
                # sont considérées comme données.
                # ---------------------------------------------

                data_rows = cleaned_table[
                    header_index + 1:
                ]

                for values in data_rows:

                    # Par sécurité, ignorer un deuxième
                    # en-tête répété.
                    if looks_like_header(values):
                        continue

                    # Au moins une vraie valeur.
                    useful_values = [
                        value
                        for value in values
                        if value
                    ]

                    if not useful_values:
                        continue

                    row = make_row_dictionary(
                        headers=headers,
                        values=values,
                        page_number=page_number,
                        table_number=table_number
                    )

                    # -----------------------------------------
                    # Ne garder que les lignes contenant
                    # au moins une vraie donnée en plus de
                    # page/table.
                    # -----------------------------------------

                    content_values = [
                        value
                        for key, value in row.items()
                        if key not in {
                            "page",
                            "table"
                        }
                        and value
                    ]

                    if not content_values:
                        continue

                    rows.append(
                        row
                    )

    print(
        f"Total PDF rows extracted: "
        f"{len(rows)}"
    )

    return rows