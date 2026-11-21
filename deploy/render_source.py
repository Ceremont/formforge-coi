"""Render one PDF source page, with no OCR, persistence, or network access."""

import math
import resource
import sys


def main():
    source, target, page, max_pages, memory = sys.argv[1:]
    resource.setrlimit(resource.RLIMIT_CPU, (10, 11))
    if sys.platform.startswith("linux"):
        limit = int(memory) * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    import pypdfium2 as pdfium

    with pdfium.PdfDocument(source) as pdf:
        if len(pdf) > int(max_pages) or not 1 <= int(page) <= len(pdf):
            raise ValueError("page_limit")
        item = pdf[int(page) - 1]
        try:
            width, height = item.get_size()
            if not math.isfinite(width * height) or min(width, height) <= 0:
                raise ValueError("invalid_page")
            scale = min(1.8, 1700 / width, 2200 / height, math.sqrt(4_000_000 / (width * height)))
            bitmap = item.render(scale=scale)
            try:
                image = bitmap.to_pil().convert("RGB")
                try:
                    image.save(target, format="PNG")
                finally:
                    image.close()
            finally:
                bitmap.close()
        finally:
            item.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(2)
