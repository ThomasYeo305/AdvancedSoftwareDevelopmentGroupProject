# ============================================================
# PAMS — widgets.py
# Reusable PySide6 UI components — Professional light theme
# ============================================================
from __future__ import annotations   # allows type hints like 'QWidget | None' on Python 3.10

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableView, QHeaderView, QSizePolicy, QProgressBar,
    QGraphicsDropShadowEffect,   # used to add soft drop shadows beneath cards and stat tiles
)
from PySide6.QtCore import Qt, QSortFilterProxyModel, Signal, QRectF, QPointF, QTimer   # QRectF / QPointF used in custom vector icon drawing; QTimer drives badge pulse animation
from PySide6.QtGui import (
    QFont, QColor, QStandardItemModel, QStandardItem, QPainter,
    QLinearGradient, QPen, QPainterPath, QRadialGradient, QConicalGradient,   # gradient classes used for glossy badge fills, progress bar fills, and card top stripes
)
import math   # used for trigonometry in the 'overdue' warning triangle icon (cos/sin)

from .theme import PALETTE as P, FONTS as F, DIMS as D, lerp_color   # imports the current theme palette (P), font specs (F), spacing constants (D), and colour blending helper


# ──────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────
def qfont(spec: tuple) -> QFont:
    """Convert a theme font tuple (family, size, weight) → QFont."""
    family, size, weight = spec   # unpacks the font spec tuple (e.g. ('Segoe UI', 11, 'normal'))
    f = QFont(family, size)       # creates a QFont with the specified typeface and point size
    if weight == "bold":
        f.setBold(True)           # makes the font bold if the spec says so (e.g. for headings and button labels)
    return f                      # returns the ready-to-use QFont object


def _blend(c1: str, c2: str, t: float) -> str:
    """Alias for lerp_color. t=0→c1, t=1→c2."""
    return lerp_color(c1, c2, t)   # delegates to the shared lerp_color helper; blends c1 toward c2 by amount t (0.0=c1, 1.0=c2)


