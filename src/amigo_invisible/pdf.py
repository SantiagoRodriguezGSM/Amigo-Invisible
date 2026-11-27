"""Generación del PDF navideño con la asignación de cada participante.

Todo el diseño se dibuja con vectores (sin emojis ni imágenes), de modo que se ve
nítido a cualquier tamaño y no depende de que la fuente tenga símbolos. Las
fuentes incluidas (Great Vibes y Crimson Text, licencia SIL OFL) admiten tildes,
eñes y signos de apertura (¡ ¿), por lo que cualquier nombre en español se ve bien.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from .config import Settings

FONTS_DIR = Path(__file__).parent / "assets" / "fonts"

# Nombres con los que se registran las fuentes en ReportLab.
SCRIPT = "GreatVibes"
SERIF = "CrimsonText"
SERIF_BOLD = "CrimsonText-SemiBold"
SERIF_ITALIC = "CrimsonText-Italic"

_FONT_FILES = {
    SCRIPT: "GreatVibes-Regular.ttf",
    SERIF: "CrimsonText-Regular.ttf",
    SERIF_BOLD: "CrimsonText-SemiBold.ttf",
    SERIF_ITALIC: "CrimsonText-Italic.ttf",
}

# Paleta
CREAM = HexColor("#FBF6EC")
GREEN = HexColor("#1E4D3B")
GREEN_LIGHT = HexColor("#2F6B52")
RED = HexColor("#B3202A")
GOLD = HexColor("#C19A3E")
GOLD_DARK = HexColor("#8A6A1F")
GOLD_LIGHT = HexColor("#E6D3A3")
INK = HexColor("#2B2B2B")
MUTED = HexColor("#6B6B6B")
SNOW = HexColor("#E8DFCB")
WOOD = HexColor("#6B4A2B")
WHITE = HexColor("#FFFFFF")

PAGE_W, PAGE_H = A4


def register_fonts() -> None:
    """Registra las fuentes incluidas en el paquete (idempotente)."""
    registered = set(pdfmetrics.getRegisteredFontNames())
    for name, filename in _FONT_FILES.items():
        if name not in registered:
            pdfmetrics.registerFont(TTFont(name, str(FONTS_DIR / filename)))


def _y(top: float) -> float:
    """Convierte una distancia medida desde el borde superior a coordenada del PDF."""
    return PAGE_H - top


# --------------------------------------------------------------------------- texto


def fit_font_size(text: str, font: str, max_size: float, max_width: float, min_size: float = 8) -> float:
    """Tamaño de fuente más grande (hasta ``max_size``) con el que ``text`` cabe en ``max_width``."""
    size = max_size
    while size > min_size and pdfmetrics.stringWidth(text, font, size) > max_width:
        size -= 0.5
    return size


def fit_name(name: str, font: str, max_size: float, max_width: float, min_size: float = 30):
    """Ajusta un nombre al ancho disponible: reduce la fuente y, si aun así no cabe, lo parte en dos líneas."""
    size = fit_font_size(name, font, max_size, max_width, min_size)
    if pdfmetrics.stringWidth(name, font, size) <= max_width or " " not in name:
        return [name], size

    words = name.split()
    best = min(
        range(1, len(words)),
        key=lambda k: abs(
            pdfmetrics.stringWidth(" ".join(words[:k]), font, min_size)
            - pdfmetrics.stringWidth(" ".join(words[k:]), font, min_size)
        ),
    )
    lines = [" ".join(words[:best]), " ".join(words[best:])]
    size = min(fit_font_size(line, font, max_size, max_width, 12) for line in lines)
    return lines, size


def _spaced(c: Canvas, x: float, y: float, text: str, font: str, size: float, spacing: float, color) -> None:
    """Texto centrado en ``x`` con espaciado entre letras (para etiquetas en versalitas)."""
    width = pdfmetrics.stringWidth(text, font, size) + spacing * (len(text) - 1)
    # El espaciado (Tc) forma parte del estado gráfico y persiste tras el texto,
    # por eso se aísla con saveState/restoreState.
    c.saveState()
    t = c.beginText(x - width / 2, y)
    t.setFont(font, size)
    t.setCharSpace(spacing)
    t.setFillColor(color)
    t.textOut(text)
    c.drawText(t)
    c.restoreState()


def _centered(c: Canvas, x: float, y: float, text: str, font: str, size: float, color) -> None:
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawCentredString(x, y, text)


# ----------------------------------------------------------------------- ilustración


def _star(c: Canvas, cx: float, cy: float, outer: float, inner: float, fill, rotation: float = 90) -> None:
    """Estrella de cinco puntas."""
    path = c.beginPath()
    for i in range(10):
        radius = outer if i % 2 == 0 else inner
        angle = math.radians(rotation + i * 36)
        point = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
        path.moveTo(*point) if i == 0 else path.lineTo(*point)
    path.close()
    c.setFillColor(fill)
    c.drawPath(path, stroke=0, fill=1)


def _snowflake(c: Canvas, cx: float, cy: float, radius: float) -> None:
    c.setStrokeColor(SNOW)
    c.setLineWidth(0.9)
    for i in range(6):
        angle = math.radians(i * 60)
        dx, dy = math.cos(angle), math.sin(angle)
        c.line(cx, cy, cx + radius * dx, cy + radius * dy)
        # Dos ramitas por brazo
        bx, by = cx + radius * 0.6 * dx, cy + radius * 0.6 * dy
        for side in (-1, 1):
            branch = math.radians(i * 60 + side * 50)
            c.line(bx, by, bx + radius * 0.35 * math.cos(branch), by + radius * 0.35 * math.sin(branch))


def _snow(c: Canvas) -> None:
    """Nieve decorativa, siempre en las mismas posiciones y fuera de la zona de texto."""
    rng = random.Random(24)
    placed = 0
    while placed < 34:
        x, y = rng.uniform(48, PAGE_W - 48), rng.uniform(48, PAGE_H - 48)
        top = PAGE_H - y
        if 90 < x < PAGE_W - 90 and 290 < top < 780:
            continue  # reservamos el centro para el texto
        if 130 < x < PAGE_W - 130 and top < 290:
            continue  # ...y la zona del árbol
        if rng.random() < 0.35:
            _snowflake(c, x, y, rng.uniform(6, 11))
        else:
            c.setFillColor(SNOW)
            c.circle(x, y, rng.uniform(1.2, 2.6), stroke=0, fill=1)
        placed += 1


def _gift(c: Canvas, x: float, y: float, size: float, box, ribbon) -> None:
    """Regalo con lazo; (x, y) es el centro de la base."""
    left = x - size / 2
    c.setFillColor(box)
    c.rect(left, y, size, size * 0.85, stroke=0, fill=1)
    c.setFillColor(ribbon)
    c.rect(x - size * 0.09, y, size * 0.18, size * 0.85, stroke=0, fill=1)
    c.rect(left, y + size * 0.85 * 0.42, size, size * 0.14, stroke=0, fill=1)
    # Tapa
    c.setFillColor(box)
    c.rect(left - size * 0.05, y + size * 0.85, size * 1.1, size * 0.16, stroke=0, fill=1)
    c.setFillColor(ribbon)
    c.rect(x - size * 0.09, y + size * 0.85, size * 0.18, size * 0.16, stroke=0, fill=1)
    # Lazo
    top = y + size * 1.01
    for side in (-1, 1):
        c.saveState()
        c.translate(x + side * size * 0.17, top + size * 0.08)
        c.rotate(side * -25)
        c.setFillColor(ribbon)
        c.ellipse(-size * 0.17, -size * 0.1, size * 0.17, size * 0.1, stroke=0, fill=1)
        c.restoreState()
    c.setFillColor(ribbon)
    c.circle(x, top + size * 0.04, size * 0.07, stroke=0, fill=1)


def _tree(c: Canvas, cx: float, base: float, height: float) -> None:
    """Árbol de Navidad; ``base`` es la coordenada y del suelo."""
    scale = height / 150
    trunk_w, trunk_h = 16 * scale, 16 * scale
    c.setFillColor(WOOD)
    c.rect(cx - trunk_w / 2, base, trunk_w, trunk_h, stroke=0, fill=1)

    tiers = [  # (ancho de la base, alto, desplazamiento vertical, color)
        (112, 58, 10, GREEN),
        (88, 54, 44, GREEN_LIGHT),
        (62, 50, 78, GREEN),
    ]
    for width, h, lift, color in tiers:
        y0 = base + trunk_h + (lift - 10) * scale
        w, hh = width * scale, h * scale
        path = c.beginPath()
        path.moveTo(cx - w / 2, y0)
        path.lineTo(cx, y0 + hh)
        path.lineTo(cx + w / 2, y0)
        # Borde inferior con pequeños festones
        steps = 4
        for i in range(steps):
            x1 = cx + w / 2 - (i + 1) * w / steps
            xm = cx + w / 2 - (i + 0.5) * w / steps
            path.curveTo(xm + w / steps * 0.2, y0 - 5 * scale, xm - w / steps * 0.2, y0 - 5 * scale, x1, y0)
        path.close()
        c.setFillColor(color)
        c.drawPath(path, stroke=0, fill=1)

    # Guirnalda dorada
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.6)
    for y_off, span in ((42, 38), (76, 28), (108, 17)):
        yy = base + trunk_h + (y_off - 10) * scale
        p = c.beginPath()
        p.moveTo(cx - span * scale, yy)
        p.curveTo(
            cx - span * 0.4 * scale,
            yy - 9 * scale,
            cx + span * 0.4 * scale,
            yy - 3 * scale,
            cx + span * scale,
            yy - 11 * scale,
        )
        c.drawPath(p, stroke=1, fill=0)

    # Bolas
    for dx, dy, color in (
        (-30, 24, RED),
        (22, 30, GOLD),
        (-8, 60, GOLD),
        (28, 66, RED),
        (-24, 88, RED),
        (6, 100, GOLD),
        (-2, 126, RED),
        (22, 14, GOLD),
        (-42, 12, GOLD),
    ):
        c.setFillColor(color)
        c.circle(cx + dx * scale, base + trunk_h + dy * scale, 4.6 * scale, stroke=0, fill=1)
        c.setFillColor(Color(1, 1, 1, alpha=0.55))
        c.circle(cx + (dx - 1.4) * scale, base + trunk_h + (dy + 1.4) * scale, 1.2 * scale, stroke=0, fill=1)

    _star(c, cx, base + trunk_h + 150 * scale - 4 * scale, 13 * scale, 5.5 * scale, GOLD)


def _illustration(c: Canvas, cx: float, ground_top: float) -> None:
    """Escena: montículo de nieve, árbol y regalos."""
    ground = _y(ground_top)
    c.setFillColor(WHITE)
    c.setStrokeColor(SNOW)
    c.setLineWidth(1)
    c.ellipse(cx - 150, ground - 20, cx + 150, ground + 18, stroke=1, fill=1)
    _tree(c, cx, ground - 2, 150)
    _gift(c, cx - 78, ground - 6, 34, RED, GOLD)
    _gift(c, cx + 84, ground - 8, 28, GOLD_DARK, RED)
    _gift(c, cx + 56, ground - 12, 20, GREEN, GOLD_LIGHT)


# ----------------------------------------------------------------------- adornos


def _frame(c: Canvas) -> None:
    c.setStrokeColor(GREEN)
    c.setLineWidth(4)
    c.rect(26, 26, PAGE_W - 52, PAGE_H - 52, stroke=1, fill=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.9)
    c.rect(35, 35, PAGE_W - 70, PAGE_H - 70, stroke=1, fill=0)
    # Rombos dorados en las esquinas
    c.setFillColor(GOLD)
    for x, y in ((35, 35), (PAGE_W - 35, 35), (35, PAGE_H - 35), (PAGE_W - 35, PAGE_H - 35)):
        c.saveState()
        c.translate(x, y)
        c.rotate(45)
        c.rect(-5, -5, 10, 10, stroke=0, fill=1)
        c.restoreState()


def _divider(c: Canvas, cx: float, y: float, half: float = 80) -> None:
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.9)
    c.line(cx - half, y, cx - 12, y)
    c.line(cx + 12, y, cx + half, y)
    c.setFillColor(GOLD)
    c.saveState()
    c.translate(cx, y)
    c.rotate(45)
    c.rect(-3.5, -3.5, 7, 7, stroke=0, fill=1)
    c.restoreState()
    for side in (-1, 1):
        c.circle(cx + side * 3.5 * 3, y, 1.4, stroke=0, fill=1)


def _wax_seal(c: Canvas, cx: float, cy: float, radius: float) -> None:
    c.setFillColor(RED)
    c.circle(cx, cy, radius, stroke=0, fill=1)
    c.setStrokeColor(Color(1, 1, 1, alpha=0.35))
    c.setLineWidth(1)
    c.circle(cx, cy, radius * 0.78, stroke=1, fill=0)
    _star(c, cx, cy - 0.5, radius * 0.5, radius * 0.22, GOLD_LIGHT)


# ----------------------------------------------------------------------- página


def draw_page(c: Canvas, giver: str, receiver: str, settings: Settings) -> None:
    """Dibuja la página completa sobre el lienzo ``c``."""
    cx = PAGE_W / 2

    c.setFillColor(CREAM)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    _snow(c)
    _frame(c)

    # Ilustración y título
    _illustration(c, cx, ground_top=232)
    _centered(c, cx, _y(318), "Amigo Invisible", SCRIPT, 60, RED)
    _spaced(c, cx, _y(344), "TU ASIGNACIÓN NAVIDEÑA", SERIF_BOLD, 10, 3.2, GOLD_DARK)
    _divider(c, cx, _y(362))

    # Saludo
    greeting = f"Hola, {giver}"
    size = fit_font_size(greeting, SERIF_BOLD, 24, PAGE_W - 150)
    _centered(c, cx, _y(412), greeting, SERIF_BOLD, size, GREEN)
    _centered(c, cx, _y(444), "Este año te toca hacer un regalo a…", SERIF_ITALIC, 17, INK)

    # Tarjeta con el nombre
    card_w, card_h = PAGE_W - 150, 112
    card_x, card_top = cx - card_w / 2, 466
    card_y = _y(card_top + card_h)
    c.setFillColor(WHITE)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.4)
    c.roundRect(card_x, card_y, card_w, card_h, 12, stroke=1, fill=1)
    c.setStrokeColor(GOLD_LIGHT)
    c.setLineWidth(0.7)
    c.roundRect(card_x + 6, card_y + 6, card_w - 12, card_h - 12, 8, stroke=1, fill=0)

    lines, name_size = fit_name(receiver, SCRIPT, 58, card_w - 48)
    leading = name_size * 0.95
    first_baseline = card_y + card_h / 2 + (len(lines) - 1) * leading / 2 - name_size * 0.28
    for i, line in enumerate(lines):
        _centered(c, cx, first_baseline - i * leading, line, SCRIPT, name_size, RED)

    # Detalles del evento
    info_top = 640
    col = 118
    c.setStrokeColor(GOLD_LIGHT)
    c.setLineWidth(0.9)
    c.line(cx, _y(info_top - 20), cx, _y(info_top + 30))
    for x, label, value in (
        (cx - col, "PRESUPUESTO", settings.budget),
        (cx + col, "ENTREGA", settings.event_date),
    ):
        _spaced(c, x, _y(info_top - 8), label, SERIF_BOLD, 9, 2.6, GOLD_DARK)
        value_size = fit_font_size(value, SERIF_BOLD, 21, 2 * col - 36)
        _centered(c, x, _y(info_top + 18), value, SERIF_BOLD, value_size, GREEN)

    # Nota de secreto
    _wax_seal(c, cx, _y(712), 15)
    _centered(
        c, cx, _y(748), "Es un secreto: no se lo cuentes a nadie hasta el día del regalo.", SERIF_ITALIC, 14, MUTED
    )

    # Pie
    _spaced(c, cx, _y(786), f"FELICES FIESTAS · {settings.event_year}", SERIF_BOLD, 9, 2.6, GOLD_DARK)


def create_assignment_pdf(giver: str, receiver: str, output_path: str | Path, settings: Settings) -> Path:
    """Crea el PDF de ``giver`` indicando que le toca regalar a ``receiver``."""
    register_fonts()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    c = Canvas(str(output_path), pagesize=A4, pageCompression=1)
    c.setTitle("Tu Amigo Invisible")
    c.setAuthor(settings.sender_name)
    c.setSubject("Asignación del Amigo Invisible")
    draw_page(c, giver, receiver, settings)
    c.showPage()
    c.save()
    return output_path
