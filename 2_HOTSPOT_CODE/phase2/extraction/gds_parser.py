"""Minimal, dependency-free GDSII stream parser.

Only supports what Phase 2 needs: reading BOUNDARY/BOX polygons (and
flattening SREF/AREF placements) into world-coordinate polygons grouped by
(layer, datatype). No third-party GDSII library (gdstk/gdspy) is available
in the WSL environment, so this reads the binary GDSII stream format
directly per the standard record layout.
"""

from pathlib import Path
from struct import unpack

RECORD_HEADER_SIZE = 4

HEADER = 0x00
BGNLIB = 0x01
UNITS = 0x03
ENDLIB = 0x04
BGNSTR = 0x05
STRNAME = 0x06
ENDSTR = 0x07
BOUNDARY = 0x08
PATH = 0x09
SREF = 0x0A
AREF = 0x0B
TEXT = 0x0C
LAYER = 0x0D
DATATYPE = 0x0E
WIDTH = 0x0F
XY = 0x10
ENDEL = 0x11
SNAME = 0x12
COLROW = 0x13
STRANS = 0x1A
MAG = 0x1B
ANGLE = 0x1C
BOX = 0x2D
BOXTYPE = 0x2E

DATA_NONE = 0x00
DATA_BITARRAY = 0x01
DATA_INT2 = 0x02
DATA_INT4 = 0x03
DATA_REAL8 = 0x05
DATA_STRING = 0x06


def decode_real8(raw):
    """Decode a GDSII 8-byte "Excess-64" floating point number."""
    (value,) = unpack(">Q", raw)
    sign = -1.0 if (value >> 63) & 1 else 1.0
    exponent = (value >> 56) & 0x7F
    mantissa = value & 0x00FFFFFFFFFFFFFF
    if mantissa == 0:
        return 0.0
    return sign * (mantissa / (1 << 56)) * (16.0 ** (exponent - 64))


def read_records(data):
    """Yield (record_type, data_type, payload_bytes) for every record."""
    offset = 0
    length_total = len(data)
    while offset < length_total:
        record_length, record_type, data_type = unpack(
            ">HBB", data[offset:offset + RECORD_HEADER_SIZE]
        )
        payload = data[offset + RECORD_HEADER_SIZE:offset + record_length]
        yield record_type, data_type, payload
        offset += record_length


def decode_payload(data_type, payload):
    if data_type == DATA_NONE:
        return None
    if data_type == DATA_INT2:
        count = len(payload) // 2
        return list(unpack(f">{count}h", payload))
    if data_type == DATA_INT4:
        count = len(payload) // 4
        return list(unpack(f">{count}i", payload))
    if data_type == DATA_REAL8:
        count = len(payload) // 8
        return [decode_real8(payload[i * 8:i * 8 + 8]) for i in range(count)]
    if data_type == DATA_STRING:
        return payload.rstrip(b"\x00").decode("ascii", errors="replace")
    return payload


def parse_gds(path):
    """Parse a GDSII file into a dict of structure name -> element list.

    Each element is a dict with keys: kind ("boundary"/"box"/"sref"/"aref"),
    layer, datatype, xy (list of (x, y) ints in database units), and for
    sref/aref: sname, angle, mag, xy (reference/array origin points).
    """
    data = Path(path).read_bytes()
    structures = {}
    units_per_micron = None

    current_structure = None
    current_element = None

    for record_type, data_type, payload in read_records(data):
        value = decode_payload(data_type, payload)

        if record_type == UNITS:
            # value = [db_units_per_user_unit, db_units_in_meters]
            units_per_micron = 1.0 / (value[1] / 1e-6)
        elif record_type == BGNSTR:
            current_structure = {"name": None, "elements": []}
        elif record_type == STRNAME:
            current_structure["name"] = value
        elif record_type == ENDSTR:
            structures[current_structure["name"]] = current_structure["elements"]
            current_structure = None
        elif record_type in (BOUNDARY, BOX, SREF, AREF, TEXT):
            kind = {
                BOUNDARY: "boundary",
                BOX: "box",
                SREF: "sref",
                AREF: "aref",
                TEXT: "text",
            }[record_type]
            current_element = {"kind": kind, "layer": None, "datatype": None}
        elif current_element is None:
            continue
        elif record_type == LAYER:
            current_element["layer"] = value[0]
        elif record_type == DATATYPE or record_type == BOXTYPE:
            current_element["datatype"] = value[0]
        elif record_type == SNAME:
            current_element["sname"] = value
        elif record_type == STRANS:
            current_element["mirror_x"] = bool(value[0] & 0x8000)
        elif record_type == ANGLE:
            current_element["angle"] = value[0]
        elif record_type == MAG:
            current_element["mag"] = value[0]
        elif record_type == COLROW:
            current_element["cols"] = value[0]
            current_element["rows"] = value[1]
        elif record_type == XY:
            points = [(value[i], value[i + 1]) for i in range(0, len(value), 2)]
            current_element["xy"] = points
        elif record_type == ENDEL:
            current_structure["elements"].append(current_element)
            current_element = None

    return structures, units_per_micron


def flatten_top_structure(structures, top_name, layers_of_interest):
    """Flatten one top structure into world-space polygons per layer.

    Only handles the transforms actually seen in SKY130 standard cells:
    translation, optional X mirroring, and 0/90/180/270 degree rotation.
    Returns {(layer, datatype): [polygon, ...]} with polygon = [(x, y), ...]
    in database units, plus the top structure's own boundary/box polygons.
    """
    import math

    result = {}

    def add_polygon(layer, datatype, points):
        if (layer, datatype) not in layers_of_interest:
            return
        result.setdefault((layer, datatype), []).append(points)

    def transform(points, origin, angle_deg, mirror_x, mag):
        angle = math.radians(angle_deg)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        transformed = []
        for x, y in points:
            if mirror_x:
                y = -y
            x, y = x * mag, y * mag
            rx = x * cos_a - y * sin_a
            ry = x * sin_a + y * cos_a
            transformed.append((rx + origin[0], ry + origin[1]))
        return transformed

    def visit(structure_name, origin, angle_deg, mirror_x, mag, depth):
        if depth > 10:
            raise ValueError("GDS reference nesting too deep; possible cycle")
        for element in structures[structure_name]:
            if element["kind"] in ("boundary", "box"):
                points = transform(
                    element["xy"], origin, angle_deg, mirror_x, mag
                )
                add_polygon(element["layer"], element["datatype"], points)
            elif element["kind"] == "sref":
                child_origin = transform(
                    [element["xy"][0]], origin, angle_deg, mirror_x, mag
                )[0]
                visit(
                    element["sname"],
                    child_origin,
                    element.get("angle", 0.0),
                    element.get("mirror_x", False),
                    element.get("mag", 1.0),
                    depth + 1,
                )
            elif element["kind"] == "aref":
                raise ValueError("AREF flattening not needed for single cells")

    visit(top_name, (0.0, 0.0), 0.0, False, 1.0, 0)
    return result


def polygon_bounds(polygons_by_layer):
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    for polygons in polygons_by_layer.values():
        for polygon in polygons:
            for x, y in polygon:
                min_x, max_x = min(min_x, x), max(max_x, x)
                min_y, max_y = min(min_y, y), max(max_y, y)
    return min_x, min_y, max_x, max_y
