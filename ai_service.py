import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

def load_environment() -> Path:
    """
    Charge le fichier .env.

    En développement :
        C:\\Users\\perri\\BOQ\\.env

    Avec PyInstaller :
        BOQ_Importer.exe
        .env
        _internal/

    Le .env doit donc être placé à côté du fichier .exe.
    """

    if getattr(sys, "frozen", False):
        # Application compilée avec PyInstaller.
        base_path = Path(sys.executable).resolve().parent
    else:
        # Exécution normale avec Python.
        base_path = Path(__file__).resolve().parent

    env_path = base_path / ".env"

    if env_path.exists():
        load_dotenv(
            dotenv_path=env_path,
            override=False
        )
    else:
        # Permet aussi de récupérer des variables
        # définies directement dans Windows.
        load_dotenv(
            override=False
        )

    return env_path


ENV_PATH = load_environment()


# ============================================================
# PYDANTIC MODELS
# ============================================================

class Specification(BaseModel):
    """
    A technical specification belonging to an item.
    """

    name: str = Field(
        description=(
            "Clear name of the technical specification."
        )
    )

    value: str = Field(
        description=(
            "Value of the specification."
        )
    )

    unit: str | None = Field(
        default=None,
        description=(
            "Measurement unit, if one exists."
        )
    )


class ExtractedItem(BaseModel):
    """
    Generic BOQ item.

    The item can be anything:
    lighting fixture, cable, breaker, motor,
    valve, pump, panel, pipe, equipment, etc.
    """

    item: str | None = Field(
        default=None,
        description=(
            "Item number, item code, type code or row "
            "reference, for example C1, D4, L01, "
            "CAB-01, 1.1.4, etc."
        )
    )

    brand: str | None = Field(
        default=None,
        description=(
            "Manufacturer or brand if explicitly present."
        )
    )

    reference: str | None = Field(
        default=None,
        description=(
            "Manufacturer reference, product code, model "
            "or catalogue reference if explicitly present."
        )
    )

    item_type: str | None = Field(
        default=None,
        description=(
            "General category of the item, for example "
            "Lighting Fixture, Cable, Breaker, Panel, "
            "Motor, Pump, Valve, Pipe, Mechanical "
            "Equipment, Electrical Equipment, etc."
        )
    )

    description: str = Field(
        description=(
            "Complete and clear description of the item "
            "without losing important technical information."
        )
    )

    quantity: float | None = Field(
        default=None,
        description=(
            "Requested quantity if explicitly present."
        )
    )

    unit: str | None = Field(
        default=None,
        description=(
            "Quantity unit, for example PCS, EA, NR, M, "
            "MR, KG, SET, LOT, L, M2 or M3."
        )
    )

    unit_price: float | None = Field(
        default=None,
        description=(
            "Unit price if explicitly present in the source."
        )
    )

    total: float | None = Field(
        default=None,
        description=(
            "Line total if explicitly present in the source. "
            "Do not calculate it when it is absent."
        )
    )

    specifications: list[Specification] = Field(
        default_factory=list,
        description=(
            "All technical specifications related to the item."
        )
    )


class ExtractedBOQ(BaseModel):
    """
    Complete structured result returned by the AI.
    """

    items: list[ExtractedItem] = Field(
        default_factory=list
    )


# ============================================================
# OPENAI INSTRUCTIONS
# ============================================================

