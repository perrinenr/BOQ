import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


PDF_MODEL = "gpt-4.1-mini"


# ============================================================
# PROMPT
# ============================================================

def create_pdf_prompt(
    rows: list[dict[str, Any]]
) -> str:
    """
    Crée les instructions adaptées aux Lighting Fixture
    Schedule PDF.

    Mapping principal :

    Type / Item       -> item_number
    Manufacturer      -> brand
    ProductCode       -> reference
    Description       -> description
    Location          -> specifications
    """

    rows_json = json.dumps(
        rows,
        ensure_ascii=False,
        indent=2
    )

    return f"""
You are an expert electrical BOQ data extraction system.

You are processing rows extracted from a PDF document such as
a Lighting Fixtures Schedule.

The PDF is not necessarily a traditional BOQ.

Each source row may represent a lighting fixture, accessory,
driver, profile, connector, lamp, or another related product.


============================================================
INPUT STRUCTURE
============================================================

The input rows may contain fields or table cells corresponding to:

- page
- item
- type
- item number
- item code
- brand
- manufacturer
- ProductCode
- Product Code
- product_code
- Ref
- Reference
- Model
- Model Number
- description
- lamp
- location


============================================================
COLUMN MAPPING
============================================================

The mapping is VERY IMPORTANT.


ITEM NUMBER:

- Type -> item_number
- Item -> item_number
- Item Number -> item_number
- Item Code -> item_number
- BOQ code -> item_number


BRAND:

- Manufacturer -> brand
- Brand -> brand
- Make -> brand


REFERENCE:

The following fields MUST be stored in the top-level
"reference" field:

- ProductCode
- Product Code
- product_code
- Product Ref
- Product Reference
- Ref
- Ref.
- Reference
- Manufacturer Reference
- Model
- Model Number
- Model No.
- Catalogue Code
- Catalog Code


CRITICAL RULE:

ProductCode = reference

Product Code = reference

Never store ProductCode inside specifications.


DESCRIPTION:

- Description -> description


LOCATION:

- Location must be stored as a specification named Location.


============================================================
EXAMPLE
============================================================

Source:

Type = L01
Manufacturer = i-LèD / Linealight
ProductCode = C00127CCWDI
Description = Encapsulated 3D Bend LED Strip 10W/m 3000K IP67
Location = Facade


Required result:

{{
    "item_number": "L01",
    "brand": "i-LèD / Linealight",
    "reference": "C00127CCWDI",
    "description": "Encapsulated 3D Bend LED Strip 10W/m 3000K IP67",
    "quantity": null,
    "unit": null,
    "item_type": "Lighting Fixture",
    "specifications": [
        {{
            "name": "Power",
            "value": "10",
            "unit": "W/m"
        }},
        {{
            "name": "ColorTemperature",
            "value": "3000",
            "unit": "K"
        }},
        {{
            "name": "ProtectionRating",
            "value": "IP67",
            "unit": null
        }},
        {{
            "name": "Location",
            "value": "Facade",
            "unit": null
        }}
    ]
}}


============================================================
IMPORTANT RULES
============================================================

1. Create one structured item for every real product/item.

2. Never combine two different real items into one.

3. Do not split one real item into several items unless the
   source clearly contains separate products.

4. item_number must come from the source item/type/BOQ code.

5. Never use ProductCode as item_number.

6. ProductCode belongs only in reference.

7. Manufacturer belongs only in brand.

8. Manufacturer must NOT be stored as a specification.

9. ProductCode must NOT be stored as a specification.

10. Preserve item identifiers exactly.

Examples:

F1
F2E
UU1
UU1E
UU2E
UU3
UU3E
L01
L02
L03

UU1 and UU1E are different items.

11. Do not invent quantity.

12. If quantity is absent, return null.

13. Do not invent unit.

14. If quantity unit is absent, return null.

15. Set item_type to "Lighting Fixture" for lighting-related
    products in this schedule.

16. Extract technical specifications from description,
    lamp, and other technical text.

Possible specifications include:

- LampType
- Power
- LuminousFlux
- ColorTemperature
- BeamAngle
- Diameter
- Length
- Width
- Height
- ProtectionRating
- EmergencyBatteryAutonomy
- MountingType
- Voltage
- Current
- Frequency
- Material
- Location


============================================================
SPECIFICATION FORMAT
============================================================

Store numerical values without their units when possible.


Example:

"28 W"

becomes:

{{
    "name": "Power",
    "value": "28",
    "unit": "W"
}}


Example:

"2000lm"

becomes:

{{
    "name": "LuminousFlux",
    "value": "2000",
    "unit": "lm"
}}


Example:

"3000K"

becomes:

{{
    "name": "ColorTemperature",
    "value": "3000",
    "unit": "K"
}}


Example:

"DIAMETER: 215 mm"

becomes:

{{
    "name": "Diameter",
    "value": "215",
    "unit": "mm"
}}


Example:

"IP67"

becomes:

{{
    "name": "ProtectionRating",
    "value": "IP67",
    "unit": null
}}


Example:

"Equipped with 1Hr emergency battery kit"

becomes:

{{
    "name": "EmergencyBatteryAutonomy",
    "value": "1",
    "unit": "hour"
}}


============================================================
MOUNTING TYPE
============================================================

Extract mounting type when clearly stated.

Examples:

"RECESSED LUMINAIRE"
-> Recessed

"SURFACE MOUNTED LUMINAIRE"
-> Surface Mounted

"WALL-MOUNTED LUMINAIRE"
-> Wall Mounted

"CEILING MOUNTED"
-> Ceiling Mounted


============================================================
OTHER RULES
============================================================

- Do not add specifications that are not clearly present.

- Do not create duplicate specifications.

- Preserve the complete description.

- Do not invent brand.

- Do not invent reference.

- Do not invent product codes.

- Ignore empty image cells.

- Ignore graphical placeholders.

- Ignore table headers.

- Ignore document titles.

- Ignore page titles.

- Return only valid JSON.


============================================================
REQUIRED JSON FORMAT
============================================================

{{
    "items": [
        {{
            "item_number": "L01",
            "brand": "i-LèD / Linealight",
            "reference": "C00127CCWDI",
            "description": "Complete fixture description",
            "quantity": null,
            "unit": null,
            "item_type": "Lighting Fixture",
            "specifications": [
                {{
                    "name": "LampType",
                    "value": "LED",
                    "unit": null
                }},
                {{
                    "name": "Power",
                    "value": "10",
                    "unit": "W/m"
                }},
                {{
                    "name": "ProtectionRating",
                    "value": "IP67",
                    "unit": null
                }},
                {{
                    "name": "Location",
                    "value": "Facade",
                    "unit": null
                }}
            ]
        }}
    ]
}}


============================================================
INPUT PDF ROWS
============================================================

{rows_json}
"""