# ──────────────────────────────────────────────────────────
# VECTOR ICON PAINTER
# ──────────────────────────────────────────────────────────
def draw_key_icon(p: QPainter, key: str, cx: float, cy: float,
                  size: float, color: QColor):
    """
    Draw a beautiful custom vector icon centered at (cx, cy) with scale `size`.
    Keys: dashboard, tenants, apartments, payments, maintenance,
          complaints, reports, users  — and stat codes: AP, TN, MT, OD, RC.
    """
    p.save()                               # saves the painter state so we can safely change pen/brush without affecting callers
    p.setRenderHint(QPainter.Antialiasing) # enables smooth anti-aliased lines so icons look crisp at any size
    s = size                               # short alias for the icon scale factor
    pw = max(1.2, s * 0.11)               # calculates pen stroke width proportionally to the icon size (minimum 1.2px)
    pen = QPen(color, pw, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)   # creates the main drawing pen with round caps and joins for smooth vector shapes
    fill = QColor(color)
    fill.setAlpha(65)   # creates a semi-transparent fill colour (alpha 65 out of 255) for background shape fills

    # Normalise key — maps short codes to full icon names
    _map = {
        "ap": "apartments", "tn": "tenants", "mt": "maintenance",
        "od": "overdue",    "rc": "collected", "db": "dashboard",
        "pm": "payments",   "cp": "complaints", "rp": "reports",
        "us": "users",
    }
    k = _map.get(key.lower(), key.lower())   # converts the short code (e.g. 'ap') to its full name ('apartments'), or keeps the key as-is if already full

    if k == "dashboard":
        # Draws a 2×2 grid of rounded squares representing the 4 dashboard panels
        gap = s * 0.14           # gap between the four squares
        hw = (s * 0.90 - gap) / 2   # width/height of each individual square
        for row in range(2):        # loops through 2 rows of squares
            for col in range(2):    # loops through 2 columns of squares
                tx = cx - s * 0.45 + col * (hw + gap)   # x position of this square
                ty = cy - s * 0.45 + row * (hw + gap)   # y position of this square
                p.setPen(Qt.NoPen); p.setBrush(fill)    # fills the square with the semi-transparent colour
                p.drawRoundedRect(QRectF(tx, ty, hw, hw), 3, 3)   # draws the filled rounded square
                p.setPen(pen); p.setBrush(Qt.NoBrush)              # switches to just drawing the outline
                p.drawRoundedRect(QRectF(tx, ty, hw, hw), 3, 3)   # draws the square outline on top

    elif k == "tenants":
        # Draws a person silhouette: a circle head + a curved body arc
        hr = s * 0.26   # radius of the head circle
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx - hr, cy - s * 0.46, hr * 2, hr * 2))   # draws the circular head
        bp = QPainterPath()   # path for the curved body/shoulder shape
        bp.moveTo(cx - s * 0.46, cy + s * 0.46)   # starts at bottom-left of the body
        bp.cubicTo(cx - s*0.46, cy + s*0.04, cx - s*0.26, cy - s*0.02, cx, cy - s*0.02)   # curves up to centre
        bp.cubicTo(cx + s*0.26, cy - s*0.02, cx + s*0.46, cy + s*0.04, cx + s*0.46, cy + s*0.46)   # curves back down to bottom-right
        p.drawPath(bp)   # draws the person's body/shoulder outline

    elif k == "apartments":
        # Draws a small building with windows and a door
        bx, by = cx - s * 0.30, cy - s * 0.46   # top-left corner of the building rectangle
        bw, bh = s * 0.60, s * 0.92              # width and height of the building
        p.setPen(Qt.NoPen); p.setBrush(fill)
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 2, 2)   # draws the filled building body
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 2, 2)   # draws the building outline
        p.setPen(QPen(color, pw * 1.4, Qt.SolidLine, Qt.FlatCap))
        p.drawLine(QPointF(bx, by + 2), QPointF(bx + bw, by + 2))   # draws a thick horizontal line at the top of the building (roofline detail)
        ww, wh = s * 0.13, s * 0.12   # width and height of each window
        for row in range(3):           # loops through 3 rows of windows
            for col in range(2):       # loops through 2 columns of windows
                wx = bx + s * 0.08 + col * (ww + s * 0.11)   # x position of this window
                wy = by + s * 0.10 + row * (wh + s * 0.09)   # y position of this window
                if wy + wh < by + bh - s * 0.24:   # only draws windows that fit above the door area
                    p.setPen(Qt.NoPen)
                    wc = QColor(color); wc.setAlpha(130)   # semi-transparent window fill
                    p.setBrush(wc)
                    p.drawRoundedRect(QRectF(wx, wy, ww, wh), 1.5, 1.5)   # draws each window as a small rounded rectangle
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(cx - s*0.10, by + bh - s*0.26, s*0.20, s*0.26), 2, 0)   # draws the door at the bottom centre of the building

    elif k == "payments":
        # Draws a credit/debit card with a magnetic stripe and chip
        card = QRectF(cx - s*0.44, cy - s*0.28, s*0.88, s*0.56)   # the card rectangle
        p.setPen(Qt.NoPen); p.setBrush(fill)
        p.drawRoundedRect(card, 5, 5)   # draws the filled card body
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(card, 5, 5)   # draws the card outline
        sc2 = QColor(color); sc2.setAlpha(150)
        p.setPen(Qt.NoPen); p.setBrush(sc2)
        p.drawRect(QRectF(cx - s*0.44, cy - s*0.14, s*0.88, s*0.12))   # draws the dark magnetic stripe band across the card
        chip = QColor(color); chip.setAlpha(185)
        p.setBrush(chip)
        p.drawRoundedRect(QRectF(cx - s*0.36, cy + s*0.05, s*0.23, s*0.16), 2, 2)   # draws the chip (small rectangle at bottom-left of card)
        p.setPen(pen); p.setBrush(Qt.NoBrush)

    elif k == "maintenance":
        # Draws a spanner/wrench tool icon
        p.setPen(QPen(color, s * 0.20, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(QPointF(cx - s*0.38, cy + s*0.42), QPointF(cx + s*0.06, cy - s*0.10))   # draws the handle of the spanner
        hr = s * 0.24
        hcx, hcy = cx + s*0.20, cy - s*0.22   # centre of the spanner head circle
        p.setPen(pen); p.setBrush(fill)
        p.drawEllipse(QRectF(hcx - hr, hcy - hr, hr * 2, hr * 2))   # draws the circular head of the spanner
        p.setPen(QPen(color, pw * 0.9, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(hcx, hcy - hr*0.6), QPointF(hcx, hcy + hr*0.6))   # draws a vertical cross line inside the spanner head
        p.drawLine(QPointF(hcx - hr*0.6, hcy), QPointF(hcx + hr*0.6, hcy))   # draws a horizontal cross line inside the spanner head

    elif k == "complaints":
        # Draws a speech/chat bubble with a tail and three dots
        bub = QRectF(cx - s*0.44, cy - s*0.42, s*0.88, s*0.64)   # the speech bubble rectangle
        p.setPen(Qt.NoPen); p.setBrush(fill)
        p.drawRoundedRect(bub, 10, 10)   # draws the filled bubble body
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(bub, 10, 10)   # draws the bubble outline
        tail = QPainterPath()   # path for the triangular speech bubble tail
        tail.moveTo(cx - s*0.08, cy + s*0.22)   # start of the tail at the bottom of the bubble
        tail.lineTo(cx - s*0.28, cy + s*0.46)   # tip of the tail pointing down-left
        tail.lineTo(cx + s*0.06, cy + s*0.22)   # end of the tail back at bubble bottom
        p.setPen(pen); p.drawPath(tail)   # draws the tail outline
        for i in range(3):   # loops through 3 dots for the "..." inside the bubble
            p.setPen(Qt.NoPen); p.setBrush(color)
            p.drawEllipse(QRectF(cx - s*0.16 + i*s*0.18, cy - s*0.13, s*0.10, s*0.10))   # draws each of the three dots spread across the bubble

    elif k == "reports":
        # Draws a bar chart with 3 bars and a trend line with data points
        bars = [(cx - s*0.36, 0.62), (cx - s*0.10, 0.38), (cx + s*0.16, 0.76)]   # (x position, height fraction) for each bar
        bw = s * 0.22     # width of each bar
        base_y = cy + s * 0.40   # y position of the chart baseline
        for bx_i, bh_f in bars:   # loops through each bar
            bh_px = bh_f * s * 0.86   # calculates the pixel height of this bar
            bc = QColor(color); bc.setAlpha(160)
            p.setPen(Qt.NoPen); p.setBrush(bc)
            p.drawRoundedRect(QRectF(bx_i, base_y - bh_px, bw, bh_px), 2.5, 2.5)   # draws this bar as a rounded rectangle above the baseline
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawLine(QPointF(cx - s*0.46, base_y), QPointF(cx + s*0.46, base_y))   # draws the horizontal baseline of the chart
        dots = [
            (cx - s*0.25, base_y - 0.62*s*0.86),   # top centre of bar 1
            (cx + s*0.01, base_y - 0.38*s*0.86),   # top centre of bar 2
            (cx + s*0.27, base_y - 0.76*s*0.86),   # top centre of bar 3
        ]
        p.setPen(QPen(color, pw * 0.85, Qt.SolidLine, Qt.RoundCap))
        for i in range(len(dots) - 1):
            p.drawLine(QPointF(*dots[i]), QPointF(*dots[i + 1]))   # draws the trend line connecting the top of each bar
        p.setPen(Qt.NoPen)
        for pt in dots:   # loops through each data point on the trend line
            p.setBrush(color)
            p.drawEllipse(QRectF(pt[0] - s*0.055, pt[1] - s*0.055, s*0.11, s*0.11))   # draws a small filled circle at each data point

    elif k == "users":
        # Draws two overlapping person silhouettes (front person larger)
        hr1 = s * 0.19   # head radius for the front (right) person
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx + s*0.06 - hr1, cy - s*0.40, hr1*2, hr1*2))   # draws the front person's head
        bp1 = QPainterPath()   # body path for the front person
        bp1.moveTo(cx - s*0.06, cy + s*0.44)
        bp1.cubicTo(cx - s*0.06, cy + s*0.08, cx + s*0.06, cy + s*0.02, cx + s*0.24, cy + s*0.02)
        bp1.cubicTo(cx + s*0.42, cy + s*0.02, cx + s*0.50, cy + s*0.10, cx + s*0.50, cy + s*0.44)
        p.drawPath(bp1)   # draws the front person's body/shoulder curve
        hr2 = s * 0.21   # head radius for the back (left) person (slightly larger to show behind)
        p.drawEllipse(QRectF(cx - s*0.22 - hr2, cy - s*0.42, hr2*2, hr2*2))   # draws the back person's head
        bp2 = QPainterPath()   # body path for the back person
        bp2.moveTo(cx - s*0.50, cy + s*0.44)
        bp2.cubicTo(cx - s*0.50, cy + s*0.06, cx - s*0.32, cy + s*0.01, cx - s*0.18, cy + s*0.01)
        bp2.cubicTo(cx - s*0.04, cy + s*0.01, cx + s*0.02, cy + s*0.06, cx + s*0.02, cy + s*0.44)
        p.drawPath(bp2)   # draws the back person's body/shoulder curve

    elif k == "overdue":
        # Draws a warning triangle with an exclamation mark inside
        pts = [
            QPointF(cx + s*0.44*math.cos(math.radians(-90 + i*120)),   # calculates each of the 3 corners of an equilateral triangle using trigonometry
                    cy + s*0.44*math.sin(math.radians(-90 + i*120)))
            for i in range(3)
        ]
        tri = QPainterPath()   # builds the triangle path from the 3 corners
        tri.moveTo(pts[0]); tri.lineTo(pts[1]); tri.lineTo(pts[2]); tri.closeSubpath()
        p.setPen(Qt.NoPen); p.setBrush(fill); p.drawPath(tri)    # draws the filled triangle background
        p.setPen(pen); p.setBrush(Qt.NoBrush); p.drawPath(tri)   # draws the triangle outline
        p.setPen(QPen(color, pw * 1.4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx, cy - s*0.24), QPointF(cx, cy + s*0.06))    # draws the vertical line of the exclamation mark
        p.setPen(Qt.NoPen); p.setBrush(color)
        p.drawEllipse(QRectF(cx - s*0.07, cy + s*0.14, s*0.14, s*0.14))   # draws the dot at the bottom of the exclamation mark

    elif k == "collected":
        # Draws a circle with a tick/checkmark inside (represents successful payment collected)
        cr = s * 0.42   # radius of the circle
        p.setPen(Qt.NoPen); p.setBrush(fill)
        p.drawEllipse(QRectF(cx - cr, cy - cr, cr*2, cr*2))   # draws the filled circle background
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx - cr, cy - cr, cr*2, cr*2))   # draws the circle outline
        ck = QPainterPath()   # path for the checkmark
        ck.moveTo(cx - s*0.24, cy + s*0.03)        # start of the tick (left side)
        ck.lineTo(cx - s*0.06, cy + s*0.23)        # bottom of the tick (downward stroke)
        ck.lineTo(cx + s*0.26, cy - s*0.18)        # right end of the tick (upward stroke)
        p.setPen(QPen(color, pw * 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(ck)   # draws the checkmark inside the circle

    p.restore()   # restores the painter state to what it was before this function was called


# ──────────────────────────────────────────────────────────
# STAT ICON BADGE  (animated glossy sphere + vector icon)
# ──────────────────────────────────────────────────────────
class _StatIconBadge(QWidget):
    """Glossy animated circular badge with custom vector icon — replaces text labels."""

    def __init__(self, icon_key: str, color: str, parent=None):
        super().__init__(parent)
        self._key   = icon_key   # stores the icon name/code (e.g. 'ap', 'tenants') to draw inside the badge
        self._color = color       # stores the accent colour for this badge (e.g. '#5C6BC0' for indigo)
        self._pulse = 0.0         # animation progress value between 0.0 and 1.0 that drives the glow intensity
        self._pulse_dir = 1       # direction of the pulse animation: 1 = growing, -1 = shrinking
        self.setFixedSize(58, 58)   # locks the badge to a 58×58 pixel circle so all stat tiles are consistent
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)   # connects the timer to the _tick method that updates the glow animation each frame
        self._timer.start(50)   # fires every 50ms (~20fps) to animate the pulsing glow ring

    def _tick(self):
        self._pulse += 0.04 * self._pulse_dir   # steps the animation forward or backward by 4% each tick
        if self._pulse >= 1.0:
            self._pulse = 1.0; self._pulse_dir = -1   # reverses the direction when the pulse reaches full brightness
        elif self._pulse <= 0.0:
            self._pulse = 0.0; self._pulse_dir = 1    # reverses the direction when the pulse reaches minimum brightness
        self.update()   # triggers a repaint so the new glow level is drawn

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)   # enables smooth anti-aliased rendering for the circular badge
        sw = min(self.width(), self.height())    # uses the smaller of width/height to keep the badge perfectly circular
        cx, cy = sw / 2, sw / 2   # calculates the centre point of the badge
        r = sw / 2 - 3            # radius of the main sphere (3px inset from the edge for the glow ring)
        col = QColor(self._color)  # converts the hex colour string to a QColor object for drawing

        # Pulsing outer glow ring — alpha oscillates with the pulse animation
        glow_a = int(30 + self._pulse * 45)   # alpha ranges from 30 (dim) to 75 (bright) based on the current pulse value
        glow_c = QColor(col); glow_c.setAlpha(glow_a)
        p.setPen(QPen(glow_c, 4))   # draws the outer ring with a 4px stroke in the pulsing colour
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(1, 1, sw - 2, sw - 2))   # draws the pulsing glow ring just inside the widget edges

        # Inner thin ring — faint static circle inside the glow ring
        ring_c = QColor(col); ring_c.setAlpha(90)   # semi-transparent inner ring (alpha 90)
        p.setPen(QPen(ring_c, 1.5))
        p.drawEllipse(QRectF(3, 3, sw - 6, sw - 6))   # draws a thin accent ring between the glow and the sphere

        # Glossy sphere background — radial gradient from light centre to dark edge
        sphere = QRadialGradient(cx - r*0.28, cy - r*0.32, r * 1.12)   # off-centre origin creates the 3D lighting effect (light source top-left)
        sphere.setColorAt(0.0, QColor(lerp_color(self._color, "#FFFFFF", 0.42)))   # bright centre (42% blended with white)
        sphere.setColorAt(0.40, QColor(lerp_color(self._color, P.bg_card, 0.72)))  # mid-tone transition
        sphere.setColorAt(1.0, QColor(lerp_color(self._color, P.bg_card, 0.90)))   # dark edge (90% blended with card background)
        p.setPen(Qt.NoPen); p.setBrush(sphere)
        p.drawEllipse(QRectF(5, 5, sw - 10, sw - 10))   # draws the glossy sphere body

        # Glass highlight — radial gradient in the top-left quarter simulating light reflection
        gloss = QRadialGradient(cx - r*0.25, cy - r*0.33, r * 0.48)
        ga = int(145 + self._pulse * 55)   # highlight opacity oscillates with the pulse (145–200 alpha)
        gloss.setColorAt(0.0, QColor(255, 255, 255, ga))    # bright white at the centre of the highlight
        gloss.setColorAt(0.6, QColor(255, 255, 255, 40))    # fading white at 60% radius
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))     # fully transparent at the edge of the highlight
        p.setBrush(gloss)
        p.drawEllipse(QRectF(8, 8, (sw - 16) * 0.68, (sw - 16) * 0.50))   # draws the highlight ellipse in the top-left area of the sphere

        # Vector icon — draws the appropriate icon on top of the sphere
        draw_key_icon(p, self._key, cx, cy, r * 0.50, col)   # draws the icon at half the sphere radius so it fits neatly inside
        p.end()


