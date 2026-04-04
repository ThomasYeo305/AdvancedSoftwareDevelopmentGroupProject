# ============================================================
# PAMS — widgets.py
# Reusable PySide6 UI components — Professional light theme
# ============================================================
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableView, QHeaderView, QSizePolicy, QProgressBar,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QSortFilterProxyModel, Signal, QRectF, QPointF, QTimer
from PySide6.QtGui import (
    QFont, QColor, QStandardItemModel, QStandardItem, QPainter,
    QLinearGradient, QPen, QPainterPath, QRadialGradient, QConicalGradient,
)
import math

from .theme import PALETTE as P, FONTS as F, DIMS as D, lerp_color


# ──────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────
def qfont(spec: tuple) -> QFont:
    """Convert a theme font tuple (family, size, weight) → QFont."""
    family, size, weight = spec
    f = QFont(family, size)
    if weight == "bold":
        f.setBold(True)
    return f


def _blend(c1: str, c2: str, t: float) -> str:
    """Alias for lerp_color. t=0→c1, t=1→c2."""
    return lerp_color(c1, c2, t)


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
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    s = size
    pw = max(1.2, s * 0.11)
    pen = QPen(color, pw, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    fill = QColor(color)
    fill.setAlpha(65)

    # Normalise key
    _map = {
        "ap": "apartments", "tn": "tenants", "mt": "maintenance",
        "od": "overdue",    "rc": "collected", "db": "dashboard",
        "pm": "payments",   "cp": "complaints", "rp": "reports",
        "us": "users",
    }
    k = _map.get(key.lower(), key.lower())

    if k == "dashboard":
        gap = s * 0.14
        hw = (s * 0.90 - gap) / 2
        for row in range(2):
            for col in range(2):
                tx = cx - s * 0.45 + col * (hw + gap)
                ty = cy - s * 0.45 + row * (hw + gap)
                p.setPen(Qt.NoPen); p.setBrush(fill)
                p.drawRoundedRect(QRectF(tx, ty, hw, hw), 3, 3)
                p.setPen(pen); p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(QRectF(tx, ty, hw, hw), 3, 3)

    elif k == "tenants":
        hr = s * 0.26
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx - hr, cy - s * 0.46, hr * 2, hr * 2))
        bp = QPainterPath()
        bp.moveTo(cx - s * 0.46, cy + s * 0.46)
        bp.cubicTo(cx - s*0.46, cy + s*0.04, cx - s*0.26, cy - s*0.02, cx, cy - s*0.02)
        bp.cubicTo(cx + s*0.26, cy - s*0.02, cx + s*0.46, cy + s*0.04, cx + s*0.46, cy + s*0.46)
        p.drawPath(bp)

    elif k == "apartments":
        bx, by = cx - s * 0.30, cy - s * 0.46
        bw, bh = s * 0.60, s * 0.92
        p.setPen(Qt.NoPen); p.setBrush(fill)
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 2, 2)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 2, 2)
        p.setPen(QPen(color, pw * 1.4, Qt.SolidLine, Qt.FlatCap))
        p.drawLine(QPointF(bx, by + 2), QPointF(bx + bw, by + 2))
        ww, wh = s * 0.13, s * 0.12
        for row in range(3):
            for col in range(2):
                wx = bx + s * 0.08 + col * (ww + s * 0.11)
                wy = by + s * 0.10 + row * (wh + s * 0.09)
                if wy + wh < by + bh - s * 0.24:
                    p.setPen(Qt.NoPen)
                    wc = QColor(color); wc.setAlpha(130)
                    p.setBrush(wc)
                    p.drawRoundedRect(QRectF(wx, wy, ww, wh), 1.5, 1.5)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(cx - s*0.10, by + bh - s*0.26, s*0.20, s*0.26), 2, 0)

    elif k == "payments":
        card = QRectF(cx - s*0.44, cy - s*0.28, s*0.88, s*0.56)
        p.setPen(Qt.NoPen); p.setBrush(fill)
        p.drawRoundedRect(card, 5, 5)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(card, 5, 5)
        sc2 = QColor(color); sc2.setAlpha(150)
        p.setPen(Qt.NoPen); p.setBrush(sc2)
        p.drawRect(QRectF(cx - s*0.44, cy - s*0.14, s*0.88, s*0.12))
        chip = QColor(color); chip.setAlpha(185)
        p.setBrush(chip)
        p.drawRoundedRect(QRectF(cx - s*0.36, cy + s*0.05, s*0.23, s*0.16), 2, 2)
        p.setPen(pen); p.setBrush(Qt.NoBrush)

    elif k == "maintenance":
        p.setPen(QPen(color, s * 0.20, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(QPointF(cx - s*0.38, cy + s*0.42), QPointF(cx + s*0.06, cy - s*0.10))
        hr = s * 0.24
        hcx, hcy = cx + s*0.20, cy - s*0.22
        p.setPen(pen); p.setBrush(fill)
        p.drawEllipse(QRectF(hcx - hr, hcy - hr, hr * 2, hr * 2))
        p.setPen(QPen(color, pw * 0.9, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(hcx, hcy - hr*0.6), QPointF(hcx, hcy + hr*0.6))
        p.drawLine(QPointF(hcx - hr*0.6, hcy), QPointF(hcx + hr*0.6, hcy))

    elif k == "complaints":
        bub = QRectF(cx - s*0.44, cy - s*0.42, s*0.88, s*0.64)
        p.setPen(Qt.NoPen); p.setBrush(fill)
        p.drawRoundedRect(bub, 10, 10)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(bub, 10, 10)
        tail = QPainterPath()
        tail.moveTo(cx - s*0.08, cy + s*0.22)
        tail.lineTo(cx - s*0.28, cy + s*0.46)
        tail.lineTo(cx + s*0.06, cy + s*0.22)
        p.setPen(pen); p.drawPath(tail)
        for i in range(3):
            p.setPen(Qt.NoPen); p.setBrush(color)
            p.drawEllipse(QRectF(cx - s*0.16 + i*s*0.18, cy - s*0.13, s*0.10, s*0.10))

    elif k == "reports":
        bars = [(cx - s*0.36, 0.62), (cx - s*0.10, 0.38), (cx + s*0.16, 0.76)]
        bw = s * 0.22
        base_y = cy + s * 0.40
        for bx_i, bh_f in bars:
            bh_px = bh_f * s * 0.86
            bc = QColor(color); bc.setAlpha(160)
            p.setPen(Qt.NoPen); p.setBrush(bc)
            p.drawRoundedRect(QRectF(bx_i, base_y - bh_px, bw, bh_px), 2.5, 2.5)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawLine(QPointF(cx - s*0.46, base_y), QPointF(cx + s*0.46, base_y))
        dots = [
            (cx - s*0.25, base_y - 0.62*s*0.86),
            (cx + s*0.01, base_y - 0.38*s*0.86),
            (cx + s*0.27, base_y - 0.76*s*0.86),
        ]
        p.setPen(QPen(color, pw * 0.85, Qt.SolidLine, Qt.RoundCap))
        for i in range(len(dots) - 1):
            p.drawLine(QPointF(*dots[i]), QPointF(*dots[i + 1]))
        p.setPen(Qt.NoPen)
        for pt in dots:
            p.setBrush(color)
            p.drawEllipse(QRectF(pt[0] - s*0.055, pt[1] - s*0.055, s*0.11, s*0.11))

    elif k == "users":
        hr1 = s * 0.19
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx + s*0.06 - hr1, cy - s*0.40, hr1*2, hr1*2))
        bp1 = QPainterPath()
        bp1.moveTo(cx - s*0.06, cy + s*0.44)
        bp1.cubicTo(cx - s*0.06, cy + s*0.08, cx + s*0.06, cy + s*0.02, cx + s*0.24, cy + s*0.02)
        bp1.cubicTo(cx + s*0.42, cy + s*0.02, cx + s*0.50, cy + s*0.10, cx + s*0.50, cy + s*0.44)
        p.drawPath(bp1)
        hr2 = s * 0.21
        p.drawEllipse(QRectF(cx - s*0.22 - hr2, cy - s*0.42, hr2*2, hr2*2))
        bp2 = QPainterPath()
        bp2.moveTo(cx - s*0.50, cy + s*0.44)
        bp2.cubicTo(cx - s*0.50, cy + s*0.06, cx - s*0.32, cy + s*0.01, cx - s*0.18, cy + s*0.01)
        bp2.cubicTo(cx - s*0.04, cy + s*0.01, cx + s*0.02, cy + s*0.06, cx + s*0.02, cy + s*0.44)
        p.drawPath(bp2)

    elif k == "overdue":
        pts = [
            QPointF(cx + s*0.44*math.cos(math.radians(-90 + i*120)),
                    cy + s*0.44*math.sin(math.radians(-90 + i*120)))
            for i in range(3)
        ]
        tri = QPainterPath()
        tri.moveTo(pts[0]); tri.lineTo(pts[1]); tri.lineTo(pts[2]); tri.closeSubpath()
        p.setPen(Qt.NoPen); p.setBrush(fill); p.drawPath(tri)
        p.setPen(pen); p.setBrush(Qt.NoBrush); p.drawPath(tri)
        p.setPen(QPen(color, pw * 1.4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx, cy - s*0.24), QPointF(cx, cy + s*0.06))
        p.setPen(Qt.NoPen); p.setBrush(color)
        p.drawEllipse(QRectF(cx - s*0.07, cy + s*0.14, s*0.14, s*0.14))

    elif k == "collected":
        cr = s * 0.42
        p.setPen(Qt.NoPen); p.setBrush(fill)
        p.drawEllipse(QRectF(cx - cr, cy - cr, cr*2, cr*2))
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx - cr, cy - cr, cr*2, cr*2))
        ck = QPainterPath()
        ck.moveTo(cx - s*0.24, cy + s*0.03)
        ck.lineTo(cx - s*0.06, cy + s*0.23)
        ck.lineTo(cx + s*0.26, cy - s*0.18)
        p.setPen(QPen(color, pw * 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(ck)

    p.restore()


# ──────────────────────────────────────────────────────────
# STAT ICON BADGE  (animated glossy sphere + vector icon)
# ──────────────────────────────────────────────────────────
class _StatIconBadge(QWidget):
    """Glossy animated circular badge with custom vector icon — replaces text labels."""

    def __init__(self, icon_key: str, color: str, parent=None):
        super().__init__(parent)
        self._key   = icon_key
        self._color = color
        self._pulse = 0.0
        self._pulse_dir = 1
        self.setFixedSize(58, 58)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)

    def _tick(self):
        self._pulse += 0.04 * self._pulse_dir
        if self._pulse >= 1.0:
            self._pulse = 1.0; self._pulse_dir = -1
        elif self._pulse <= 0.0:
            self._pulse = 0.0; self._pulse_dir = 1
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        sw = min(self.width(), self.height())
        cx, cy = sw / 2, sw / 2
        r = sw / 2 - 3
        col = QColor(self._color)

        # Pulsing outer glow ring
        glow_a = int(30 + self._pulse * 45)
        glow_c = QColor(col); glow_c.setAlpha(glow_a)
        p.setPen(QPen(glow_c, 4))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(1, 1, sw - 2, sw - 2))

        # Inner thin ring
        ring_c = QColor(col); ring_c.setAlpha(90)
        p.setPen(QPen(ring_c, 1.5))
        p.drawEllipse(QRectF(3, 3, sw - 6, sw - 6))

        # Glossy sphere background
        sphere = QRadialGradient(cx - r*0.28, cy - r*0.32, r * 1.12)
        sphere.setColorAt(0.0, QColor(lerp_color(self._color, "#FFFFFF", 0.42)))
        sphere.setColorAt(0.40, QColor(lerp_color(self._color, P.bg_card, 0.72)))
        sphere.setColorAt(1.0, QColor(lerp_color(self._color, P.bg_card, 0.90)))
        p.setPen(Qt.NoPen); p.setBrush(sphere)
        p.drawEllipse(QRectF(5, 5, sw - 10, sw - 10))

        # Glass highlight
        gloss = QRadialGradient(cx - r*0.25, cy - r*0.33, r * 0.48)
        ga = int(145 + self._pulse * 55)
        gloss.setColorAt(0.0, QColor(255, 255, 255, ga))
        gloss.setColorAt(0.6, QColor(255, 255, 255, 40))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(gloss)
        p.drawEllipse(QRectF(8, 8, (sw - 16) * 0.68, (sw - 16) * 0.50))

        # Vector icon
        draw_key_icon(p, self._key, cx, cy, r * 0.50, col)
        p.end()