SYSTEM_INSTRUCTIONS = """
You are an expert in reading BOQs, technical quotations,
schedules, material lists, supplier offers and technical
documents.

The input may come from an Excel/XLSX/XLS file or from
text/tables that were extracted from a PDF.

Your job is GENERIC.

An item can be anything:
- lighting fixture
- cable
- breaker
- panel
- motor
- pump
- valve
- pipe
- electrical equipment
- mechanical equipment
- accessory
- material
- product

Do not assume that every file is a lighting file.

Extract only real items that must be purchased, supplied,
installed, quoted, proposed or listed as products/materials.


For every item return these fields:


1. item

Item number, item code, type code or BOQ row reference
if present.

Examples:

C1
D4
L01
CAB-01
1.1.4


2. brand

Manufacturer or brand only if explicitly present.


3. reference

Product code, catalogue reference, manufacturer reference
or model only if explicitly present.


4. item_type

General understandable category of the item.

Examples:

Lighting Fixture
Cable
Breaker
Panel
Motor
Pump
Valve
Pipe
Electrical Equipment
Mechanical Equipment


5. description

Complete and clear item description.

Keep important technical information from the source.


6. quantity

Numeric requested quantity if explicitly present.


7. unit

Quantity unit such as:

PCS
EA
NR
M
MR
KG
SET
LOT
L
M2
M3


8. unit_price

Unit price only when explicitly present.


9. total

Line total only when explicitly present.

Do NOT calculate a total when it is not present
in the source.


10. specifications

Technical characteristics represented as:

name
value
unit


Possible technical specifications include,
but are not limited to:

Voltage: 220 V
Power: 30 W
Current: 63 A
Frequency: 50 Hz
NumberOfPhases: 3
NumberOfPoles: 4
NumberOfCores: 4
CrossSection: 25 mm²
Speed: 1500 RPM
Diameter: 50 mm
Length: 2 m
Width: 500 mm
Height: 800 mm
LumenOutput: 800 lm
ColorTemperature: 3000 K
BeamAngle: 60 degree
ProtectionRating: IP65
Material: Copper
Insulation: XLPE
BreakingCapacity: 10 kA
Pressure: 10 bar
EmergencyBackup: 3 h
MountingType: Ceiling recessed
Location: Bedroom


IMPORTANT RULES:


- Never invent information that is not explicitly present.

- Missing values must remain null.

- Do not guess missing quantities.

- Do not guess missing units.

- Do not guess missing brands.

- Do not guess missing references.

- Do not create a specification with an unknown value.

- Brand belongs in the top-level field "brand",
  not in specifications.

- Product/model/catalogue code belongs in
  "reference", not in specifications.

- Item/type/BOQ code belongs in "item".

- A quantity unit such as PCS, NR, M or KG
  belongs in "unit".

- A technical unit such as V, W, A, mm²,
  lm, K or Hz belongs to its specification.

- IP65 should be represented as:
  ProtectionRating = IP65
  with no measurement unit.

- Preserve ranges such as:
  220-240 V

- Preserve compound values such as:
  0.6/1 kV
  4x25 mm²

- For 4x25 mm² you may extract:
  NumberOfCores = 4
  CrossSection = 25 mm²

- Section titles are not items.

- Headers are not items.

- Subtotals are not items.

- Grand totals are not items.

- Empty rows are not items.

- Page titles are not items.

- Document titles are not items.

- If a row only continues the description or
  specifications of the previous item, merge that
  information with the same item.

- Do not create a second item from a continuation row.

- If Brand or Reference is shown once and clearly
  applies to continuation information, keep it with
  the corresponding item.

- Each real item must appear only once.

- Preserve item identifiers exactly.

For example:

C1 must stay C1.
UU1 must stay UU1.
UU1E must stay UU1E.
F1 must stay F1.
F2E must stay F2E.

Do not normalize or rename item codes.

- The order of columns can vary from one document
  to another.

For example, a PDF may contain:

Type | Brand | Product Code | Description | Image | Location

or:

Item | Brand | Ref | Description

or another technical table structure.

Use the meaning of the data rather than assuming
a fixed column position.

- Ignore empty image cells or graphical placeholders.

- If Location exists, store it as a technical
  specification named "Location".

- Do not add commentary outside the structured result.
"""


# ============================================================
# OPENAI CLIENT
# ============================================================

def get_openai_client() -> OpenAI:
    """
    Creates the OpenAI client using OPENAI_API_KEY.

    The key can come from:
    - the .env file
    - a Windows environment variable
    """

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "The OpenAI API key is missing.\n\n"
            f"Expected .env location:\n{ENV_PATH}\n\n"
            "Add this line to the .env file:\n"
            "OPENAI_API_KEY=your_real_key"
        )

    return OpenAI(
        api_key=api_key
    )


# ============================================================
# DATA CONVERSION
# ============================================================

def convert_chunk_to_text(
    chunk: Any
) -> str:
    """
    Converts data received from an Excel or PDF reader
    into text suitable for the AI.

    Supported input:
    - string
    - list
    - dictionary
    - other serializable structures
    """

    if chunk is None:
        return ""

    if isinstance(chunk, str):
        return chunk.strip()

    try:
        return json.dumps(
            chunk,
            ensure_ascii=False,
            indent=2,
            default=str
        )

    except (
        TypeError,
        ValueError
    ):
        return str(chunk)


# ============================================================
# AI EXTRACTION
# ============================================================

def extract_items_with_ai(
    chunk: Any
) -> list[dict[str, Any]]:
    """
    Sends an Excel/PDF extracted chunk to OpenAI
    and returns generic BOQ items.

    Returned keys:

    item
    brand
    reference
    item_type
    description
    quantity
    unit
    unit_price
    total
    specifications

    DWG processing is intentionally not handled here.
    """

    chunk_text = convert_chunk_to_text(
        chunk
    )

    if not chunk_text:
        return []

    client = get_openai_client()

    try:

        response = client.responses.parse(
            model="gpt-4.1-mini",

            instructions=SYSTEM_INSTRUCTIONS,

            input=(
                "Analyze the following BOQ / technical "
                "document data.\n\n"
                "Extract every real item using the required "
                "generic structure.\n\n"
                "The source can have any table structure. "
                "Do not assume fixed column positions.\n\n"
                f"{chunk_text}"
            ),

            text_format=ExtractedBOQ
        )

        extracted_boq = response.output_parsed

        if extracted_boq is None:
            raise ValueError(
                "The AI did not return a structured result."
            )

        return [
            item.model_dump()
            for item in extracted_boq.items
        ]

    except Exception as error:

        raise RuntimeError(
            "An error occurred while analyzing "
            "the BOQ with OpenAI: "
            f"{error}"
        ) from error