# ── Dynamic per-class button style (reads current PALETTE each time) ──
def _get_btn_qss(css_class: str = "primary") -> str:
    """Build button QSS from the *current* palette (not frozen at import time)."""
    styles = {
        # primary: the main call-to-action button filled with the accent indigo colour
        "primary": f"""
            QPushButton {{
                background-color: {P.accent}; color: {P.text_on_accent};
                border: none; border-radius: {D.btn_radius}px;
                padding: 10px 24px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover  {{ background-color: {P.accent_dim}; }}
            QPushButton:pressed {{ background-color: {lerp_color(P.accent_dim, '#000000', 0.18)}; }}
        """,
        # danger: a bright red button used for destructive actions like Delete
        "danger": f"""
            QPushButton {{
                background-color: {P.danger}; color: #FFFFFF;
                border: none; border-radius: {D.btn_radius}px;
                padding: 10px 20px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover  {{ background-color: {lerp_color(P.danger, '#000000', 0.15)}; }}
            QPushButton:pressed {{ background-color: {lerp_color(P.danger, '#000000', 0.30)}; }}
        """,
        # success: a green button used for confirmations like Mark as Paid
        "success": f"""
            QPushButton {{
                background-color: {P.success}; color: #FFFFFF;
                border: none; border-radius: {D.btn_radius}px;
                padding: 10px 20px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover  {{ background-color: {lerp_color(P.success, '#000000', 0.15)}; }}
            QPushButton:pressed {{ background-color: {lerp_color(P.success, '#000000', 0.30)}; }}
        """,
        # warning: an amber button with dark text used for cautionary actions
        "warning": f"""
            QPushButton {{
                background-color: {P.warning}; color: #1A1A1A;
                border: none; border-radius: {D.btn_radius}px;
                padding: 10px 20px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover  {{ background-color: {lerp_color(P.warning, '#000000', 0.12)}; }}
            QPushButton:pressed {{ background-color: {lerp_color(P.warning, '#000000', 0.25)}; }}
        """,
        # outline: a transparent button with a 1.5px accent border (hollow look)
        "outline": f"""
            QPushButton {{
                background-color: transparent; color: {P.accent};
                border: 1.5px solid {P.accent}; border-radius: {D.btn_radius}px;
                padding: 10px 20px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover  {{ background-color: {P.accent_glow}; }}
            QPushButton:pressed {{ background-color: {P.accent_ultra}; }}
        """,
        # ghost: a completely invisible button with no border, shows subtle highlight on hover
        "ghost": f"""
            QPushButton {{
                background-color: transparent; color: {P.text_secondary};
                border: none; padding: 6px 12px; font-size: 11px;
            }}
            QPushButton:hover {{
                color: {P.text_primary}; background-color: {P.bg_card_hover};
                border-radius: 6px;
            }}
        """,
    }
    return styles.get(css_class, styles["primary"])   # returns the matching style string, falls back to primary if name is unknown