# ── Dynamic per-class button style (reads current PALETTE each time) ──
def _get_btn_qss(css_class: str = "primary") -> str:
    """Build button QSS from the *current* palette (not frozen at import time)."""
    styles = {
        "primary": f"""
            QPushButton {{
                background-color: {P.accent}; color: {P.text_on_accent};
                border: none; border-radius: {D.btn_radius}px;
                padding: 10px 24px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover  {{ background-color: {P.accent_dim}; }}
            QPushButton:pressed {{ background-color: {lerp_color(P.accent_dim, '#000000', 0.18)}; }}
        """,
        "danger": f"""
            QPushButton {{
                background-color: {P.danger}; color: #FFFFFF;
                border: none; border-radius: {D.btn_radius}px;
                padding: 10px 20px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover  {{ background-color: {lerp_color(P.danger, '#000000', 0.15)}; }}
            QPushButton:pressed {{ background-color: {lerp_color(P.danger, '#000000', 0.30)}; }}
        """,
        "success": f"""
            QPushButton {{
                background-color: {P.success}; color: #FFFFFF;
                border: none; border-radius: {D.btn_radius}px;
                padding: 10px 20px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover  {{ background-color: {lerp_color(P.success, '#000000', 0.15)}; }}
            QPushButton:pressed {{ background-color: {lerp_color(P.success, '#000000', 0.30)}; }}
        """,
        "warning": f"""
            QPushButton {{
                background-color: {P.warning}; color: #1A1A1A;
                border: none; border-radius: {D.btn_radius}px;
                padding: 10px 20px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover  {{ background-color: {lerp_color(P.warning, '#000000', 0.12)}; }}
            QPushButton:pressed {{ background-color: {lerp_color(P.warning, '#000000', 0.25)}; }}
        """,
        "outline": f"""
            QPushButton {{
                background-color: transparent; color: {P.accent};
                border: 1.5px solid {P.accent}; border-radius: {D.btn_radius}px;
                padding: 10px 20px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover  {{ background-color: {P.accent_glow}; }}
            QPushButton:pressed {{ background-color: {P.accent_ultra}; }}
        """,
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
    return styles.get(css_class, styles["primary"])


def styled_button(text: str, css_class: str = "primary",
                   parent: QWidget = None) -> QPushButton:
    """Create a QPushButton with guaranteed inline colour styling."""
    btn = QPushButton(text, parent)
    btn.setProperty("cssClass", css_class)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFont(qfont(F.btn))
    # Dynamic QSS — reads current palette each time (not frozen at import time)
    btn.setStyleSheet(_get_btn_qss(css_class))
    return btn


# ──────────────────────────────────────────────────────────
# STATUS helpers
# ──────────────────────────────────────────────────────────
STATUS_COLORS = {
    "Active":      P.success,
    "Inactive":    P.text_muted,
    "Pending":     P.warning,
    "Paid":        P.success,
    "Overdue":     P.danger,
    "Resolved":    P.success,
    "Open":        P.warning,
    "In Progress": P.info,
    "Vacant":      P.accent,
    "Occupied":    P.success,
    "Leaving":     P.warning,
    "Reserved":    P.info,
    "Maintenance": P.warning,
}

PRIORITY_COLORS = {
    "High":   P.danger,
    "Medium": P.warning,
    "Low":    P.success,
}


def badge_text(status: str) -> str:
    """Return status string with a coloured dot prefix."""
    symbol_map = {
        "Active": "● ", "Occupied": "● ", "Paid": "● ", "Resolved": "● ",
        "Pending": "◐ ", "Open": "◐ ", "In Progress": "◑ ",
        "Inactive": "○ ", "Vacant": "○ ",
        "Overdue": "● ", "Leaving": "◐ ",
    }
    return f"{symbol_map.get(status, '')} {status}"


# ──────────────────────────────────────────────────────────
# CARD  (elevated QFrame with accent top stripe)
# ──────────────────────────────────────────────────────────
class Card(QFrame):
    """Elevated card with border, accent top-line, and optional title."""

    def __init__(self, parent=None, title: str = "",
                 accent_color: str = P.accent):
        super().__init__(parent)
        self.setProperty("cssClass", "card")
        self._accent = accent_color
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # Accent top stripe (painted in paintEvent)
        if title:
            hdr = QWidget()
            hdr_layout = QHBoxLayout(hdr)
            hdr_layout.setContentsMargins(D.pad_md, D.pad_sm + 2, D.pad_md, 0)
            dot = QLabel("●")
            dot.setFont(QFont("Segoe UI", 9))
            dot.setStyleSheet(f"color: {accent_color};")
            dot.setFixedWidth(18)
            hdr_layout.addWidget(dot)
            title_lbl = QLabel(title)
            title_lbl.setFont(qfont(F.h4))
            title_lbl.setStyleSheet(f"color: {P.text_primary};")
            hdr_layout.addWidget(title_lbl)
            hdr_layout.addStretch()
            self._layout.addWidget(hdr)

            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet(f"color: {P.divider};")
            sep.setFixedHeight(1)
            self._layout.addWidget(sep)

        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(D.pad_md, D.pad_sm, D.pad_md, D.pad_md)
        self._layout.addWidget(self._body, 1)

        # Drop shadow — deeper and softer
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 22))
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        super().paintEvent(event)
        # Draw accent top stripe (5px)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0.0, QColor(self._accent))
        grad.setColorAt(0.6, QColor(_blend(self._accent, P.bg_card, 0.5)))
        grad.setColorAt(1.0, QColor(P.bg_card))
        painter.fillRect(0, 0, self.width(), 5, grad)
        painter.end()

    def body_layout(self) -> QVBoxLayout:
        return self._body_layout


