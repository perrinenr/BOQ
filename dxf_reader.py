from pathlib import Path
from typing import Any

import ezdxf


SUPPORTED_TEXT_TYPES = {
    "TEXT",
    "MTEXT",
    "ATTRIB",
    "ATTDEF"
}


def read_dxf_file(
    dxf_file: Path
) -> list[dict[str, Any]]:
    """
    Lit un fichier DXF et extrait ses entités principales.
    """

    if not dxf_file.exists():
        raise FileNotFoundError(
            f"DXF file not found: {dxf_file}"
        )

    try:
        document = ezdxf.readfile(dxf_file)

    except ezdxf.DXFStructureError as error:
        raise ValueError(
            f"Invalid or corrupted DXF file: {error}"
        ) from error

    modelspace = document.modelspace()

    entities: list[dict[str, Any]] = []

    for entity in modelspace:
        entity_type = entity.dxftype()

        data: dict[str, Any] = {
            "entity_type": entity_type,
            "layer": entity.dxf.get("layer", None)
        }

        if entity_type == "TEXT":
            data["text"] = entity.dxf.text

            insert = entity.dxf.insert

            data["x"] = insert.x
            data["y"] = insert.y
            data["z"] = insert.z

        elif entity_type == "MTEXT":
            data["text"] = entity.plain_text()

            insert = entity.dxf.insert

            data["x"] = insert.x
            data["y"] = insert.y
            data["z"] = insert.z

        elif entity_type == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end

            data["start_x"] = start.x
            data["start_y"] = start.y
            data["start_z"] = start.z

            data["end_x"] = end.x
            data["end_y"] = end.y
            data["end_z"] = end.z

        elif entity_type == "CIRCLE":
            center = entity.dxf.center

            data["center_x"] = center.x
            data["center_y"] = center.y
            data["center_z"] = center.z
            data["radius"] = entity.dxf.radius

        elif entity_type == "ARC":
            center = entity.dxf.center

            data["center_x"] = center.x
            data["center_y"] = center.y
            data["center_z"] = center.z
            data["radius"] = entity.dxf.radius
            data["start_angle"] = entity.dxf.start_angle
            data["end_angle"] = entity.dxf.end_angle

        elif entity_type == "INSERT":
            insert = entity.dxf.insert

            data["block_name"] = entity.dxf.name
            data["x"] = insert.x
            data["y"] = insert.y
            data["z"] = insert.z

            attributes = {}

            for attribute in entity.attribs:
                attributes[attribute.dxf.tag] = (
                    attribute.dxf.text
                )

            data["attributes"] = attributes

        elif entity_type in {
            "LWPOLYLINE",
            "POLYLINE"
        }:
            points = []

            try:
                if entity_type == "LWPOLYLINE":
                    for point in entity.get_points():
                        points.append({
                            "x": point[0],
                            "y": point[1]
                        })
                else:
                    for vertex in entity.vertices:
                        location = vertex.dxf.location

                        points.append({
                            "x": location.x,
                            "y": location.y,
                            "z": location.z
                        })

            except Exception:
                points = []

            data["points"] = points

        else:
            # On garde au minimum le type et le layer.
            pass

        entities.append(data)

    return entities