def styled_button(text: str, css_class: str = "primary",
                   parent: QWidget = None) -> QPushButton:
    """Create a QPushButton with guaranteed inline colour styling."""
    btn = QPushButton(text, parent)   # creates a new button widget with the given label text
    btn.setProperty("cssClass", css_class)   # stores the style class name as a Qt property so other code can read it
    btn.setCursor(Qt.PointingHandCursor)   # changes the mouse cursor to a hand icon when hovering over the button
    btn.setFont(qfont(F.btn))   # applies the app's standard button font (semi-bold, 11px)
    # Dynamic QSS — reads current palette each time (not frozen at import time)
    btn.setStyleSheet(_get_btn_qss(css_class))   # applies the full colour stylesheet matching the requested variant
    return btn   # hands back the fully styled button to the caller


# ──────────────────────────────────────────────────────────
# STATUS helpers
# ──────────────────────────────────────────────────────────
STATUS_COLORS = {
    "Active":      P.success,    # maps Active status to the green success colour
    "Inactive":    P.text_muted, # maps Inactive status to the muted grey colour
    "Pending":     P.warning,    # maps Pending status to the amber warning colour
    "Paid":        P.success,    # maps Paid status to the green success colour
    "Overdue":     P.danger,     # maps Overdue status to the red danger colour
    "Resolved":    P.success,    # maps Resolved status to the green success colour
    "Open":        P.warning,    # maps Open status to the amber warning colour
    "In Progress": P.info,       # maps In Progress status to the blue info colour
    "Vacant":      P.accent,     # maps Vacant status to the indigo accent colour
    "Occupied":    P.success,    # maps Occupied status to the green success colour
    "Leaving":     P.warning,    # maps Leaving status to the amber warning colour
    "Reserved":    P.info,       # maps Reserved status to the blue info colour
    "Maintenance": P.warning,    # maps Maintenance status to the amber warning colour
}

PRIORITY_COLORS = {
    "High":   P.danger,   # maps High priority to the red danger colour (most urgent)
    "Medium": P.warning,  # maps Medium priority to the amber warning colour
    "Low":    P.success,  # maps Low priority to the green success colour (least urgent)
}


def badge_text(status: str) -> str:
    """Return status string with a coloured dot prefix."""
    symbol_map = {
        "Active": "● ", "Occupied": "● ", "Paid": "● ", "Resolved": "● ",   # solid circle for fully positive states
        "Pending": "◐ ", "Open": "◐ ", "In Progress": "◑ ",                  # half-circle for in-between states
        "Inactive": "○ ", "Vacant": "○ ",                                     # hollow circle for neutral/off states
        "Overdue": "● ", "Leaving": "◐ ",                                     # solid circle for overdue (red), half for leaving
    }
    return f"{symbol_map.get(status, '')} {status}"   # prepends the matching symbol then adds a space before the status label


