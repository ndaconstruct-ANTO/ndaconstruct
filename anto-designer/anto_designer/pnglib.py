"""Lecture/écriture PNG en bibliothèque standard (sans Pillow).

Permet au moteur de calques de fonctionner et d'être testé hors-ligne, même
sans Pillow installé. Si Pillow est présent, le moteur l'utilise (plus rapide).

Supporte en lecture : 8 bits, RGB / RGBA / niveaux de gris (+alpha), non
entrelacé. Tout est normalisé en RGBA. Écriture : RGBA 8 bits.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def read_rgba(path: Path):
    """Décode un PNG (chemin) et retourne (width, height, bytearray RGBA)."""
    return read_rgba_bytes(Path(path).read_bytes())


def read_size(path: Path):
    """Lit uniquement les dimensions (largeur, hauteur) via l'en-tête IHDR."""
    raw = Path(path).read_bytes()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Fichier non-PNG")
    # IHDR commence à l'octet 16 : width(4) height(4)
    w, h = struct.unpack(">II", raw[16:24])
    return w, h


def read_rgba_bytes(raw: bytes):
    """Décode des octets PNG et retourne (width, height, bytearray RGBA)."""
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Fichier non-PNG")
    pos = 8
    w = h = depth = ctype = interlace = None
    idat = bytearray()
    while pos < len(raw):
        length = struct.unpack(">I", raw[pos:pos + 4])[0]
        tag = raw[pos + 4:pos + 8]
        data = raw[pos + 8:pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", data)
        elif tag == b"IDAT":
            idat += data
        elif tag == b"IEND":
            break

    if depth != 8 or interlace != 0 or ctype not in (0, 2, 4, 6):
        raise ValueError(f"PNG non supporté (depth={depth}, type={ctype}, il={interlace})")

    src_ch = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    stride = w * src_ch
    dec = zlib.decompress(bytes(idat))

    rows = bytearray(stride * h)
    prev = bytearray(stride)
    s = 0
    for y in range(h):
        ft = dec[s]; s += 1
        line = bytearray(dec[s:s + stride]); s += stride
        if ft == 1:
            for i in range(src_ch, stride):
                line[i] = (line[i] + line[i - src_ch]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                a = line[i - src_ch] if i >= src_ch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = line[i - src_ch] if i >= src_ch else 0
                c = prev[i - src_ch] if i >= src_ch else 0
                line[i] = (line[i] + _paeth(a, prev[i], c)) & 0xFF
        rows[y * stride:(y + 1) * stride] = line
        prev = line

    # Normalisation -> RGBA
    out = bytearray(w * h * 4)
    for i in range(w * h):
        o = i * 4
        si = i * src_ch
        if ctype == 6:      # RGBA
            out[o:o + 4] = rows[si:si + 4]
        elif ctype == 2:    # RGB
            out[o] = rows[si]; out[o + 1] = rows[si + 1]
            out[o + 2] = rows[si + 2]; out[o + 3] = 255
        elif ctype == 0:    # Gray
            g = rows[si]
            out[o] = out[o + 1] = out[o + 2] = g; out[o + 3] = 255
        else:               # Gray + alpha
            g = rows[si]
            out[o] = out[o + 1] = out[o + 2] = g; out[o + 3] = rows[si + 1]
    return w, h, out


def write_rgba(path: Path, w: int, h: int, rgba: bytearray) -> None:
    """Écrit un PNG RGBA 8 bits."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    stride = w * 4
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw.extend(rgba[y * stride:(y + 1) * stride])
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
           + chunk(b"IEND", b""))
    Path(path).write_bytes(png)


def new_canvas(w: int, h: int, rgba=(255, 255, 255, 0)) -> bytearray:
    """Crée un canevas RGBA uni (transparent par défaut)."""
    buf = bytearray(w * h * 4)
    r, g, b, a = rgba
    for i in range(0, len(buf), 4):
        buf[i] = r; buf[i + 1] = g; buf[i + 2] = b; buf[i + 3] = a
    return buf


def alpha_over(dst: bytearray, src: bytearray) -> None:
    """Compose src au-dessus de dst (alpha over standard), en place. Même taille."""
    for i in range(0, len(dst), 4):
        sa = src[i + 3]
        if sa == 0:
            continue
        if sa == 255:
            dst[i:i + 4] = src[i:i + 4]
            continue
        ia = 255 - sa
        da = dst[i + 3]
        out_a = sa + da * ia // 255
        if out_a == 0:
            continue
        for c in range(3):
            dst[i + c] = (src[i + c] * sa + dst[i + c] * da * ia // 255) // out_a
        dst[i + 3] = out_a
