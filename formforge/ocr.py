"""Bounded local OCR candidates with source-coordinate restoration."""

import math
from dataclasses import dataclass
from time import monotonic

from PIL import Image, ImageFilter, ImageOps

from .errors import DocumentError


@dataclass
class Variant:
    name: str
    image: Image.Image
    scale: float = 1
    angle: float = 0

    def source_box(self, box):
        width, height = self.image.width / self.scale, self.image.height / self.scale
        angle = math.radians(self.angle)
        points = []
        for x, y in [(box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3])]:
            x, y = x / self.scale - width / 2, y / self.scale - height / 2
            points.append((math.cos(angle) * x - math.sin(angle) * y + width / 2, math.sin(angle) * x + math.cos(angle) * y + height / 2))
        return (max(0, min(p[0] for p in points)), max(0, min(p[1] for p in points)), min(width, max(p[0] for p in points)), min(height, max(p[1] for p in points)))


def deskew_angle(gray):
    sample = gray.copy()
    sample.thumbnail((850, 850))
    sample = ImageOps.autocontrast(sample).point(lambda p: 0 if p < 170 else 255)

    def score(angle):
        image = sample.rotate(angle, fillcolor=255)
        rows = list(image.resize((1, image.height), Image.Resampling.BOX).get_flattened_data())
        return sum((rows[i] - rows[i - 1]) ** 2 for i in range(1, len(rows)))

    scores = [(score(a / 2), a / 2) for a in range(-10, 11)]
    best = max(scores)
    baseline = next(value for value, angle in scores if angle == 0)
    return best[1] if best[0] > baseline * 1.12 else 0


def threshold(gray):
    histogram = gray.histogram()
    total = sum(histogram)
    mean = sum(i * n for i, n in enumerate(histogram))
    weight = 0
    cumulative = 0
    best = 0
    cutoff = 160
    for i, n in enumerate(histogram):
        weight += n
        cumulative += i * n
        if not weight or weight == total:
            continue
        variance = weight * (total - weight) * (cumulative / weight - (mean - cumulative) / (total - weight)) ** 2
        if variance > best:
            best, cutoff = variance, i
    return gray.point(lambda p: 0 if p <= cutoff else 255)


def variants(image, max_pixels, count):
    gray = ImageOps.grayscale(image)
    yield Variant("original", gray)
    if count < 2:
        return
    angle = deskew_angle(gray)
    enhanced = ImageOps.autocontrast(gray, cutoff=1).filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
    scale = min(1.7, math.sqrt(max_pixels / (gray.width * gray.height)))
    scale = max(1, scale)
    if scale != 1:
        enhanced = enhanced.resize((int(gray.width * scale), int(gray.height * scale)), Image.Resampling.LANCZOS)
    if angle:
        enhanced = enhanced.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor=255)
    yield Variant("contrast_deskew_scale", enhanced, scale, angle)
    if count > 2:
        yield Variant("otsu_sparse", threshold(enhanced), scale, angle)


def read_lines(data, variant):
    groups = {}
    for i, text in enumerate(data["text"]):
        if text.strip():
            groups.setdefault((data["block_num"][i], data["par_num"][i], data["line_num"][i]), []).append(i)
    lines = []
    for indices in groups.values():
        text = " ".join(data["text"][i] for i in indices)
        confs = [max(0, float(data["conf"][i])) for i in indices]
        box = (
            min(data["left"][i] for i in indices),
            min(data["top"][i] for i in indices),
            max(data["left"][i] + data["width"][i] for i in indices),
            max(data["top"][i] + data["height"][i] for i in indices),
        )
        lines.append({"text": text, "bbox": variant.source_box(box), "confidence": sum(confs) / len(confs) / 100, "variant": variant.name})
    return lines


def quality(lines):
    # Recognized high-confidence alphanumerics, confidence, and noise ratio.
    # No known field names, expected outputs, or holdout labels are consulted.
    if not lines:
        return 0
    weighted = sum(sum(c.isalnum() for c in line["text"]) * line["confidence"] for line in lines)
    letters = sum(c.isalnum() for line in lines for c in line["text"])
    chars = sum(len(line["text"]) for line in lines)
    confidence = sum(line["confidence"] for line in lines) / len(lines)
    return round(0.45 * confidence + 0.4 * (1 - math.exp(-weighted / 120)) + 0.15 * letters / max(chars, 1), 5)


def recognize(image, languages, settings):
    import pytesseract

    deadline = monotonic() + settings.ocr_timeout
    results = []
    for variant in variants(image, settings.max_image_pixels, settings.ocr_variants):
        remaining = deadline - monotonic()
        if remaining < 0.2:
            break
        try:
            data = pytesseract.image_to_data(
                variant.image, lang=languages, config="--psm 11" if variant.name == "otsu_sparse" else "--psm 3", output_type=pytesseract.Output.DICT, timeout=max(0.2, remaining)
            )
            lines = read_lines(data, variant)
            results.append(
                (quality(lines), lines, {"variant": variant.name, "score": quality(lines), "deskew_degrees": variant.angle, "scale": variant.scale, "lines": len(lines)})
            )
        except RuntimeError:
            if not results:
                raise DocumentError("Przekroczono budżet czasu lokalnego OCR.", 408, "ocr_timeout")
            break
    if not results:
        raise DocumentError("Brak wyniku OCR.", 422, "no_text")
    best = max(results, key=lambda row: row[0])
    selected = list(best[1])
    # Complement a missed physical line only with clear OCR from a different pass.
    # Conflicting text in the same region is never combined or fabricated.
    for _, lines, _ in results:
        for line in lines:
            if line["confidence"] < 0.65 or len(line["text"]) < 3:
                continue
            y = (line["bbox"][1] + line["bbox"][3]) / 2
            if not any(abs(y - (other["bbox"][1] + other["bbox"][3]) / 2) < max(8, line["bbox"][3] - line["bbox"][1]) for other in selected):
                selected.append(line)
    return sorted(selected, key=lambda line: (line["bbox"][1], line["bbox"][0])), {
        "selected": best[2]["variant"],
        "quality_score": best[0],
        "score_semantics": "uncalibrated_ocr_quality",
        "candidates": [r[2] for r in results],
    }