# ──────────────────────────────────────────────────────────
# CARD  (elevated QFrame with accent top stripe)
# ──────────────────────────────────────────────────────────
class Card(QFrame):
    """Elevated card with border, accent top-line, and optional title."""

    def __init__(self, parent=None, title: str = "",
                 accent_color: str = P.accent):
        super().__init__(parent)
        self.setProperty("cssClass", "card")   # marks the frame as a 'card' so the global stylesheet can apply card-specific background and border rules
        self._accent = accent_color             # saves the accent colour for this card (used for the top stripe in paintEvent)
        self._layout = QVBoxLayout(self)        # creates a vertical stack layout that holds the header and body areas
        self._layout.setContentsMargins(0, 0, 0, 0)   # removes all padding so the painted top stripe sits flush against the card edge
        self._layout.setSpacing(0)                     # removes the gap between header and body sections

        # Accent top stripe (painted in paintEvent) — space is reserved by starting at y=0
        if title:
            hdr = QWidget()   # creates a plain container widget for the card header row
            hdr_layout = QHBoxLayout(hdr)
            hdr_layout.setContentsMargins(D.pad_md, D.pad_sm + 2, D.pad_md, 0)   # indents the header content and adds extra top padding to clear the 5px painted stripe
            dot = QLabel("●")   # creates a filled circle symbol that will be coloured in the accent colour as a visual marker
            dot.setFont(QFont("Segoe UI", 9))   # sets the bullet point to a small 9px size
            dot.setStyleSheet(f"color: {accent_color};")   # colours the dot with this card's accent colour (e.g. indigo for payments)
            dot.setFixedWidth(18)   # locks the dot to 18px wide so text always lines up regardless of dot size
            hdr_layout.addWidget(dot)
            title_lbl = QLabel(title)   # creates the card title text label
            title_lbl.setFont(qfont(F.h4))   # applies the h4 heading font (semi-bold, 13px)
            title_lbl.setStyleSheet(f"color: {P.text_primary};")   # sets the title text to the primary (near-white or near-black) text colour
            hdr_layout.addWidget(title_lbl)
            hdr_layout.addStretch()   # pushes the dot and title to the left, leaving empty space on the right
            self._layout.addWidget(hdr)

            sep = QFrame()   # creates a 1px horizontal line to visually separate the title from the card body
            sep.setFrameShape(QFrame.HLine)   # makes the QFrame render as a flat horizontal rule
            sep.setStyleSheet(f"color: {P.divider};")   # colours the separator line with the theme's divider colour
            sep.setFixedHeight(1)   # forces the separator to exactly 1px tall so it doesn't waste vertical space
            self._layout.addWidget(sep)

        self._body = QWidget()   # creates the body container that holds the main card content
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(D.pad_md, D.pad_sm, D.pad_md, D.pad_md)   # adds consistent internal padding around the card content
        self._layout.addWidget(self._body, 1)   # adds the body below the header and lets it stretch to fill the remaining card height

        # Drop shadow — deeper and softer
        shadow = QGraphicsDropShadowEffect()   # creates a drop shadow effect to make the card appear elevated above the background
        shadow.setBlurRadius(24)   # spreads the shadow softly over 24px for a deep, modern look
        shadow.setOffset(0, 4)     # offsets the shadow 4px downward (no horizontal offset) to match a light source from above
        shadow.setColor(QColor(0, 0, 0, 22))   # uses a very faint black (alpha 22) so the shadow is subtle, not heavy
        self.setGraphicsEffect(shadow)   # attaches the shadow effect to the card frame

    def paintEvent(self, event):
        super().paintEvent(event)   # lets Qt draw the card's standard background and border first
        # Draw accent top stripe (5px)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)   # enables anti-aliasing so the stripe edges are smooth
        grad = QLinearGradient(0, 0, self.width(), 0)   # creates a horizontal gradient from left to right across the full card width
        grad.setColorAt(0.0, QColor(self._accent))   # starts the stripe at full accent colour on the left
        grad.setColorAt(0.6, QColor(_blend(self._accent, P.bg_card, 0.5)))   # fades to a 50% blend at 60% of the width
        grad.setColorAt(1.0, QColor(P.bg_card))   # completely fades into the card background colour at the right edge
        painter.fillRect(0, 0, self.width(), 5, grad)   # paints the 5px tall gradient stripe at the very top of the card
        painter.end()

    def body_layout(self) -> QVBoxLayout:
        return self._body_layout   # exposes the inner body layout so callers can add their own widgets directly into the card


# ──────────────────────────────────────────────────────────
# STAT CARD  (KPI tile)
# ──────────────────────────────────────────────────────────
class StatCard(QFrame):
    """KPI tile: bold number + caption + icon badge."""

    def __init__(self, parent=None, icon="▦", value="0",
                 label="", color=P.accent):
        super().__init__(parent)
        self.setProperty("cssClass", "card")   # marks the frame as a card for the global stylesheet to apply card background/border
        self._color = color   # saves the accent colour so paintEvent can draw the matching top stripe

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)   # adds 20px left/right and 18px top/bottom padding inside the KPI tile

        # Left: value + label
        left = QVBoxLayout()
        left.setSpacing(4)   # puts 4px of space between the big number and the caption text below it
        self._val_lbl = QLabel(value)   # creates the large KPI number label (e.g. "142" for total tenants)
        self._val_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))   # makes the KPI number big (20pt bold) so it stands out at a glance
        self._val_lbl.setStyleSheet(f"color: {P.text_primary};")   # sets the number colour to the primary theme text colour
        left.addWidget(self._val_lbl)

        cap = QLabel(label)   # creates the caption label below the number (e.g. "Total Tenants")
        cap.setFont(qfont(F.small))   # uses the small font size so the caption doesn't compete visually with the number
        cap.setStyleSheet(f"color: {P.text_muted};")   # sets the caption to the muted colour so it reads as secondary info
        left.addWidget(cap)
        layout.addLayout(left, 1)   # places the text on the left side and gives it all available stretch space

        # Right: animated glossy icon badge
        badge = _StatIconBadge(icon, color)   # creates the pulsing sphere icon for this stat (e.g. house icon for apartments)
        layout.addWidget(badge)   # places the icon badge on the right side of the KPI tile

        # Drop shadow — deeper
        shadow = QGraphicsDropShadowEffect()   # creates a drop shadow to make this tile appear lifted above the dashboard grid
        shadow.setBlurRadius(18)   # spreads the shadow 18px for a medium-depth elevated look
        shadow.setOffset(0, 3)     # shifts the shadow 3px downward to simulate light from above
        shadow.setColor(QColor(0, 0, 0, 18))   # uses a very faint black shadow (alpha 18) for a subtle effect
        self.setGraphicsEffect(shadow)   # attaches the shadow to this stat card widget

    def paintEvent(self, event):
        super().paintEvent(event)   # lets Qt draw the standard card background and border first
        painter = QPainter(self)
        # Top gradient accent stripe (5px)
        grad = QLinearGradient(0, 0, self.width(), 0)   # horizontal gradient from left to right across the full tile width
        grad.setColorAt(0.0, QColor(self._color))   # starts at full accent colour (e.g. indigo for the payments tile)
        grad.setColorAt(0.6, QColor(_blend(self._color, P.bg_card, 0.5)))   # blends 50% with the card background at 60%
        grad.setColorAt(1.0, QColor(P.bg_card))   # fully fades into the card background on the right edge
        painter.fillRect(0, 0, self.width(), 5, grad)   # paints the 5px tall gradient stripe at the very top edge of the tile
        painter.end()

    def update_value(self, v: str):
        self._val_lbl.setText(v)   # replaces the displayed KPI number with a new value (e.g. after data refreshes)


