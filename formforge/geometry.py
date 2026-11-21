"""Conservative geometric primitives; no model or fixture lookups."""

import re


def pdf_regions(page, height):
    pending = []
    output = []
    move = None

    def point(x, y, matrix):
        a, b, c, d, e, f = matrix
        return (a * x + c * y + e, height - (b * x + d * y + f))

    def visit(operator, args, cm, tm):
        nonlocal move, pending
        if len(output) > 1500:
            return
        if operator == b"re":
            x, y, w, h = map(float, args[:4])
            corners = [point(x, y, cm), point(x + w, y + h, cm)]
            pending.append((min(p[0] for p in corners), min(p[1] for p in corners), max(p[0] for p in corners), max(p[1] for p in corners)))
        elif operator == b"m":
            move = point(float(args[0]), float(args[1]), cm)
        elif operator == b"l" and move:
            end = point(float(args[0]), float(args[1]), cm)
            if abs(end[1] - move[1]) < 2 and abs(end[0] - move[0]) > 45:
                pending.append((min(move[0], end[0]), min(move[1], end[1]), max(move[0], end[0]), max(move[1], end[1]) + 1))
            move = end
        elif operator in (b"S", b"s", b"B", b"b", b"f", b"f*"):
            for box in pending:
                w, h = box[2] - box[0], box[3] - box[1]
                if (w > 45 and h <= 100) or (8 < w < 28 and 8 < h < 28):
                    output.append(box)
            pending = []
            move = None
        elif operator == b"n":
            pending = []
            move = None

    page.extract_text(visitor_operand_before=visit)
    return output


def raster_lines(image):
    from PIL import Image, ImageOps

    gray = ImageOps.grayscale(image)
    ratio = min(1, 1400 / gray.width)
    if ratio < 1:
        gray = gray.resize((int(gray.width * ratio), int(gray.height * ratio)), Image.Resampling.BOX)
    data = gray.point(lambda p: 0 if p < 140 else 255).tobytes()
    boxes = []
    for y in range(0, gray.height, 2):
        for match in re.finditer(b"\x00{55,}", data[y * gray.width : (y + 1) * gray.width]):
            x, right = match.span()
            if right - x > gray.width * 0.92:
                continue
            box = (x / ratio, y / ratio, right / ratio, (y + 2) / ratio)
            if not any(abs(box[1] - old[1]) < 5 and abs(box[0] - old[0]) < 10 for old in boxes):
                boxes.append(box)
            if len(boxes) >= 500:
                return boxes
    return boxes