# ──────────────────────────────────────────────────────────
# STAT CARD  (KPI tile)
# ──────────────────────────────────────────────────────────
class StatCard(QFrame):
    """KPI tile: bold number + caption + icon badge."""

    def __init__(self, parent=None, icon="▦", value="0",
                 label="", color=P.accent):
        super().__init__(parent)
        self.setProperty("cssClass", "card")
        self._color = color

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)

        # Left: value + label
        left = QVBoxLayout()
        left.setSpacing(4)
        self._val_lbl = QLabel(value)
        self._val_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self._val_lbl.setStyleSheet(f"color: {P.text_primary};")
        left.addWidget(self._val_lbl)

        cap = QLabel(label)
        cap.setFont(qfont(F.small))
        cap.setStyleSheet(f"color: {P.text_muted};")
        left.addWidget(cap)
        layout.addLayout(left, 1)

        # Right: animated glossy icon badge
        badge = _StatIconBadge(icon, color)
        layout.addWidget(badge)

        # Drop shadow — deeper
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 18))
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        # Top gradient accent stripe (5px)
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0.0, QColor(self._color))
        grad.setColorAt(0.6, QColor(_blend(self._color, P.bg_card, 0.5)))
        grad.setColorAt(1.0, QColor(P.bg_card))
        painter.fillRect(0, 0, self.width(), 5, grad)
        painter.end()

    def update_value(self, v: str):
        self._val_lbl.setText(v)


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
            norm.append((str(c[0]), int(c[1])))
        else:
            norm.append((str(c[1]), int(c[2])))

    model = QStandardItemModel()
    model.setHorizontalHeaderLabels([h for h, _w in norm])

    # Determine parent widget vs layout
    parent_widget = None
    parent_layout = None
    if isinstance(parent, QLayout):
        parent_layout = parent
    elif isinstance(parent, QWidget):
        parent_widget = parent

    table = QTableView(parent_widget)
    table.setModel(model)
    table.setSelectionBehavior(QTableView.SelectRows)
    table.setSelectionMode(QTableView.SingleSelection)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.setShowGrid(False)
    table.horizontalHeader().setHighlightSections(False)
    table.verticalHeader().setDefaultSectionSize(row_height)
    table.setEditTriggers(QTableView.NoEditTriggers)
    table.setSortingEnabled(True)

    header = table.horizontalHeader()
    for i, (_h, w) in enumerate(norm):
        table.setColumnWidth(i, w)
    # Stretch last column
    header.setStretchLastSection(True)

    if parent_layout is not None:
        parent_layout.addWidget(table)

    return table, model


