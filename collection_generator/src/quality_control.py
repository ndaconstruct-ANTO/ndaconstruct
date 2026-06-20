"""Contrôle qualité automatique des combinaisons et des images générées.

- Contrôles LOGIQUES (toujours, même en simulation) : un seul objet, cohérence
  style/objet, pelage valide, etc.
- Contrôles IMAGE (uniquement si une image réelle existe) : format carré,
  résolution, fond blanc, personnage centré et non coupé. Décodage PNG via la
  bibliothèque standard (zlib), sans dépendance externe.

Statuts possibles : VALIDÉ, À CORRIGER, REFUSÉ.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from .combination_generator import Combination
from .utils import Config

VALID = "VALIDÉ"
REVIEW = "À CORRIGER"
REJECT = "REFUSÉ"

_MULTI_OBJECT_HINTS = (" and ", " plus ", "+", "two ", "double", "pair of weapons")


# --- Contrôles logiques ------------------------------------------------------
def check_logical(combo: Combination, config: Config) -> list:
    """Retourne une liste de (niveau, message) ; niveau = REJECT/REVIEW."""
    issues = []

    if combo.fur.code not in config.fur_by_code:
        issues.append((REJECT, f"Pelage inconnu : {combo.fur.code}"))

    obj = (combo.held_object or "").strip()
    if not obj or obj.lower() == "none":
        # Un style sans objet est toléré (la patte reste vide), mais signalé.
        issues.append((REVIEW, "Aucun objet tenu (patte vide) — vérifier l'intention"))
    else:
        low = obj.lower()
        if any(h in low for h in _MULTI_OBJECT_HINTS):
            issues.append((REJECT, f"Plusieurs objets potentiels détectés : '{obj}'"))

    if combo.held_object != combo.style.held_object:
        issues.append(
            (REJECT, "Objet tenu incohérent avec le style "
                     f"({combo.held_object!r} != {combo.style.held_object!r})")
        )

    return issues


# --- Décodage PNG (stdlib) ---------------------------------------------------
def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_png(path: Path):
    """Décode un PNG 8 bits (RGB/RGBA, non entrelacé). Retourne (w, h, channels, data)."""
    raw = Path(path).read_bytes()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Fichier non-PNG")
    pos = 8
    width = height = bit_depth = color_type = interlace = None
    idat = bytearray()
    while pos < len(raw):
        length = struct.unpack(">I", raw[pos:pos + 4])[0]
        ctype = raw[pos + 4:pos + 8]
        data = raw[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(
                ">IIBBBBB", data
            )
        elif ctype == b"IDAT":
            idat += data
        elif ctype == b"IEND":
            break

    if bit_depth != 8 or interlace != 0 or color_type not in (2, 6):
        raise ValueError(
            f"PNG non supporté par le décodeur stdlib (depth={bit_depth}, "
            f"color_type={color_type}, interlace={interlace})"
        )

    channels = 3 if color_type == 2 else 4
    stride = width * channels
    decompressed = zlib.decompress(bytes(idat))

    out = bytearray(stride * height)
    prev = bytearray(stride)
    src = 0
    for y in range(height):
        ftype = decompressed[src]
        src += 1
        line = bytearray(decompressed[src:src + stride])
        src += stride
        if ftype == 1:  # Sub
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif ftype == 2:  # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:  # Average
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:  # Paeth
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                c = prev[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(a, prev[i], c)) & 0xFF
        out[y * stride:(y + 1) * stride] = line
        prev = line

    return width, height, channels, out


# --- Contrôles image ---------------------------------------------------------
def check_image(path: Path, config: Config) -> list:
    """Contrôle une image réelle. Retourne une liste de (niveau, message)."""
    issues = []
    try:
        w, h, ch, data = read_png(path)
    except Exception as exc:  # noqa: BLE001
        return [(REVIEW, f"Image illisible par le contrôle stdlib : {exc}")]

    expected = config.resolution
    if w != h:
        issues.append((REJECT, f"Image non carrée ({w}x{h})"))
    if w != expected or h != expected:
        issues.append((REVIEW, f"Résolution {w}x{h} != attendue {expected}x{expected}"))

    bg = config.background
    white_min = int(bg.get("white_min_channel", 240))
    white_ratio_min = float(bg.get("white_min_ratio", 0.45))
    comp = config.composition
    tol = float(comp.get("center_tolerance_pct", 6)) / 100.0
    min_h_ratio = float(comp.get("subject_min_height_ratio", 0.6))

    # Échantillonnage pour la performance (pas trop fin pour de grandes images).
    step = max(1, w // 256)
    white = 0
    sampled = 0
    min_x = min_y = 10**9
    max_x = max_y = -1
    for y in range(0, h, step):
        row = y * w * ch
        for x in range(0, w, step):
            o = row + x * ch
            r, g, b = data[o], data[o + 1], data[o + 2]
            sampled += 1
            if r >= white_min and g >= white_min and b >= white_min:
                white += 1
            else:
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y

    white_ratio = white / (sampled or 1)
    if white_ratio < white_ratio_min:
        issues.append((REJECT, f"Fond non majoritairement blanc (blanc={white_ratio:.0%})"))

    if max_x < 0:  # image entièrement blanche
        issues.append((REJECT, "Aucun personnage détecté (image vide)"))
        return issues

    # Personnage coupé : touche un bord (au-delà du pas d'échantillonnage).
    if min_x <= step or min_y <= step or max_x >= w - 1 - step or max_y >= h - 1 - step:
        issues.append((REVIEW, "Personnage possiblement coupé (touche un bord)"))

    # Centrage horizontal.
    cx = (min_x + max_x) / 2 / w
    if abs(cx - 0.5) > tol:
        issues.append((REVIEW, f"Personnage non centré horizontalement (cx={cx:.2f})"))

    # Hauteur occupée (anti-zoom).
    subj_h = (max_y - min_y) / h
    if subj_h < min_h_ratio:
        issues.append((REVIEW, f"Personnage trop petit (hauteur={subj_h:.0%})"))

    return issues


# --- Rapport -----------------------------------------------------------------
def _status_from(issues: list) -> str:
    levels = {lvl for lvl, _ in issues}
    if REJECT in levels:
        return REJECT
    if REVIEW in levels:
        return REVIEW
    return VALID


def build_report(combo: Combination, config: Config, image_path: Path | None) -> dict:
    """Construit le rapport de validation d'une combinaison/image."""
    issues = check_logical(combo, config)
    if image_path and Path(image_path).exists():
        issues += check_image(image_path, config)

    return {
        "id": combo.uid,
        "status": _status_from(issues),
        "reasons": [f"[{lvl}] {msg}" for lvl, msg in issues],
        "image_checked": bool(image_path and Path(image_path).exists()),
    }
