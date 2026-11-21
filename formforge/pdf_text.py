"""Recover reading lines from character geometry instead of PDF object order."""

import statistics


def lines(textpage, height):
    count = min(textpage.count_chars(), 200000)
    glyphs = []
    for i in range(count):
        char = textpage.get_text_range(i, 1)
        if char in "\r\n" or not char:
            continue
        try:
            left, bottom, right, top = textpage.get_charbox(i, loose=True)
        except Exception:
            continue
        if right <= left or top <= bottom:
            continue
        glyphs.append((height - top, left, right, height - bottom, char))
    if not glyphs:
        return
    median = statistics.median(g[3] - g[0] for g in glyphs)
    rows = []
    for glyph in sorted(glyphs, key=lambda g: ((g[0] + g[3]) / 2, g[1])):
        center = (glyph[0] + glyph[3]) / 2
        row = next((r for r in reversed(rows[-4:]) if abs(center - r[0]) < max(2, median * 0.42)), None)
        if row is None:
            rows.append([center, [glyph]])
        else:
            row[1].append(glyph)
    for _, row in rows:
        row.sort(key=lambda g: g[1])
        parts = []
        segment = []
        previous = None
        for glyph in row:
            gap = glyph[1] - previous[2] if previous else 0
            if previous and gap > max(24, median * 3):
                if segment:
                    parts.append(segment)
                segment = []
            segment.append(glyph)
            previous = glyph
        if segment:
            parts.append(segment)
        for segment in parts:
            content = []
            previous = None
            for glyph in segment:
                if previous and glyph[1] - previous[2] > max(1.3, median * 0.22):
                    content.append(" ")
                content.append(glyph[4])
                previous = glyph
            yield "".join(content), (min(g[1] for g in segment), min(g[0] for g in segment), max(g[2] for g in segment), max(g[3] for g in segment))
