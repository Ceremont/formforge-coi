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


def raster_dotted_lines(image):
    """Regular small-dot runs, not arbitrary horizontal text density."""
    import statistics
    from PIL import Image, ImageOps

    gray = ImageOps.grayscale(image)
    ratio = min(1, 1400 / gray.width)
    if ratio < 1:
        gray = gray.resize((int(gray.width * ratio), int(gray.height * ratio)), Image.Resampling.BOX)
    data = gray.point(lambda p: 0 if p < 150 else 255).tobytes()
    found = []
    for y in range(0, gray.height, 2):
        runs = [m.span() for m in re.finditer(b"\x00+", data[y * gray.width : (y + 1) * gray.width])]
        group = []
        for start, end in runs + [(gray.width + 20, gray.width + 40)]:
            if end - start > 6 or group and start - group[-1][1] > 14:
                if len(group) >= 9 and group[-1][1] - group[0][0] > 65:
                    pitch = [b[0] - a[0] for a, b in zip(group, group[1:])]
                    median = statistics.median(pitch)
                    if median >= 5 and statistics.pstdev(pitch) / median < 0.3:
                        box = (group[0][0] / ratio, y / ratio, group[-1][1] / ratio, (y + 2) / ratio)
                        if not any(abs(box[1] - b[1]) < 5 and abs(box[0] - b[0]) < 12 for b in found):
                            found.append(box)
                group = []
            if end - start <= 6:
                group.append((start, end))
        if len(found) > 500:
            break
    return found