def table_clear(model: QStandardItemModel):
    """Remove all rows from the model (keeps headers)."""
    model.removeRows(0, model.rowCount())


def table_insert(model: QStandardItemModel, values: list,
                 color: str = ""):
    """Add a row to the model with optional text colour."""
    items = []
    for val in values:
        item = QStandardItem(str(val) if val is not None else "—")
        item.setEditable(False)
        if color:
            item.setForeground(QColor(color))
        items.append(item)
    model.appendRow(items)


def table_selected_id(table: QTableView, model: QStandardItemModel,
                      id_column: int = 0):
    """Return the value in `id_column` of the selected row, or None."""
    indexes = table.selectionModel().selectedRows()
    if not indexes:
        return None
    row = indexes[0].row()
    item = model.item(row, id_column)
    if item:
        try:
            return int(item.text())
        except (ValueError, TypeError):
            return None
    return None


# ──────────────────────────────────────────────────────────
# SECTION HEADER
# ──────────────────────────────────────────────────────────
def section_header(parent_layout, title: str, subtitle: str = "",
                   accent: str = P.accent) -> QWidget:
    """Create a section header widget with gradient underline."""
    wrapper = QWidget()
    layout = QVBoxLayout(wrapper)
    layout.setContentsMargins(D.pad_lg, D.pad_lg, D.pad_lg, D.pad_md)
    layout.setSpacing(2)

    t_lbl = QLabel(title)
    t_lbl.setFont(qfont(F.h1))
    t_lbl.setStyleSheet(f"color: {P.text_primary};")
    layout.addWidget(t_lbl)

    if subtitle:
        s_lbl = QLabel(subtitle)
        s_lbl.setFont(qfont(F.body))
        s_lbl.setStyleSheet(f"color: {P.text_muted};")
        layout.addWidget(s_lbl)

    # Gradient accent underline painted via a small custom widget
    line = _AccentLine(accent)
    line.setFixedHeight(5)
    layout.addWidget(line)

    parent_layout.addWidget(wrapper)
    return wrapper


