import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field


# Loads the environment variables contained in the .env file.
load_dotenv()


class Specification(BaseModel):
    """
    A technical specification belonging to an item.

    Example:
        name = "Voltage"
        value = "220"
        unit = "V"
    """

    name: str = Field(
        description="Clear name of the technical specification."
    )

    value: str = Field(
        description="Value of the specification."
    )

    unit: str | None = Field(
        default=None,
        description="Measurement unit, if one exists."
    )


class ExtractedItem(BaseModel):
    """
    Structure of an item extracted from the BOQ.
    """

    item_number: str | None = Field(
        default=None,
        description="Item number, code, or reference in the BOQ."
    )

    description: str = Field(
        description=(
            "Main and clear name of the item without losing "
            "important information."
        )
    )

    quantity: float | None = Field(
        default=None,
        description="Requested quantity."
    )

    unit: str | None = Field(
        default=None,
        description=(
            "Quantity unit, for example PCS, M, MR, KG, SET, or LOT."
        )
    )

    item_type: str | None = Field(
        default=None,
        description=(
            "General category of the item, for example Cable, "
            "Lighting, Motor, Breaker, Pipe, or Mechanical Equipment."
        )
    )

    specifications: list[Specification] = Field(
        default_factory=list,
        description="All technical specifications related to the item."
    )


class ExtractedBOQ(BaseModel):
    """
    Complete result returned by the AI.
    """

    items: list[ExtractedItem] = Field(default_factory=list)


SYSTEM_INSTRUCTIONS = """
You are an expert in reading BOQs, technical quotations, and material lists.

BOQ means Bill of Quantities.

Your task is to analyze data coming from an Excel file and extract only
the real items that must be purchased, supplied, installed, or quoted.

For each item, return:

1. item_number:
   The item number, code, or reference if it exists.

2. description:
   The main name of the item.

3. quantity:
   The requested quantity as a numeric value.

4. unit:
   The quantity unit, for example:
   PCS, EA, M, MR, KG, SET, LOT, L, M2, or M3.

5. item_type:
   A general and understandable category, for example:
   Cable, Lighting, Motor, Breaker, Panel, Pipe, Valve,
   Mechanical Equipment, or Electrical Equipment.

6. specifications:
   All technical specifications related to the item.

Examples of possible specifications:

- Voltage: 220 V
- Power: 200 W
- Current: 20 A
- Frequency: 50 Hz
- NumberOfPhases: 3
- Speed: 1500 RPM
- CrossSection: 25 mm²
- NumberOfCores: 4
- Diameter: 50 mm
- Length: 2 m
- Width: 500 mm
- Height: 800 mm
- Material: Copper
- Insulation: XLPE
- ProtectionRating: IP65
- BreakingCapacity: 10 kA
- Pressure: 10 bar
- ColorTemperature: 4000 K
- Brand: Schneider
- Model: ABC123
- Height: 180 cm

Important rules:

- Never invent information that is not present.
- Do not create a specification with an unknown value.
- A quantity unit such as PCS or M must be placed in "unit".
- A technical unit such as V, W, A, mm², or Hz must be placed
  in the related specification.
- Preserve value ranges such as 220-240 V.
- Preserve values such as 0.6/1 kV or 4x25 mm².
- For 4x25 mm², you may extract:
    NumberOfCores = 4
    CrossSection = 25 mm²
- IP65 is a ProtectionRating with the value IP65 and no unit.
- Section titles and empty rows are not items.
- Merge information from multiple columns when it clearly belongs
  to the same item.
- Each item must appear only once.
- Do not add any text outside the requested structure.
"""


def get_openai_client() -> OpenAI:
    """
    Creates the OpenAI client using the key stored
    in the OPENAI_API_KEY environment variable.
    """

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "The OpenAI API key is missing. "
            "Create a .env file and add: "
            "OPENAI_API_KEY=your_real_key"
        )

    return OpenAI(api_key=api_key)


def convert_chunk_to_text(chunk: Any) -> str:
    """
    Converts the chunk received from excel_reader.py into JSON text.

    The chunk may be a list, dictionary, or string.
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

    except (TypeError, ValueError):
        return str(chunk)


def extract_items_with_ai(
    chunk: Any
) -> list[dict[str, Any]]:
    """
    Sends an Excel chunk to OpenAI and returns the extracted items
    as a list of dictionaries.

    This structure is directly compatible with main.py.
    """

    chunk_text = convert_chunk_to_text(chunk)

    if not chunk_text:
        return []

    client = get_openai_client()

    try:
        response = client.responses.parse(
            model="gpt-4.1-mini",
            instructions=SYSTEM_INSTRUCTIONS,
            input=(
                "Analyze the following Excel data and extract all "
                "real BOQ items.\n\n"
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
            "An error occurred while analyzing the BOQ with OpenAI: "
            f"{error}"
        ) from error