# ──────────────────────────────────────────────────────────
# TABLE VIEW  (QTableView + QStandardItemModel)
# ──────────────────────────────────────────────────────────
def make_table(parent, columns, row_height: int = 42):
    """
    Create a styled QTableView with QStandardItemModel.
    columns: list of (heading, width) **or** (col_id, heading, width).
    parent: a QWidget **or** a QLayout (the table is added automatically).
    Returns (QTableView, QStandardItemModel).
    """
    from PySide6.QtWidgets import QLayout

    # Normalise columns to (heading, width)
    norm = []
    for c in columns:
        if len(c) == 2:
            norm.append((str(c[0]), int(c[1])))   # already in (heading, width) format — use as-is
        else:
            norm.append((str(c[1]), int(c[2])))   # in (id, heading, width) format — skip the id, keep heading and width

    model = QStandardItemModel()   # creates the data model that stores all the table rows and cells
    model.setHorizontalHeaderLabels([h for h, _w in norm])   # sets the column header text from the normalised column list

    # Determine parent widget vs layout
    parent_widget = None
    parent_layout = None
    if isinstance(parent, QLayout):
        parent_layout = parent   # if a layout was passed, the table will be added to it automatically
    elif isinstance(parent, QWidget):
        parent_widget = parent   # if a widget was passed, use it as the table's parent for ownership

    table = QTableView(parent_widget)   # creates the visual table view that renders the model data
    table.setModel(model)   # connects the data model to the table view so any model changes appear instantly
    table.setSelectionBehavior(QTableView.SelectRows)   # makes clicking any cell in a row select the entire row instead of just that cell
    table.setSelectionMode(QTableView.SingleSelection)   # restricts selection so the user can only highlight one row at a time
    table.setAlternatingRowColors(True)   # alternates row background colours (light/dark) to make rows easier to distinguish
    table.verticalHeader().setVisible(False)   # hides the row numbers on the left side for a cleaner look
    table.setShowGrid(False)   # removes the grid lines between cells to give the table a modern card-style appearance
    table.horizontalHeader().setHighlightSections(False)   # prevents the column header from changing colour when its column is selected
    table.verticalHeader().setDefaultSectionSize(row_height)   # sets every row to the specified height (42px default) for consistent spacing
    table.setEditTriggers(QTableView.NoEditTriggers)   # makes the table read-only so users cannot edit cells by clicking
    table.setSortingEnabled(True)   # lets users click a column header to sort the table by that column

    header = table.horizontalHeader()
    for i, (_h, w) in enumerate(norm):
        table.setColumnWidth(i, w)   # sets each column to its specified width in pixels
    # Stretch last column
    header.setStretchLastSection(True)   # makes the final column expand to fill all remaining horizontal space

    if parent_layout is not None:
        parent_layout.addWidget(table)   # automatically adds the table to the provided layout so the caller doesn't need to do it

    return table, model   # returns both the table view and the model so the caller can populate and manage the data


def table_clear(model: QStandardItemModel):
    """Remove all rows from the model (keeps headers)."""
    model.removeRows(0, model.rowCount())   # deletes every data row starting from row 0, keeping the header row intact


def table_insert(model: QStandardItemModel, values: list,
                 color: str = ""):
    """Add a row to the model with optional text colour."""
    items = []
    for val in values:
        item = QStandardItem(str(val) if val is not None else "—")   # converts each value to a string, showing a dash for None/empty values
        item.setEditable(False)   # makes this individual cell non-editable so users can't accidentally change the data
        if color:
            item.setForeground(QColor(color))   # sets the text colour for this cell (e.g. red for overdue rows)
        items.append(item)
    model.appendRow(items)   # adds the complete list of cells as a new row at the bottom of the table


def table_selected_id(table: QTableView, model: QStandardItemModel,
                      id_column: int = 0):
    """Return the value in `id_column` of the selected row, or None."""
    indexes = table.selectionModel().selectedRows()   # gets the list of currently selected rows from the table's selection state
    if not indexes:
        return None   # returns None when no row is selected (user hasn't clicked anything yet)
    row = indexes[0].row()   # gets the row number of the first (and only) selected row
    item = model.item(row, id_column)   # retrieves the cell at the selected row in the ID column (column 0 by default)
    if item:
        try:
            return int(item.text())   # converts the cell text to an integer database ID so it can be used for DB lookups
        except (ValueError, TypeError):
            return None   # returns None if the cell content can't be converted to an integer
    return None   # returns None if the cell itself is missing from the model


# ──────────────────────────────────────────────────────────
# SECTION HEADER
# ──────────────────────────────────────────────────────────
def section_header(parent_layout, title: str, subtitle: str = "",
                   accent: str = P.accent) -> QWidget:
    """Create a section header widget with gradient underline."""
    wrapper = QWidget()   # creates an outer container widget that holds both the title text and the gradient underline
    layout = QVBoxLayout(wrapper)
    layout.setContentsMargins(D.pad_lg, D.pad_lg, D.pad_lg, D.pad_md)   # adds large padding above/sides and medium padding below the heading
    layout.setSpacing(2)   # puts 2px of space between the title, subtitle, and underline

    t_lbl = QLabel(title)   # creates the main page/section title label (e.g. "Tenant Management")
    t_lbl.setFont(qfont(F.h1))   # applies the largest heading font (h1: bold, ~20px) to make the title prominent
    t_lbl.setStyleSheet(f"color: {P.text_primary};")   # sets the title text to the primary theme text colour
    layout.addWidget(t_lbl)

    if subtitle:
        s_lbl = QLabel(subtitle)   # creates a smaller subtitle label below the main title (e.g. "Manage all tenant records")
        s_lbl.setFont(qfont(F.body))   # uses the regular body font so the subtitle reads as secondary information
        s_lbl.setStyleSheet(f"color: {P.text_muted};")   # sets the subtitle to muted grey so it doesn't compete with the title
        layout.addWidget(s_lbl)

    # Gradient accent underline painted via a small custom widget
    line = _AccentLine(accent)   # creates the coloured underline widget that fades from accent colour to transparent
    line.setFixedHeight(5)   # locks the underline to exactly 5px tall
    layout.addWidget(line)

    parent_layout.addWidget(wrapper)   # inserts the complete header block (title + subtitle + underline) into the given parent layout
    return wrapper   # returns the wrapper so callers can optionally hide or update it later


