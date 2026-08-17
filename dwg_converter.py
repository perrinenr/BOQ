import subprocess
from pathlib import Path


ODA_CONVERTER_PATH = Path(
    r"C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe"
)


def convert_dwg_to_dxf(dwg_file: Path) -> Path:
    """
    Convertit un fichier DWG en DXF avec ODA File Converter.
    """

    dwg_file = dwg_file.resolve()

    # Vérifier que le DWG existe.
    if not dwg_file.exists():
        raise FileNotFoundError(
            f"DWG file not found: {dwg_file}"
        )

    if not dwg_file.is_file():
        raise ValueError(
            f"The selected path is not a file: {dwg_file}"
        )

    if dwg_file.suffix.lower() != ".dwg":
        raise ValueError(
            "The input file must have a .dwg extension."
        )

    # Vérifier qu'ODA est installé.
    if not ODA_CONVERTER_PATH.exists():
        raise FileNotFoundError(
            "ODA File Converter was not found at: "
            f"{ODA_CONVERTER_PATH}"
        )

    input_folder = dwg_file.parent

    output_folder = input_folder / "converted_dxf"

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    print(f"ODA converter : {ODA_CONVERTER_PATH}")
    print(f"Input folder  : {input_folder}")
    print(f"Output folder : {output_folder}")
    print(f"Input file    : {dwg_file.name}")

    command = [
        str(ODA_CONVERTER_PATH),

        # 1. Quoted Input Folder
        str(input_folder),

        # 2. Quoted Output Folder
        str(output_folder),

        # 3. Output version
        "ACAD2018",

        # 4. Output file type
        "DXF",

        # 5. Recurse Input Folder: 0 = non
        "0",

        # 6. Audit each file: 1 = oui
        "1",

        # 7. Filtre facultatif
        dwg_file.name
    ]

    print("\nODA command:")

    for argument in command:
        print(f"  {argument}")

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False
    )

    if result.stdout:
        print("\nODA output:")
        print(result.stdout)

    if result.stderr:
        print("\nODA errors:")
        print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            "DWG to DXF conversion failed. "
            f"ODA return code: {result.returncode}"
        )

    expected_dxf_file = (
        output_folder / f"{dwg_file.stem}.dxf"
    )

    # Certains systèmes produisent une extension en majuscules.
    if not expected_dxf_file.exists():
        uppercase_dxf_file = (
            output_folder / f"{dwg_file.stem}.DXF"
        )

        if uppercase_dxf_file.exists():
            expected_dxf_file = uppercase_dxf_file

    if not expected_dxf_file.exists():
        created_dxf_files = list(
            output_folder.glob("*.dxf")
        ) + list(
            output_folder.glob("*.DXF")
        )

        matching_files = [
            file
            for file in created_dxf_files
            if file.stem.lower() == dwg_file.stem.lower()
        ]

        if matching_files:
            expected_dxf_file = matching_files[0]

    if not expected_dxf_file.exists():
        raise FileNotFoundError(
            "ODA finished, but the expected DXF file "
            f"was not found in: {output_folder}"
        )

    return expected_dxf_file