# ============================================================
# PARSE AI RESPONSE
# ============================================================

def parse_pdf_ai_response(
    response_text: str
) -> list[dict[str, Any]]:
    """
    Convertit la réponse JSON de l'IA en liste Python.
    """

    if not response_text:
        return []

    cleaned_text = response_text.strip()

    # Au cas où l'IA ajoute ```json
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]

    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:]

    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]

    cleaned_text = cleaned_text.strip()

    try:
        data = json.loads(cleaned_text)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"The PDF AI returned invalid JSON: {error}"
        ) from error

    items = data.get(
        "items",
        []
    )

    if not isinstance(items, list):
        raise ValueError(
            "The PDF AI response must contain an 'items' list."
        )

    return items


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_pdf_item(
    item: dict[str, Any]
) -> dict[str, Any]:
    """
    Corrige automatiquement certains champs après
    la réponse de l'IA.

    Exemple :

    specifications:
        ProductCode = C00127CCWDI

    devient :

    reference = C00127CCWDI
    """

    specifications = item.get(
        "specifications"
    ) or []

    cleaned_specifications: list[
        dict[str, Any]
    ] = []

    # Tous ces noms correspondent à Reference.
    reference_names = {
        "productcode",
        "product code",
        "product_code",
        "product ref",
        "product reference",
        "productreference",
        "ref",
        "ref.",
        "reference",
        "manufacturer reference",
        "manufacturerreference",
        "model",
        "model number",
        "modelnumber",
        "model no",
        "model no.",
        "catalogue code",
        "cataloguecode",
        "catalog code",
        "catalogcode",
        "catalogue reference",
        "catalog reference",
    }

    # Tous ces noms correspondent à Brand.
    brand_names = {
        "brand",
        "manufacturer",
        "manufacturer name",
        "make",
        "maker",
    }

    for specification in specifications:

        if not isinstance(
            specification,
            dict
        ):
            continue

        raw_name = specification.get(
            "name"
        )

        name = str(
            raw_name or ""
        ).strip().lower()

        value = specification.get(
            "value"
        )

        # ----------------------------------------------------
        # PRODUCT CODE -> REFERENCE
        # ----------------------------------------------------

        if name in reference_names:

            if (
                value is not None
                and not item.get("reference")
            ):
                item["reference"] = str(
                    value
                ).strip()

            # Ne pas garder ProductCode
            # dans ItemSpecifications.
            continue

        # ----------------------------------------------------
        # MANUFACTURER -> BRAND
        # ----------------------------------------------------

        if name in brand_names:

            if (
                value is not None
                and not item.get("brand")
            ):
                item["brand"] = str(
                    value
                ).strip()

            # Ne pas garder Manufacturer
            # dans ItemSpecifications.
            continue

        cleaned_specifications.append(
            specification
        )

    item["specifications"] = (
        cleaned_specifications
    )

    return item


# ============================================================
# EXTRACT PDF ITEMS WITH AI
# ============================================================

def extract_pdf_items_with_ai(
    rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Envoie les lignes extraites du PDF à OpenAI.

    Ensuite le résultat est normalisé pour garantir :

    ProductCode -> reference
    Manufacturer -> brand
    """

    if not rows:
        return []

    prompt = create_pdf_prompt(
        rows
    )

    response = client.responses.create(
        model=PDF_MODEL,
        input=prompt
    )

    response_text = (
        response.output_text
    )

    items = parse_pdf_ai_response(
        response_text
    )

    # --------------------------------------------------------
    # NORMALISATION FINALE
    # --------------------------------------------------------

    normalized_items = [
        normalize_pdf_item(item)
        for item in items
        if isinstance(item, dict)
    ]

    return normalized_items