class _AccentLine(QWidget):
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self._color = color   # stores the accent colour that the gradient line starts from

    def paintEvent(self, event):
        p = QPainter(self)
        w = min(self.width(), 180)   # caps the gradient line at 180px wide so it doesn't stretch too far across the page
        grad = QLinearGradient(0, 0, w, 0)   # creates a horizontal gradient from x=0 to x=w
        grad.setColorAt(0.0, QColor(self._color))   # starts at full accent colour on the left end of the line
        grad.setColorAt(1.0, QColor(P.bg_surface))   # fades completely into the surface background colour on the right end
        p.fillRect(0, 0, w, 5, grad)   # paints the 5px tall gradient stripe starting from the left edge
        p.end()


# ──────────────────────────────────────────────────────────
# STATUS RING  (circular gauge with QPainter)
# ──────────────────────────────────────────────────────────
class StatusRing(QWidget):
    """Circular occupancy gauge drawn with QPainter arcs."""

    def __init__(self, size=120, thickness=13,
                 color=P.accent, value=0.0, label="",
                 parent=None, fg_color=None):
        super().__init__(parent)
        self.setFixedSize(size, size)   # locks the ring widget to the given size (same width and height) so it's always circular
        self._size = size               # saves the size for use in paintEvent calculations
        self._t = thickness             # saves the arc stroke thickness (13px default for a bold ring)
        self._fg = fg_color if fg_color is not None else color   # uses fg_color if provided, otherwise falls back to the accent colour for the value arc
        self._label = label             # optional text label drawn in the centre of the ring below the percentage (e.g. "Occupied")
        self._value = max(0.0, min(1.0, value))   # clamps the initial value between 0.0 and 1.0 (0% to 100%)

    def set_value(self, v: float):
        self._value = max(0.0, min(1.0, v))   # clamps the new value between 0.0–1.0 then saves it
        self.update()   # triggers a repaint so the ring redraws with the updated percentage

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)   # enables smooth anti-aliased rendering for the circular arcs

        s = self._size
        t = self._t
        pad = 8   # 8px padding on each side so the arc isn't clipped at the widget edges
        rect = self.rect().adjusted(pad, pad, -pad, -pad)   # creates the drawing rectangle inset by 8px on all four sides

        # Track arc (background) — draws the full 360° grey circle behind the value arc
        pen = QPen(QColor(P.border), t)   # creates a pen with the border colour and the arc thickness
        pen.setCapStyle(Qt.RoundCap)      # rounds the ends of the drawn arc for a polished look
        p.setPen(pen)
        p.drawArc(rect, 0, 360 * 16)   # draws a full 360° background track circle (Qt angles use 1/16th degree units)

        # Subtle glow behind the value arc — paints a slightly wider, more transparent arc for a bloom effect
        if self._value > 0:
            glow_pen = QPen(QColor(_blend(self._fg, P.bg_card, 0.60)), t + 6)   # 6px wider than the main arc, 60% blended with background for a subtle glow
            glow_pen.setCapStyle(Qt.RoundCap)
            p.setPen(glow_pen)
            span = int(-360 * 16 * self._value)   # negative span makes the arc sweep clockwise from the top
            p.drawArc(rect, 90 * 16, span)   # starts the glow arc at 90° (12 o'clock position)

        # Value arc — draws the filled portion indicating the actual percentage
        pen.setColor(QColor(self._fg))   # switches the pen colour to the accent/foreground colour
        pen.setWidth(t)                  # resets the pen width back to the normal arc thickness
        p.setPen(pen)
        span = int(-360 * 16 * self._value)   # calculates the arc angle: e.g. 75% = -270 * 16 quarter-turns
        p.drawArc(rect, 90 * 16, span)   # draws the value arc starting at 12 o'clock, sweeping clockwise

        # Centre text — draws the percentage number and optional label in the middle of the ring
        p.setPen(QPen(QColor(P.text_primary)))
        pct_str = f"{int(self._value * 100)}%"   # converts the 0–1 float to a readable percentage string (e.g. "75%")
        p.setFont(QFont("Segoe UI", 16, QFont.Bold))   # uses a large bold font so the percentage is clearly readable
        if self._label:
            p.drawText(rect.adjusted(0, -8, 0, -8), Qt.AlignCenter, pct_str)   # draws the percentage slightly above centre to leave room for the label
            p.setFont(qfont(F.small))                                            # switches to the small font for the label text below the percentage
            p.setPen(QPen(QColor(P.text_secondary)))
            p.drawText(rect.adjusted(0, 14, 0, 14), Qt.AlignCenter, self._label)   # draws the label text 14px below the centre point
        else:
            p.drawText(rect, Qt.AlignCenter, pct_str)   # draws the percentage centred in the ring when no label is provided

        p.end()


