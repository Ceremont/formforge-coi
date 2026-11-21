"""Self-authored, minimal CFB/Word97 text fixture. Not used by runtime."""

import struct


def document_bytes(text):
    encoded = text.encode("utf-16le")
    if len(encoded) > 3000:
        raise ValueError("Synthetic fixture text is too long")
    header = bytearray(512)
    header[:8] = bytes.fromhex("d0cf11e0a1b11ae1")
    struct.pack_into("<HHHHH", header, 24, 0x3E, 3, 0xFFFE, 9, 6)
    struct.pack_into("<IIIIIIIII", header, 40, 0, 1, 0, 0, 4096, 0xFFFFFFFE, 0, 0xFFFFFFFE, 0)
    struct.pack_into("<109I", header, 76, 17, *([0xFFFFFFFF] * 108))
    directory = bytearray(512)

    def entry(i, name, kind, start, size, child=0xFFFFFFFF, right=0xFFFFFFFF):
        offset = i * 128
        label = (name + "\x00").encode("utf-16le")
        directory[offset : offset + len(label)] = label
        struct.pack_into("<HBBIII", directory, offset + 64, len(label), kind, 1, 0xFFFFFFFF, right, child)
        struct.pack_into("<IQ", directory, offset + 116, start, size)

    entry(0, "Root Entry", 5, 0xFFFFFFFE, 0, child=1)
    entry(1, "WordDocument", 2, 1, 4096, right=2)
    entry(2, "1Table", 2, 9, 4096)
    word, table = bytearray(4096), bytearray(4096)
    struct.pack_into("<HH", word, 0, 0xA5EC, 0xC1)
    struct.pack_into("<H", word, 10, 0x1200)
    struct.pack_into("<H", word, 12, 0xBF)
    struct.pack_into("<H", word, 32, 14)
    struct.pack_into("<H", word, 62, 22)
    struct.pack_into("<I", word, 64, 4096)
    struct.pack_into("<I", word, 76, len(encoded) // 2)
    struct.pack_into("<H", word, 152, 93)
    struct.pack_into("<II", word, 418, 0, 21)
    word[1024 : 1024 + len(encoded)] = encoded
    table[:21] = b"\x02" + struct.pack("<IIIHIH", 16, 0, len(encoded) // 2, 0, 1024, 0)
    fat = [0xFFFFFFFF] * 128
    fat[0] = 0xFFFFFFFE
    for first in [1, 9]:
        for i in range(first, first + 8):
            fat[i] = i + 1 if i < first + 7 else 0xFFFFFFFE
    fat[17] = 0xFFFFFFFD
    return bytes(header + directory + word + table + struct.pack("<128I", *fat))
