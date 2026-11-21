"""Tile oversized page strips using nearby whitespace; no source content omitted."""

from PIL import Image, ImageOps


def tiles(source, budget):
    width, height = source.size
    if width > budget:
        from .errors import DocumentError

        raise DocumentError("Szerokość obrazu przekracza budżet OCR.", 413, "pixel_limit")
    step = max(1, min(int(width * 1.5), budget // width))
    top = 0
    while top < height:
        bottom = min(height, top + step)
        if bottom < height:
            lo = max(top + step // 2, bottom - step // 8)
            hi = min(height, bottom + step // 8, top + budget // width)
            with source.crop((0, lo, width, hi)) as strip:
                gray = ImageOps.grayscale(strip).resize((1, hi - lo), Image.Resampling.BOX)
                values = list(gray.get_flattened_data())
                # Prefer a whitespace row close to the nominal page boundary.
                candidates = [(abs(lo + i - bottom), lo + i) for i, v in enumerate(values) if v >= 253]
                if candidates:
                    bottom = min(candidates)[1]
        yield (0, top, width, bottom)
        top = bottom