# ──────────────────────────────────────────────────────────
# GRADIENT PROGRESS BAR  (thin, custom-painted)
# ──────────────────────────────────────────────────────────
class GradientProgressBar(QWidget):
    """Thin rounded progress bar with gradient fill."""

    def __init__(self, value=0.0, color=P.accent, *,
                 parent=None, width=280, height=12,
                 w=None, h=None):
        super().__init__(parent)
        width = w if w is not None else width    # prefers the shorthand 'w' parameter over 'width' when both are provided
        height = h if h is not None else height  # prefers the shorthand 'h' parameter over 'height' when both are provided
        self.setFixedSize(width, height)   # locks the widget to the exact dimensions so it doesn't resize with its container
        self._bar_w = width    # saves the bar width for use in paintEvent fill calculations
        self._bar_h = height   # saves the bar height for use in paintEvent corner radius calculations
        self._color = color    # saves the fill colour (e.g. indigo for payments bar)
        self._value = max(0.0, min(1.0, value))   # clamps the fill fraction between 0.0 (empty) and 1.0 (full)

    def set_value(self, v: float):
        self._value = max(0.0, min(1.0, v))   # clamps the new fill value between 0.0 and 1.0
        self.update()   # triggers a repaint so the bar redraws with the new fill width

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)   # enables anti-aliased rendering for smooth rounded corners
        r = self._bar_h // 2   # calculates the corner radius as half the bar height, making the ends perfectly semi-circular

        # Track — draws the full-width grey background bar
        p.setPen(Qt.NoPen)   # removes the border/outline from the background track
        p.setBrush(QColor(P.border))   # fills the track with the theme's border colour (light grey in light mode)
        p.drawRoundedRect(0, 0, self._bar_w, self._bar_h, r, r)   # draws the rounded background track across the full bar width

        # Fill — draws the coloured filled portion representing the current value
        fill_w = max(self._bar_h, int(self._bar_w * self._value))   # ensures the fill is at least as wide as the bar height so the rounded end always fits
        grad = QLinearGradient(0, 0, fill_w, 0)   # creates a horizontal gradient that runs across the fill portion only
        lighter = _blend(self._color, "#FFFFFF", 0.25)   # blends the accent colour 25% with white to create the lighter start of the gradient
        grad.setColorAt(0.0, QColor(lighter))   # starts the gradient with the lighter blended colour on the left
        grad.setColorAt(1.0, QColor(self._color))   # ends the gradient at the full accent colour on the right side
        p.setBrush(grad)
        p.drawRoundedRect(0, 0, fill_w, self._bar_h, r, r)   # draws the filled portion over the track with matching rounded corners

        # Gloss/shine overlay — a white semi-transparent highlight on the top half of the fill
        if fill_w > r * 2:   # only draws the gloss if the fill is wide enough to show it (at least a full rounded cap)
            shine = QLinearGradient(0, 0, 0, self._bar_h)   # creates a vertical gradient from top to bottom
            shine_c = QColor("#FFFFFF")
            shine_c.setAlpha(55)   # sets the top of the shine to white at alpha 55 (slightly opaque)
            shine.setColorAt(0.0, shine_c)   # places the brighter white highlight at the very top of the bar
            shine_c2 = QColor("#FFFFFF")
            shine_c2.setAlpha(0)             # fully transparent at the bottom half of the bar
            shine.setColorAt(1.0, shine_c2)
            p.setBrush(shine)
            p.drawRoundedRect(0, 0, fill_w, self._bar_h // 2, r, r)   # draws the gloss only on the top half of the fill area

        p.end()


# ──────────────────────────────────────────────────────────
# TOAST NOTIFICATION
# ──────────────────────────────────────────────────────────
class Toast(QWidget):
    """Transient overlay toast notification."""

    def __init__(self, parent, message: str, kind="success"):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)   # makes the toast appear as a floating tooltip-style overlay with no window title bar
        self.setAttribute(Qt.WA_TranslucentBackground)   # makes the window background transparent so the card border radius is visible without a white box around it
        self.setAttribute(Qt.WA_DeleteOnClose)   # automatically frees the widget's memory after it is closed

        # Maps each toast kind to its corresponding theme colour
        colors = {"success": P.success, "error": P.danger,
                  "info": P.info, "warning": P.warning}
        color = colors.get(kind, P.success)   # looks up the colour for the requested kind; defaults to green success if kind is unrecognised

        # Maps each toast kind to a short two-letter icon label (displayed in the coloured circle)
        icons = {"success": "OK", "error": "ER", "info": "IN", "warning": "WR"}
        icon = icons.get(kind, "OK")   # looks up the icon text for the requested kind; defaults to 'OK' if unrecognised

        # Applies QSS to make the body widget a rounded card with a thick left-side accent border
        self.setStyleSheet(f"""
            QWidget#toastBody {{
                background-color: {P.bg_card};
                border: 1px solid {P.border};
                border-radius: 10px;
                border-left: 5px solid {color};
            }}
        """)   # the 5px left border acts as the colour indicator strip matching the toast type (green/red/blue/amber)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)   # removes all margins around the outer layout so the body widget fills the full toast size

        body = QWidget()   # creates the visible card body that holds the icon and text
        body.setObjectName("toastBody")   # names this widget 'toastBody' so the QSS #toastBody selector applies to it
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(14, 12, 18, 12)   # adds 14px left, 18px right, 12px top/bottom padding inside the toast card

        icon_lbl = QLabel(icon)   # creates a label showing the two-letter icon text inside a coloured circle
        icon_lbl.setAlignment(Qt.AlignCenter)   # centres the icon text within its circular background
        icon_lbl.setFixedSize(26, 26)   # locks the icon badge to a 26×26px circle
        icon_lbl.setStyleSheet(
            f"background-color: {_blend(color, P.bg_card, 0.82)}; "   # blends the accent colour 82% with the card background for a very light tint behind the icon
            f"color: {color}; border-radius: 13px; font-weight: bold;")   # colours the icon text in the accent colour and makes the badge a perfect circle (13px radius)
        body_layout.addWidget(icon_lbl)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)   # puts 1px between the message and type label to keep them visually tight
        msg_lbl = QLabel(message)   # creates the main message text label (e.g. "Tenant added successfully")
        msg_lbl.setFont(qfont(F.body_bold))   # uses the semi-bold body font so the message text reads clearly
        msg_lbl.setStyleSheet(f"color: {P.text_primary};")   # sets the message text to the primary font colour
        text_layout.addWidget(msg_lbl)
        type_lbl = QLabel(kind.capitalize())   # creates the small type label below the message (e.g. "Success", "Error")
        type_lbl.setFont(qfont(F.caption))   # uses the tiny caption font so the type reads as secondary metadata
        type_lbl.setStyleSheet(f"color: {P.text_muted};")   # sets the type label to the muted grey colour
        text_layout.addWidget(type_lbl)
        body_layout.addLayout(text_layout)   # places the message and type labels to the right of the icon badge

        layout.addWidget(body)   # adds the completed card body into the outer transparent wrapper
        self.setFixedWidth(400)   # locks the toast to 400px wide so all toasts have a consistent size
        self.adjustSize()   # resizes the toast height to fit the content

        # Position in bottom-right of parent
        if parent:
            pw = parent.window()   # gets the top-level application window so the toast is positioned relative to the whole app
            geom = pw.geometry()   # reads the window's current position and size on screen
            self.move(geom.x() + geom.width() - 424,
                      geom.y() + geom.height() - self.height() - 24)   # positions the toast 24px above the bottom-right corner of the main window

        self.show()   # makes the toast visible immediately

        # Auto-dismiss after 3s
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3200, self.close)   # schedules the toast to automatically close itself after 3200ms (3.2 seconds)
