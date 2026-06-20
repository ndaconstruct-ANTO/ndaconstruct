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


def _rgb_to_hsl(r, g, b):
    r, g, b = r / 255, g / 255, b / 255
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        return 0.0, 0.0, l
    d = mx - mn
    s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    if mx == r:
        h = (g - b) / d + (6 if g < b else 0)
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return h / 6, s, l


def _hue(p, q, t):
    if t < 0:
        t += 1
    if t > 1:
        t -= 1
    if t < 1 / 6:
        return p + (q - p) * 6 * t
    if t < 1 / 2:
        return q
    if t < 2 / 3:
        return p + (q - p) * (2 / 3 - t) * 6
    return p


def _hsl_to_rgb(h, s, l):
    if s == 0:
        v = int(l * 255)
        return v, v, v
    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q
    return (int(_hue(p, q, h + 1 / 3) * 255),
            int(_hue(p, q, h) * 255),
            int(_hue(p, q, h - 1 / 3) * 255))


def recolor(rgba: bytearray, w: int, h: int, target_rgb, strength: float = 0.85) -> None:
    """Recolore un calque vers ``target_rgb`` en CONSERVANT les ombres/lumières.

    Prend la teinte et la saturation de la couleur cible, garde la luminosité de
    chaque pixel (donc le relief de la fourrure reste réaliste). ``strength``
    mélange entre couleur d'origine et couleur recolorée. Modifie en place.
    """
    th, ts, _ = _rgb_to_hsl(*target_rgb)
    for i in range(0, len(rgba), 4):
        if rgba[i + 3] == 0:
            continue
        _, _, l = _rgb_to_hsl(rgba[i], rgba[i + 1], rgba[i + 2])
        nr, ng, nb = _hsl_to_rgb(th, ts, l)
        if strength >= 1.0:
            rgba[i], rgba[i + 1], rgba[i + 2] = nr, ng, nb
        else:
            rgba[i] = int(rgba[i] * (1 - strength) + nr * strength)
            rgba[i + 1] = int(rgba[i + 1] * (1 - strength) + ng * strength)
            rgba[i + 2] = int(rgba[i + 2] * (1 - strength) + nb * strength)


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
