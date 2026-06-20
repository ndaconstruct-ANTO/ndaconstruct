"""Opérations d'image en bibliothèque standard (sans Pillow) sur tampons RGBA.

Sert à l'éditeur de calques : détourage automatique (fond transparent),
ajustement à la taille de la collection, gomme. Tout est testable hors-ligne.
"""

from __future__ import annotations

from collections import deque


def _idx(x, y, w):
    return (y * w + x) * 4


def remove_background(rgba: bytearray, w: int, h: int, tolerance: int = 32) -> int:
    """Rend transparent le fond connecté aux bords (color-key par remplissage).

    Part des pixels de bord, et propage la transparence aux pixels voisins dont
    la couleur est proche (≤ tolerance) de la couleur de fond échantillonnée.
    Préserve le sujet central même s'il a une couleur proche, tant qu'il n'est
    pas connecté au bord. Retourne le nombre de pixels rendus transparents.
    """
    # Couleur de fond de référence = moyenne des 4 coins.
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    rs = gs = bs = 0
    for (cx, cy) in corners:
        o = _idx(cx, cy, w)
        rs += rgba[o]; gs += rgba[o + 1]; bs += rgba[o + 2]
    br, bg, bb = rs // 4, gs // 4, bs // 4
    tol2 = tolerance * tolerance * 3

    def close(o):
        dr = rgba[o] - br; dg = rgba[o + 1] - bg; db = rgba[o + 2] - bb
        return dr * dr + dg * dg + db * db <= tol2

    visited = bytearray(w * h)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            q.append((x, y))

    cleared = 0
    while q:
        x, y = q.popleft()
        p = y * w + x
        if visited[p]:
            continue
        visited[p] = 1
        o = p * 4
        if not close(o):
            continue
        if rgba[o + 3] != 0:
            rgba[o + 3] = 0
            cleared += 1
        if x > 0:
            q.append((x - 1, y))
        if x < w - 1:
            q.append((x + 1, y))
        if y > 0:
            q.append((x, y - 1))
        if y < h - 1:
            q.append((x, y + 1))
    return cleared


def erase_circle(rgba: bytearray, w: int, h: int, cx: int, cy: int, r: int) -> None:
    """Efface (alpha=0) un disque — outil gomme."""
    r2 = r * r
    for y in range(max(0, cy - r), min(h, cy + r + 1)):
        for x in range(max(0, cx - r), min(w, cx + r + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                rgba[_idx(x, y, w) + 3] = 0


def fit_to_canvas(src: bytearray, sw: int, sh: int, dw: int, dh: int,
                  scale: float = 1.0) -> bytearray:
    """Redimensionne (plus proche voisin) en gardant le ratio, centre sur un
    canevas transparent dw×dh. ``scale`` permet d'agrandir/réduire le sujet.
    """
    if sw == 0 or sh == 0:
        return bytearray(dw * dh * 4)
    ratio = min(dw / sw, dh / sh) * max(0.05, scale)
    tw = max(1, int(sw * ratio))
    th = max(1, int(sh * ratio))
    ox = (dw - tw) // 2
    oy = (dh - th) // 2

    dst = bytearray(dw * dh * 4)
    for y in range(th):
        sy = min(sh - 1, int(y / ratio))
        dy = oy + y
        if dy < 0 or dy >= dh:
            continue
        for x in range(tw):
            sx = min(sw - 1, int(x / ratio))
            dx = ox + x
            if dx < 0 or dx >= dw:
                continue
            so = _idx(sx, sy, sw)
            do = _idx(dx, dy, dw)
            dst[do:do + 4] = src[so:so + 4]
    return dst