class _AccentLine(QWidget):
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self._color = color

    def paintEvent(self, event):
        p = QPainter(self)
        w = min(self.width(), 180)
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(self._color))
        grad.setColorAt(1.0, QColor(P.bg_surface))
        p.fillRect(0, 0, w, 5, grad)
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
        self.setFixedSize(size, size)
        self._size = size
        self._t = thickness
        self._fg = fg_color if fg_color is not None else color
        self._label = label
        self._value = max(0.0, min(1.0, value))

    def set_value(self, v: float):
        self._value = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        s = self._size
        t = self._t
        pad = 8
        rect = self.rect().adjusted(pad, pad, -pad, -pad)

        # Track arc (background)
        pen = QPen(QColor(P.border), t)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, 0, 360 * 16)

        # Subtle glow behind the value arc
        if self._value > 0:
            glow_pen = QPen(QColor(_blend(self._fg, P.bg_card, 0.60)), t + 6)
            glow_pen.setCapStyle(Qt.RoundCap)
            p.setPen(glow_pen)
            span = int(-360 * 16 * self._value)
            p.drawArc(rect, 90 * 16, span)

        # Value arc
        pen.setColor(QColor(self._fg))
        pen.setWidth(t)
        p.setPen(pen)
        span = int(-360 * 16 * self._value)
        p.drawArc(rect, 90 * 16, span)

        # Centre text
        p.setPen(QPen(QColor(P.text_primary)))
        pct_str = f"{int(self._value * 100)}%"
        p.setFont(QFont("Segoe UI", 16, QFont.Bold))
        if self._label:
            p.drawText(rect.adjusted(0, -8, 0, -8), Qt.AlignCenter, pct_str)
            p.setFont(qfont(F.small))
            p.setPen(QPen(QColor(P.text_secondary)))
            p.drawText(rect.adjusted(0, 14, 0, 14), Qt.AlignCenter, self._label)
        else:
            p.drawText(rect, Qt.AlignCenter, pct_str)

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
        width = w if w is not None else width
        height = h if h is not None else height
        self.setFixedSize(width, height)
        self._bar_w = width
        self._bar_h = height
        self._color = color
        self._value = max(0.0, min(1.0, value))

    def set_value(self, v: float):
        self._value = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self._bar_h // 2

        # Track
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(P.border))
        p.drawRoundedRect(0, 0, self._bar_w, self._bar_h, r, r)

        # Fill
        fill_w = max(self._bar_h, int(self._bar_w * self._value))
        grad = QLinearGradient(0, 0, fill_w, 0)
        lighter = _blend(self._color, "#FFFFFF", 0.25)
        grad.setColorAt(0.0, QColor(lighter))
        grad.setColorAt(1.0, QColor(self._color))
        p.setBrush(grad)
        p.drawRoundedRect(0, 0, fill_w, self._bar_h, r, r)

        # Gloss/shine overlay
        if fill_w > r * 2:
            shine = QLinearGradient(0, 0, 0, self._bar_h)
            shine_c = QColor("#FFFFFF")
            shine_c.setAlpha(55)
            shine.setColorAt(0.0, shine_c)
            shine_c2 = QColor("#FFFFFF")
            shine_c2.setAlpha(0)
            shine.setColorAt(1.0, shine_c2)
            p.setBrush(shine)
            p.drawRoundedRect(0, 0, fill_w, self._bar_h // 2, r, r)

        p.end()


# ──────────────────────────────────────────────────────────
# TOAST NOTIFICATION
# ──────────────────────────────────────────────────────────
class Toast(QWidget):
    """Transient overlay toast notification."""

    def __init__(self, parent, message: str, kind="success"):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)

        colors = {"success": P.success, "error": P.danger,
                  "info": P.info, "warning": P.warning}
        color = colors.get(kind, P.success)
        icons = {"success": "OK", "error": "ER", "info": "IN", "warning": "WR"}
        icon = icons.get(kind, "OK")

        self.setStyleSheet(f"""
            QWidget#toastBody {{
                background-color: {P.bg_card};
                border: 1px solid {P.border};
                border-radius: 10px;
                border-left: 5px solid {color};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        body = QWidget()
        body.setObjectName("toastBody")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(14, 12, 18, 12)

        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setFixedSize(26, 26)
        icon_lbl.setStyleSheet(
            f"background-color: {_blend(color, P.bg_card, 0.82)}; "
            f"color: {color}; border-radius: 13px; font-weight: bold;")
        body_layout.addWidget(icon_lbl)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        msg_lbl = QLabel(message)
        msg_lbl.setFont(qfont(F.body_bold))
        msg_lbl.setStyleSheet(f"color: {P.text_primary};")
        text_layout.addWidget(msg_lbl)
        type_lbl = QLabel(kind.capitalize())
        type_lbl.setFont(qfont(F.caption))
        type_lbl.setStyleSheet(f"color: {P.text_muted};")
        text_layout.addWidget(type_lbl)
        body_layout.addLayout(text_layout)

        layout.addWidget(body)
        self.setFixedWidth(400)
        self.adjustSize()

        # Position in bottom-right of parent
        if parent:
            pw = parent.window()
            geom = pw.geometry()
            self.move(geom.x() + geom.width() - 424,
                      geom.y() + geom.height() - self.height() - 24)

        self.show()

        # Auto-dismiss after 3s
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3200, self.close)
